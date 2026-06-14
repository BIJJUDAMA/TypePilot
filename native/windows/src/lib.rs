use pyo3::prelude::*;

mod hotkeys;
mod audio;
mod injection;

// Registers the global hotkey callbacks (Ctrl+Alt+Space)
#[pyfunction]
fn register_hotkey(on_press: PyObject, on_release: PyObject) -> PyResult<()> {
    hotkeys::register_global_hotkey(on_press, on_release)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))
}

// Unregisters the global hotkey hook
#[pyfunction]
fn unregister_hotkey() {
    hotkeys::unregister_global_hotkey();
}

// Starts the CPAL microphone capture
#[pyfunction]
fn start_audio_capture() -> PyResult<()> {
    audio::start_capture_stream()
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))
}

// Stops the CPAL microphone capture
#[pyfunction]
fn stop_audio_capture() {
    audio::stop_capture_stream();
}

// Retrieves accumulated float32 audio samples from CPAL ring buffer
#[pyfunction]
fn get_audio_samples() -> Vec<f32> {
    audio::pull_samples()
}

// Injects text into the focused window using SendInput API
#[pyfunction]
fn inject_text(text: String) -> PyResult<()> {
    injection::inject_text_to_active_window(&text)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))
}

// PyO3 native module definition
#[pymodule]
fn typepilot_native(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(register_hotkey, m)?)?;
    m.add_function(wrap_pyfunction!(unregister_hotkey, m)?)?;
    m.add_function(wrap_pyfunction!(start_audio_capture, m)?)?;
    m.add_function(wrap_pyfunction!(stop_audio_capture, m)?)?;
    m.add_function(wrap_pyfunction!(get_audio_samples, m)?)?;
    m.add_function(wrap_pyfunction!(inject_text, m)?)?;
    Ok(())
}
