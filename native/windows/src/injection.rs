use windows::Win32::UI::Input::KeyboardAndMouse::{
    SendInput, INPUT, INPUT_0, INPUT_KEYBOARD, KEYBDINPUT, KEYEVENTF_KEYUP, KEYEVENTF_UNICODE,
    VIRTUAL_KEY, VK_LCONTROL, VK_LMENU, VK_LSHIFT, VK_LWIN, VK_RCONTROL, VK_RMENU, VK_RSHIFT,
    VK_RWIN, VK_BACK, KEYBD_EVENT_FLAGS,
};

fn add_keyup(inputs: &mut Vec<INPUT>, vk: VIRTUAL_KEY) {
    inputs.push(INPUT {
        r#type: INPUT_KEYBOARD,
        Anonymous: INPUT_0 {
            ki: KEYBDINPUT {
                wVk: vk,
                wScan: 0,
                dwFlags: KEYEVENTF_KEYUP,
                time: 0,
                dwExtraInfo: 0,
            },
        },
    });
}

// Injects string into active window by sending unicode keyboard inputs
pub fn inject_text_to_active_window(text: &str) -> Result<(), String> {
    let mut inputs = Vec::new();

    // Release any physically held modifier keys to prevent shortcut interference
    let modifiers = [
        VK_LCONTROL, VK_RCONTROL,
        VK_LMENU, VK_RMENU,
        VK_LSHIFT, VK_RSHIFT,
        VK_LWIN, VK_RWIN
    ];
    for &mod_key in &modifiers {
        add_keyup(&mut inputs, mod_key);
    }

    let utf16_units: Vec<u16> = text.encode_utf16().collect();
    for &unit in &utf16_units {
        if unit == 0x0008 {
            // Special case: Windows KEYEVENTF_UNICODE treats backspace control character 0x0008 
            // as a printable space/glyph in many editors. Omit KEYEVENTF_UNICODE and send 
            // as a standard virtual keypress (VK_BACK) to force real character deletion.
            
            // Key down event for virtual backspace key
            inputs.push(INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: INPUT_0 {
                    ki: KEYBDINPUT {
                        wVk: VK_BACK,
                        wScan: 0,
                        dwFlags: KEYBD_EVENT_FLAGS(0),
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            });

            // Key up event for virtual backspace key
            inputs.push(INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: INPUT_0 {
                    ki: KEYBDINPUT {
                        wVk: VK_BACK,
                        wScan: 0,
                        dwFlags: KEYEVENTF_KEYUP,
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            });
        } else {
            // Key down event for unicode character
            inputs.push(INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: INPUT_0 {
                    ki: KEYBDINPUT {
                        wVk: VIRTUAL_KEY(0),
                        wScan: unit,
                        dwFlags: KEYEVENTF_UNICODE,
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            });

            // Key up event for unicode character
            inputs.push(INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: INPUT_0 {
                    ki: KEYBDINPUT {
                        wVk: VIRTUAL_KEY(0),
                        wScan: unit,
                        dwFlags: KEYEVENTF_UNICODE | KEYEVENTF_KEYUP,
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            });
        }
    }

    unsafe {
        let sent = SendInput(&inputs, std::mem::size_of::<INPUT>() as i32);
        if sent != inputs.len() as u32 {
            return Err("Failed to inject all keyboard input events".to_string());
        }
    }

    Ok(())
}
