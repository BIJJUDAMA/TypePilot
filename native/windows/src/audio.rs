use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use crossbeam_channel::{unbounded, Receiver, Sender};
use once_cell::sync::Lazy;

struct StreamWrapper(cpal::Stream);
unsafe impl Send for StreamWrapper {}
unsafe impl Sync for StreamWrapper {}

// Channel to pass chunks of samples from audio thread to bridge
static AUDIO_CHANNEL: Lazy<(Sender<Vec<f32>>, Receiver<Vec<f32>>)> = Lazy::new(|| unbounded());
static STREAM: Mutex<Option<StreamWrapper>> = Mutex::new(None);
static IS_RECORDING: AtomicBool = AtomicBool::new(false);

// Starts cpal audio capture stream and linear resampling
pub fn start_capture_stream() -> Result<(), String> {
    if IS_RECORDING.load(Ordering::SeqCst) {
        return Ok(());
    }

    // Drain old samples
    while AUDIO_CHANNEL.1.try_recv().is_ok() {}

    let host = cpal::default_host();
    let device = host.default_input_device()
        .ok_or_else(|| "No default input device found".to_string())?;

    let default_config = device.default_input_config()
        .map_err(|e| format!("Failed to get default input config: {}", e))?;

    let config = cpal::StreamConfig {
        channels: default_config.channels(),
        sample_rate: default_config.sample_rate(),
        buffer_size: cpal::BufferSize::Default,
    };

    let sample_rate = config.sample_rate.0 as f32;
    let channels = config.channels as usize;

    let mut resample_index = 0.0f32;
    let resample_step = sample_rate / 16000.0f32;
    let mut sample_buffer = Vec::new();
    let tx = AUDIO_CHANNEL.0.clone();

    let error_callback = |err| eprintln!("Audio stream error: {}", err);
    let data_callback = move |data: &[f32], _: &cpal::InputCallbackInfo| {
        if !IS_RECORDING.load(Ordering::SeqCst) {
            return;
        }

        // Convert stereo/multi-channel to mono
        let mut mono_samples = Vec::new();
        if channels == 1 {
            mono_samples.extend_from_slice(data);
        } else {
            for chunk in data.chunks_exact(channels) {
                let sum: f32 = chunk.iter().sum();
                mono_samples.push(sum / channels as f32);
            }
        }

        // Perform linear resampling to 16kHz and batch into a single vector
        let mut resampled_chunk = Vec::new();
        sample_buffer.extend(mono_samples);
        while (resample_index as usize) < sample_buffer.len() {
            let idx = resample_index as usize;
            let sample = if idx + 1 < sample_buffer.len() {
                let frac = resample_index - idx as f32;
                sample_buffer[idx] * (1.0 - frac) + sample_buffer[idx + 1] * frac
            } else {
                sample_buffer[idx]
            };

            resampled_chunk.push(sample);
            resample_index += resample_step;
        }

        // Send the entire chunk at once to minimize thread contention
        if !resampled_chunk.is_empty() {
            let _ = tx.send(resampled_chunk);
        }

        if resample_index as usize > 0 {
            sample_buffer.drain(0..(resample_index as usize));
            resample_index -= resample_index.floor();
        }
    };

    let stream = match default_config.sample_format() {
        cpal::SampleFormat::F32 => device.build_input_stream(&config, data_callback, error_callback, None),
        _ => return Err("Only F32 sample format is supported".to_string()),
    }.map_err(|e| format!("Failed to build input stream: {}", e))?;

    stream.play().map_err(|e| format!("Failed to play stream: {}", e))?;

    let mut stream_guard = STREAM.lock().unwrap();
    *stream_guard = Some(StreamWrapper(stream));
    IS_RECORDING.store(true, Ordering::SeqCst);

    Ok(())
}

// Stops cpal audio capture stream
pub fn stop_capture_stream() {
    IS_RECORDING.store(false, Ordering::SeqCst);
    let mut stream_guard = STREAM.lock().unwrap();
    if let Some(wrapper) = stream_guard.take() {
        let _ = wrapper.0.pause();
    }
}

// Pulls all pending sample chunks from channel and flattens them
pub fn pull_samples() -> Vec<f32> {
    let mut samples = Vec::new();
    while let Ok(chunk) = AUDIO_CHANNEL.1.try_recv() {
        samples.extend(chunk);
    }
    samples
}
