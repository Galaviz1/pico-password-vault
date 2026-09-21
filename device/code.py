# Pico Password Vault - a USB-HID password typer on a Raspberry Pi Pico.
#
# Turn the encoder to move, press to select. Pick a database, pick an entry,
# and the device types that entry's text into whatever field is focused on the
# host, as if you had typed it on a keyboard.
#
# HARDWARE NOTE specific to this build: the OLED runs on BIT-BANGED I2C
# (bitbangio), not hardware I2C (busio). The RP2040 hardware I2C block does not
# work with this SSD1306 - it NAKs every data byte. bitbangio drives the same
# two pins in software and works. See github.com/Galaviz1/pico-ssd1306-guide.
#
# SECURITY NOTE: databases are PLAIN TEXT in flash, gated only by a PIN. This
# is fine for low-value logins and demos; do not store anything that matters
# without the encrypted variant. See the README.

import time
import board
import bitbangio
import digitalio
import rotaryio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
import adafruit_ssd1306

# ------------------------------------------------------------------ pins
SDA_PIN = board.GP0
SCL_PIN = board.GP1
ENC_A_PIN = board.GP2
ENC_B_PIN = board.GP3
BTN_PIN = board.GP4
# Optional RGB LED - set any to None if you did not wire it.
LED_R_PIN = board.GP5
LED_G_PIN = board.GP6
LED_B_PIN = board.GP7

# --------------------------------------------------------------- settings
OLED_W, OLED_H = 128, 32
LINE_H = 8                 # 5x8 font, one text row is 8 px -> 4 rows
ROWS = OLED_H // LINE_H
BOOT_WAIT_S = 180          # wait after power-on so we do not disturb PC boot
IDLE_OFF_S = 30            # blank the display after this many idle seconds
PIN_FILE = "/PIN.txt"
INDEX_FILE = "/DB_Index.txt"

# --------------------------------------------------------------- hardware
i2c = bitbangio.I2C(SCL_PIN, SDA_PIN, frequency=400_000)
oled = adafruit_ssd1306.SSD1306_I2C(OLED_W, OLED_H, i2c, addr=0x3C)

encoder = rotaryio.IncrementalEncoder(ENC_A_PIN, ENC_B_PIN)

button = digitalio.DigitalInOut(BTN_PIN)
button.switch_to_input(pull=digitalio.Pull.UP)

kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)


def _led(pin):
    if pin is None:
        return None
    io = digitalio.DigitalInOut(pin)
    io.switch_to_output(value=False)
    return io


led_r, led_g, led_b = _led(LED_R_PIN), _led(LED_G_PIN), _led(LED_B_PIN)


def set_led(r=False, g=False, b=False):
    if led_r:
        led_r.value = r
    if led_g:
        led_g.value = g
    if led_b:
        led_b.value = b


# --------------------------------------------------------------- display
def show_lines(lines, selected=None):
    """Draw up to ROWS lines; mark the selected one with a caret."""
    oled.fill(0)
    for i, text in enumerate(lines[:ROWS]):
        prefix = ">" if i == selected else " "
        oled.text((prefix + text)[:21], 0, i * LINE_H, 1)
    oled.show()


def message(*lines):
    show_lines(list(lines))


# --------------------------------------------------------------- input
def read_button():
    """Debounced press detector. Returns True once per physical press."""
    if button.value:            # released (pull-up high)
        return False
    time.sleep(0.02)
    if button.value:
        return False
    while not button.value:     # wait for release so one press = one event
        time.sleep(0.01)
    return True


_last_pos = encoder.position


def read_delta():
    """Signed detents since the last call.

    rotaryio.IncrementalEncoder applies divisor=4 by default, so one detent of
    a standard KY-040 is a position change of 1. If your encoder steps two at a
    time, pass divisor=2 where the encoder is created; if it feels reversed,
    swap ENC_A_PIN and ENC_B_PIN.
    """
    global _last_pos
    pos = encoder.position
    delta = pos - _last_pos
    _last_pos = pos
    return delta


