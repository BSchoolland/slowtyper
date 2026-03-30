#!/usr/bin/env python3
"""
SlowTyper - A cross-platform tool that adds a keybind to type clipboard
contents naturally instead of pasting them instantly.

Keybind: Ctrl+Shift+M (Linux) / Cmd+Shift+M (Mac)

Requirements: pip install pynput pyperclip
"""

import platform
import random
import threading
import time

import pyperclip
from pynput import keyboard
from pynput.keyboard import Controller, Key

typer = Controller()
is_typing = False

# Timing config (seconds)
BASE_DELAY = 0.035  # Center of normal typing speed
FAST_KEYS = set("etaoinsrhld ")  # Common letters typed fastest
SLOW_KEYS = set("zqxjkvbp{}[]()!@#$%^&*")  # Uncommon chars typed slower

# Burst typing: humans type familiar sequences quickly then pause
BURST_MIN = 2
BURST_MAX = 7
BURST_PAUSE_MIN = 0.04
BURST_PAUSE_MAX = 0.125

# Thinking pauses at sentence boundaries
SENTENCE_ENDS = set(".!?")
THINK_PAUSE_MIN = 0.1
THINK_PAUSE_MAX = 0.3

# Micro-hesitations (brief unexpected pauses mid-word)
HESITATION_CHANCE = 0.03
HESITATION_MIN = 0.05
HESITATION_MAX = 0.15

IS_MAC = platform.system() == "Darwin"


def char_delay(char, prev_char):
    """Compute a human-like delay for a single character."""
    # Base delay with gaussian jitter (humans have a bell-curve timing)
    delay = max(0.02, random.gauss(BASE_DELAY, 0.025))

    # Fast typists hit common keys quicker
    if char.lower() in FAST_KEYS:
        delay *= random.uniform(0.6, 0.85)
    elif char.lower() in SLOW_KEYS or char.isupper():
        delay *= random.uniform(1.2, 1.6)

    # Repeated characters are faster (muscle memory)
    if char == prev_char:
        delay *= 0.5

    # Random micro-hesitation
    if random.random() < HESITATION_CHANCE:
        delay += random.uniform(HESITATION_MIN, HESITATION_MAX)

    return delay


MODIFIER_KEYS = {Key.shift, Key.ctrl, Key.cmd} if IS_MAC else {Key.shift, Key.ctrl}


def type_naturally(text, current_keys):
    global is_typing
    if is_typing:
        return
    is_typing = True

    # Wait for modifier keys to actually be released
    deadline = time.monotonic() + 3
    while any(k in current_keys for k in MODIFIER_KEYS):
        if time.monotonic() > deadline:
            break
        time.sleep(0.05)

    try:
        i = 0
        prev_char = ""
        while i < len(text) and is_typing:
            # Type in bursts then pause, like a real human
            burst_len = random.randint(BURST_MIN, BURST_MAX)

            for _ in range(burst_len):
                if i >= len(text) or not is_typing:
                    break

                char = text[i]

                # Thinking pause at sentence boundaries
                if prev_char in SENTENCE_ENDS and char == " ":
                    time.sleep(random.uniform(THINK_PAUSE_MIN, THINK_PAUSE_MAX))

                if char == "\n":
                    typer.press(Key.enter)
                    typer.release(Key.enter)
                    time.sleep(random.uniform(0.05, 0.2))
                elif char == "\t":
                    typer.press(Key.tab)
                    typer.release(Key.tab)
                    time.sleep(random.uniform(0.04, 0.1))
                else:
                    typer.type(char)
                    time.sleep(char_delay(char, prev_char))

                prev_char = char
                i += 1

            # Pause between bursts (simulates reading ahead / thinking)
            if i < len(text) and is_typing:
                time.sleep(random.uniform(BURST_PAUSE_MIN, BURST_PAUSE_MAX))
    finally:
        is_typing = False


def on_activate(current_keys):
    global is_typing
    if is_typing:
        print("[SlowTyper] Typing interrupted.")
        is_typing = False
        return

    text = pyperclip.paste()
    if not text:
        print("[SlowTyper] Clipboard is empty.")
        return

    print(f"[SlowTyper] Typing {len(text)} chars...")
    threading.Thread(target=type_naturally, args=(text, current_keys), daemon=True).start()


def normalize_key(key):
    """Normalize a key so modifiers and case are consistent."""
    if key in (Key.shift_l, Key.shift_r, Key.shift):
        return Key.shift
    if key in (Key.ctrl_l, Key.ctrl_r, Key.ctrl):
        return Key.ctrl
    if IS_MAC and key in (Key.cmd_l, Key.cmd_r, Key.cmd):
        return Key.cmd
    if isinstance(key, keyboard.KeyCode):
        # When Ctrl is held, key.char becomes a control character (e.g. \x02
        # for Ctrl+B). Fall back to vk (virtual key code) to get the real key.
        if key.vk is not None and 65 <= key.vk <= 90:
            return keyboard.KeyCode.from_char(chr(key.vk + 32))
        if key.char:
            return keyboard.KeyCode.from_char(key.char.lower())
    return key


def main():
    if IS_MAC:
        trigger = {Key.cmd, Key.shift, keyboard.KeyCode.from_char("m")}
        combo_name = "Cmd+Shift+M"
    else:
        trigger = {Key.ctrl, Key.shift, keyboard.KeyCode.from_char("m")}
        combo_name = "Ctrl+Shift+M"

    current_keys = set()

    def on_press(key):
        nk = normalize_key(key)
        current_keys.add(nk)
        if trigger.issubset(current_keys):
            on_activate(current_keys)

    def on_release(key):
        nk = normalize_key(key)
        current_keys.discard(nk)

    print(f"[SlowTyper] Listening for {combo_name} to slow-type clipboard contents.")
    print("[SlowTyper] Press the combo again while typing to cancel.")
    print("[SlowTyper] Press Ctrl+C here to quit.")

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


if __name__ == "__main__":
    main()
