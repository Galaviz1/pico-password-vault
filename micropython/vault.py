# Pico Password Vault - MicroPython edition.
#
# A B10K potentiometer navigates (absolute position -> menu index, with
# hysteresis so ADC noise doesn't flicker the selection); a push-button
# selects. Selecting an entry types its text into the focused field on the host
# over USB HID.
#
# Wiring:
#   OLED   SDA GP0, SCL GP1, VCC 3V3(pin36), GND
#   Pot    wiper -> GP26 (ADC0), ends -> 3V3 and GND
#   Button GP4 -> GND   (internal pull-up; pressed = low)
#
# Run standalone by copying to the board as main.py. On this dev board the
# stuck BOOTSEL means it won't auto-start; boot it with start.sh first.

import time
from machine import Pin, SoftI2C, ADC
from ssd1306 import SSD1306_I2C
import hid

# ----------------------------------------------------------------- config
OLED_W, OLED_H = 128, 32
LINE_H = 8
ROWS = OLED_H // LINE_H
ADC_FULL = 65535
OVERSAMPLE = 16
BOOT_WAIT_S = 180
IDLE_OFF_S = 30

# ----------------------------------------------------------------- hardware
i2c = SoftI2C(sda=Pin(0), scl=Pin(1), freq=400_000)
oled = SSD1306_I2C(OLED_W, OLED_H, i2c, addr=0x3C)
pot = ADC(Pin(26))
button = Pin(4, Pin.IN, Pin.PULL_UP)


def read_pot():
    """Averaged 0..ADC_FULL. Oversampling calms the RP2040 ADC noise."""
    total = 0
    for _ in range(OVERSAMPLE):
        total += pot.read_u16()
    return total // OVERSAMPLE


def pot_index(n, current):
    """Absolute pot position -> menu index in [0, n), with a dead-band around
    each boundary so a reading sitting on an edge does not flicker between two
    items. Only commits to a new index when clearly inside its slot."""
    if n <= 1:
        return 0
    raw = read_pot()
    slot = ADC_FULL // n
    band = slot // 4
    cand = raw * n // (ADC_FULL + 1)
    if cand < 0:
        cand = 0
    elif cand >= n:
        cand = n - 1
    if cand == current:
        return current
    lo = cand * slot
    hi = (cand + 1) * slot
    if lo + band <= raw <= hi - band:
        return cand
    return current


def pressed():
    """One event per physical press, debounced, waits for release."""
    if button.value():
        return False
    time.sleep_ms(20)
    if button.value():
        return False
    while not button.value():
        time.sleep_ms(5)
    return True


# ----------------------------------------------------------------- display
def show_lines(lines, selected=None):
    oled.fill(0)
    for i, text in enumerate(lines[:ROWS]):
        prefix = ">" if i == selected else " "
        oled.text((prefix + text)[:21], 0, i * LINE_H)
    oled.show()


def message(*lines):
    show_lines(list(lines))


# ----------------------------------------------------------------- data
def read_lines(path):
    try:
        with open(path) as f:
            return [ln.rstrip("\n\r") for ln in f if ln.strip()]
    except OSError:
        return []


def load_index():
    out = []
    for line in read_lines("/DB_Index.txt"):
        label, _, fname = line.partition("|")
        out.append((label.strip(), (fname or label).strip()))
    return out


def load_entries(fname):
    out = []
    for line in read_lines("/" + fname):
        label, sep, secret = line.partition("|")
        out.append((label.strip(), secret if sep else line))
    return out


# ----------------------------------------------------------------- menu
def menu(items, get_label):
    if not items:
        message("(empty)", "press to go back")
        while not pressed():
            time.sleep_ms(20)
        return -1
    idx = pot_index(len(items), 0)
    last_drawn = -1
    idle = time.time()
    blanked = False
    while True:
        new = pot_index(len(items), idx)
        if new != idx:
            idx = new
            idle = time.time()
            blanked = False
        if idx != last_drawn and not blanked:
            top = max(0, min(idx - (ROWS - 2), len(items) - ROWS))
            window = items[top:top + ROWS]
            show_lines([get_label(it) for it in window], selected=idx - top)
            last_drawn = idx
        if pressed():
            return idx
        if not blanked and time.time() - idle > IDLE_OFF_S:
            oled.fill(0)
            oled.show()
            blanked = True
            last_drawn = -1
        time.sleep_ms(20)


# ----------------------------------------------------------------- app
def boot_wait():
    start = time.time()
    while time.time() - start < BOOT_WAIT_S:
        message("Password Vault", "Ready in %ds" % int(BOOT_WAIT_S - (time.time() - start)),
                "", "press to skip")
        if pressed():
            break
        time.sleep_ms(200)
    oled.fill(0)
    oled.show()


def check_pin():
    pin = read_lines("/PIN.txt")
    pin = pin[0].strip() if pin else ""
    if not pin:
        return
    # 4 digits: turn to the digit position by pot, press to accept each.
    while True:
        entered = ""
        for slot in range(len(pin)):
            d = 0
            while True:
                d = pot_index(10, d)
                shown = entered + "[" + str(d) + "]" + "_" * (len(pin) - slot - 1)
                message("Enter PIN", shown)
                if pressed():
                    entered += str(d)
                    break
                time.sleep_ms(20)
        if entered == pin:
            return
        message("Wrong PIN", "try again")
        time.sleep(1)


def main():
    boot_wait()
    check_pin()
    databases = load_index()
    while True:
        di = menu(databases, lambda db: db[0])
        if di < 0:
            continue
        label, fname = databases[di]
        entries = load_entries(fname) + [("<- back", None)]
        while True:
            ei = menu(entries, lambda e: e[0])
            name, secret = entries[ei]
            if secret is None:
                break
            message("Typing:", name[:21])
            time.sleep_ms(300)
            hid.type_string(secret)


try:
    main()
except Exception as e:
    try:
        message("ERROR", str(e)[:21], str(e)[21:42])
    except Exception:
        pass
    raise