# --------------------------------------------------------------- data
def read_lines(path):
    try:
        with open(path, "r") as f:
            return [ln.rstrip("\n\r") for ln in f if ln.strip()]
    except OSError:
        return []


def load_index():
    """DB_Index.txt: one 'Label|filename.txt' per line."""
    dbs = []
    for line in read_lines(INDEX_FILE):
        if "|" in line:
            label, fname = line.split("|", 1)
            dbs.append((label.strip(), fname.strip()))
        else:
            dbs.append((line.strip(), line.strip()))
    return dbs


def load_entries(fname):
    """A database file: one 'Label|secret-to-type' per line."""
    entries = []
    for line in read_lines("/" + fname):
        if "|" in line:
            label, secret = line.split("|", 1)
            entries.append((label.strip(), secret))
        else:
            entries.append((line.strip(), line))
    return entries


# --------------------------------------------------------------- menus
def menu(title, items, get_label):
    """Scroll a list, return the chosen index, or -1 if the list is empty."""
    if not items:
        message(title, "(empty)")
        while not read_button():
            time.sleep(0.05)
        return -1

    idx = 0
    dirty = True
    idle_since = time.monotonic()
    blanked = False

    while True:
        d = read_delta()
        if d:
            idx = (idx + d) % len(items)
            dirty = True
            idle_since = time.monotonic()
            if blanked:
                blanked = False

        if dirty and not blanked:
            top = max(0, min(idx - (ROWS - 2), len(items) - ROWS))
            window = items[top:top + ROWS]
            labels = [get_label(it) for it in window]
            show_lines(labels, selected=idx - top)
            dirty = False

        if read_button():
            return idx

        if not blanked and time.monotonic() - idle_since > IDLE_OFF_S:
            oled.fill(0)
            oled.show()
            blanked = True

        time.sleep(0.02)


def enter_pin(correct):
    """Turn to change the current digit, press to lock it in. 4 digits."""
    digits = [0, 0, 0, 0]
    pos = 0
    while pos < 4:
        d = read_delta()
        if d:
            digits[pos] = (digits[pos] + d) % 10
        shown = "".join(str(x) if i < pos else
                        ("[" + str(x) + "]" if i == pos else "_")
                        for i, x in enumerate(digits))
        message("Enter PIN", shown)
        if read_button():
            pos += 1
        time.sleep(0.02)
    return "".join(str(x) for x in digits) == correct.strip()


# --------------------------------------------------------------- app
def boot_wait():
    """Idle after power-on so we do not inject anything during PC boot."""
    set_led(b=True)
    start = time.monotonic()
    while time.monotonic() - start < BOOT_WAIT_S:
        remaining = int(BOOT_WAIT_S - (time.monotonic() - start))
        message("Password Vault", "Ready in %ds" % remaining, "", "press to skip")
        if read_button():
            break
        time.sleep(0.2)
    oled.fill(0)
    oled.show()


def main():
    boot_wait()

    pin = read_lines(PIN_FILE)
    pin = pin[0] if pin else ""
    if pin:
        set_led(r=True)
        while not enter_pin(pin):
            message("Wrong PIN", "try again")
            time.sleep(1)
    set_led(g=True)

    databases = load_index()

    while True:
        di = menu("Databases", databases, lambda db: db[0])
        if di < 0:
            continue
        label, fname = databases[di]
        entries = load_entries(fname)

        while True:
            ei = menu(label, entries + [("<- back", None)],
                      lambda e: e[0])
            if ei == len(entries):        # the "back" row
                break
            name, secret = entries[ei]
            if secret is None:
                break
            message("Typing:", name[:21])
            set_led(g=True, b=True)
            time.sleep(0.3)
            layout.write(secret)
            set_led(g=True)


try:
    main()
except Exception as e:  # keep a crash visible instead of a dark screen
    try:
        message("ERROR", str(e)[:21], str(e)[21:42])
    except Exception:
        pass
    raise
