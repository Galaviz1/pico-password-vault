# USB-HID keyboard for the MicroPython vault: a singleton keyboard interface,
# and type_string(), which turns an ASCII string into US-layout keystrokes.
#
# The keyboard is created at import time but NOT started - starting it
# re-enumerates USB, which must happen once, early, from boot.py. builtin_driver
# keeps the REPL and the drive alive alongside the keyboard so the device is
# still debuggable and editable.
import usb.device
from usb.device.keyboard import KeyboardInterface, KeyCode

keyboard = KeyboardInterface()


def start():
    usb.device.get().init(keyboard, builtin_driver=True)


# --- US-layout ASCII -> (keycode, shift) -----------------------------------
def _build_map():
    m = {}
    for i in range(26):                       # a-z / A-Z
        m[chr(ord("a") + i)] = (KeyCode.A + i, False)
        m[chr(ord("A") + i)] = (KeyCode.A + i, True)
    digits = "1234567890"                     # N1..N9 then N0 are contiguous
    for i, d in enumerate(digits):
        m[d] = (KeyCode.N1 + i, False)
    shifted_digits = "!@#$%^&*()"             # same keys, shifted
    for i, s in enumerate(shifted_digits):
        m[s] = (KeyCode.N1 + i, True)
    pairs = {                                 # key: (unshifted, shifted)
        KeyCode.SPACE: (" ", None),
        KeyCode.TAB: ("\t", None),
        KeyCode.ENTER: ("\n", None),
        KeyCode.MINUS: ("-", "_"),
        KeyCode.EQUAL: ("=", "+"),
        KeyCode.OPEN_BRACKET: ("[", "{"),
        KeyCode.CLOSE_BRACKET: ("]", "}"),
        KeyCode.BACKSLASH: ("\\", "|"),
        KeyCode.SEMICOLON: (";", ":"),
        KeyCode.QUOTE: ("'", '"'),
        KeyCode.GRAVE: ("`", "~"),
        KeyCode.COMMA: (",", "<"),
        KeyCode.DOT: (".", ">"),
        KeyCode.SLASH: ("/", "?"),
    }
    for code, (plain, shift) in pairs.items():
        m[plain] = (code, False)
        if shift is not None:
            m[shift] = (code, True)
    return m


KEYMAP = _build_map()


def type_string(text, per_key_ms=6):
    import time
    for ch in text:
        entry = KEYMAP.get(ch)
        if entry is None:
            continue                          # skip anything not on a US keyboard
        code, shift = entry
        keys = [KeyCode.LEFT_SHIFT, code] if shift else [code]
        keyboard.send_keys(keys)
        time.sleep_ms(per_key_ms)
        keyboard.send_keys([])                # release
        time.sleep_ms(per_key_ms)
