use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;
use std::thread;
use once_cell::sync::Lazy;
use pyo3::prelude::*;
use windows::Win32::Foundation::{HWND, LPARAM, LRESULT, WPARAM};
use windows::Win32::UI::Input::KeyboardAndMouse::{
    GetAsyncKeyState, VK_CONTROL, VK_MENU, VK_SPACE
};
use windows::Win32::UI::WindowsAndMessaging::{
    CallNextHookEx, DispatchMessageW, GetMessageW, SetWindowsHookExW, TranslateMessage,
    UnhookWindowsHookEx, HHOOK, KBDLLHOOKSTRUCT, MSG, WH_KEYBOARD_LL, WM_KEYDOWN, WM_KEYUP,
    WM_SYSKEYDOWN, WM_SYSKEYUP,
};

static HOOK_HANDLE: Lazy<Mutex<Option<HHOOK>>> = Lazy::new(|| Mutex::new(None));
static CALLBACKS: Lazy<Mutex<Option<(PyObject, PyObject)>>> = Lazy::new(|| Mutex::new(None));
static IS_PRESSED: AtomicBool = AtomicBool::new(false);
static HOOK_THREAD_ACTIVE: AtomicBool = AtomicBool::new(false);

// Low-level keyboard hook callback procedure
unsafe extern "system" fn hook_proc(code: i32, w_param: WPARAM, l_param: LPARAM) -> LRESULT {
    if code >= 0 {
        let kb_struct = *(l_param.0 as *const KBDLLHOOKSTRUCT);
        let key = kb_struct.vkCode as u16;

        if key == VK_SPACE.0 {
            let msg = w_param.0 as u32;
            let is_down = msg == WM_KEYDOWN || msg == WM_SYSKEYDOWN;
            let is_up = msg == WM_KEYUP || msg == WM_SYSKEYUP;

            if is_down {
                let ctrl_down = GetAsyncKeyState(VK_CONTROL.0 as i32) < 0;
                let alt_down = GetAsyncKeyState(VK_MENU.0 as i32) < 0;

                if ctrl_down && alt_down {
                    if !IS_PRESSED.load(Ordering::SeqCst) {
                        IS_PRESSED.store(true, Ordering::SeqCst);
                        trigger_callback(true);
                    }
                    return LRESULT(1); // Swallow the hotkey press and repeat events
                }
            } else if is_up && IS_PRESSED.load(Ordering::SeqCst) {
                IS_PRESSED.store(false, Ordering::SeqCst);
                trigger_callback(false);
                return LRESULT(1); // Swallow the hotkey release event
            }
        }
    }
    CallNextHookEx(None, code, w_param, l_param)
}

fn trigger_callback(is_press: bool) {
    let callbacks_guard = CALLBACKS.lock().unwrap();
    if let Some((on_press, on_release)) = &*callbacks_guard {
        Python::with_gil(|py| {
            let callback = if is_press { on_press } else { on_release };
            if let Err(e) = callback.call0(py) {
                eprintln!("Error executing hotkey callback: {:?}", e);
            }
        });
    }
}

pub fn register_global_hotkey(on_press: PyObject, on_release: PyObject) -> Result<(), String> {
    {
        let mut callbacks_guard = CALLBACKS.lock().unwrap();
        *callbacks_guard = Some((on_press, on_release));
    }

    if HOOK_THREAD_ACTIVE.load(Ordering::SeqCst) {
        return Ok(());
    }
    HOOK_THREAD_ACTIVE.store(true, Ordering::SeqCst);

    thread::spawn(|| unsafe {
        let hook = SetWindowsHookExW(
            WH_KEYBOARD_LL,
            Some(hook_proc),
            None,
            0,
        ).map_err(|e| e.to_string());

        match hook {
            Ok(h) => {
                {
                    let mut handle_guard = HOOK_HANDLE.lock().unwrap();
                    *handle_guard = Some(h);
                }
                let mut msg = MSG::default();
                while HOOK_THREAD_ACTIVE.load(Ordering::SeqCst) {
                    let _ = GetMessageW(&mut msg, HWND::default(), 0, 0);
                    let _ = TranslateMessage(&msg);
                    let _ = DispatchMessageW(&msg);
                }
            }
            Err(e) => {
                eprintln!("Failed to set windows keyboard hook: {}", e);
                HOOK_THREAD_ACTIVE.store(false, Ordering::SeqCst);
            }
        }
    });

    Ok(())
}

pub fn unregister_global_hotkey() {
    HOOK_THREAD_ACTIVE.store(false, Ordering::SeqCst);
    let mut handle_guard = HOOK_HANDLE.lock().unwrap();
    if let Some(h) = handle_guard.take() {
        unsafe {
            let _ = UnhookWindowsHookEx(h);
        }
    }
    let mut callbacks_guard = CALLBACKS.lock().unwrap();
    *callbacks_guard = None;
}
