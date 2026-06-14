# TypePilot

## Idea

A local voice typing tool that converts speech into clean text and types it wherever the cursor is.

## Flow

Hold Hotkey
    ↓
Speak
    ↓
Transcribe Speech
    ↓
Clean Up Text
    ↓
Type At Cursor

## Features

- Push-to-talk voice typing
- Local speech recognition
- Live transcript overlay
- Automatic punctuation
- Automatic capitalization
- Remove filler words
- Remove repeated words
- Remove false starts
- Number normalization
- Symbol normalization
- Fast text injection
- Works in any text field
- Basic voice shortcuts
  - Undo
  - Redo
- Snippet expansion
- Fully offline

## Tech Stack

- Faster Whisper → Speech Recognition
- DeepMultilingualPunctuation → Punctuation
- SmolLM2 1.7B → Text Cleanup
- PyQt6 → Overlay UI
- Rust → Hotkeys, Audio Capture, Text Injection

## Goal

Replace keyboard typing with voice while producing text that looks like it was typed manually.
