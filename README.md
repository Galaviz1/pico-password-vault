# pico-password-vault

A Raspberry Pi Pico that plugs into a PC as a USB keyboard and **types** a stored login into whatever field is focused. Turn the encoder to pick an entry, press to type it.

A port of Smurfy_CH's [Password Safe / Keyboard Injector v5](https://www.instructables.com/Password-Safe-Keyboard-Injector-Version-50/) from the Waveshare RP2040-Zero to a plain Raspberry Pi Pico, with the pins remapped and two changes forced by the hardware — see below.

> **Read the security section before storing anything real.** Entries are plain text in flash behind a PIN, not encryption.

---

## Editions

| Edition | Input | Firmware | Folder |
| --- | --- | --- | --- |
| Original port | rotary encoder | CircuitPython | [`device/`](device/) |
| MicroPython | **B10K pot + button** | MicroPython | [`micropython/`](micropython/) |

The MicroPython edition runs on the firmware this Pico already has (no reflash)
and swaps the encoder for a potentiometer. Everything below describes the
CircuitPython port; the MicroPython edition has its own [README](micropython/README.md).

## Components

You already have the Pico, the 0.91" SSD1306 128×32 OLED, and jumper wires. To finish it you need **one** part:

| Part | Role | Cost | Required |
| --- | --- | --- | --- |
| Rotary encoder w/ push-button (KY-040) | the only control — scroll and select | ~$2 | **yes** |
| RGB LED (5 mm) + 150 Ω resistor | status colour (waiting / locked / ready) | ~$1 | optional |

The original also lists springs, a metal rod and 3D-printed parts — those are only for the pull-out desk drawer enclosure, not the electronics.

---

## Wiring

| Signal | Pico pin | Pico label |
| --- | --- | --- |
| OLED SDA | 1 | `GP0` |
| OLED SCL | 2 | `GP1` |
| OLED GND | 3 | `GND` |
| OLED VCC | 36 | `3V3(OUT)` |
| Encoder A (CLK) | 4 | `GP2` |
| Encoder B (DT) | 5 | `GP3` |
| Encoder switch (SW) | 6 | `GP4` |
| Encoder +/GND | 36 / 38 | `3V3` / `GND` |
| LED R / G / B *(opt)* | 7 / 9 / 10 | `GP5` / `GP6` / `GP7` |
| LED common *(opt)* | via 150 Ω | `GND` |

Pin numbers are set at the top of `code.py` — change them there if you wire it differently. If the menu scrolls the wrong way, swap `GP2` and `GP3`.

---

## Two changes from the original

**1. Bit-banged I²C, not hardware I²C.** The RP2040's hardware I²C block does not work with this SSD1306 — it finds the display in a scan, then NAKs every data byte. `code.py` uses `bitbangio.I2C`, which drives the same two pins in software and works. The full story is in [pico-ssd1306-guide](https://github.com/Galaviz1/pico-ssd1306-guide).

**2. Pins remapped.** The original's numbers are Waveshare RP2040-Zero board labels; these are Raspberry Pi Pico GPIO numbers.

---

## Installing

1. Flash **CircuitPython for the Raspberry Pi Pico** from [circuitpython.org/board/raspberry_pi_pico](https://circuitpython.org/board/raspberry_pi_pico/) — drag the `.uf2` onto the `RPI-RP2` drive. The board reboots as a `CIRCUITPY` drive.
2. From the matching [CircuitPython library bundle](https://circuitpython.org/libraries), copy into `CIRCUITPY/lib/`:
   - `adafruit_ssd1306.mpy`
   - `adafruit_hid/` (the whole folder)
3. Copy `font5x8.bin` (from the [Adafruit_CircuitPython_framebuf](https://github.com/adafruit/Adafruit_CircuitPython_framebuf/tree/main/examples) examples) to the drive root — `adafruit_ssd1306` needs it to draw text.
4. Copy everything from `device/` to the drive root: `boot.py`, `code.py`, `DB_Index.txt`, `PIN.txt`, and the `PWT_*.txt` files.
5. Eject and replug. It runs.

Target layout on the device:

```
CIRCUITPY/
├── boot.py            USB mode switch (drive hidden unless button held at boot)
├── code.py            the app
├── font5x8.bin        text font for the OLED
├── DB_Index.txt       list of databases:  Label|filename.txt
├── PIN.txt            the PIN (default 1234)
├── PWT_Demo.txt       a database:  Label|text-to-type
├── PWT_Bookmarks.txt
└── lib/
    ├── adafruit_ssd1306.mpy
    └── adafruit_hid/
```

---

## Using it

- **On power-up** it waits 3 minutes (so it can't inject anything into a PC that's still booting). Press the knob to skip.
- **Enter the PIN**: turn to change the highlighted digit, press to move on. Default `1234`, in `PIN.txt`.
- **Pick a database, then an entry.** Pressing an entry types its text into the focused field on the host.
- **Idle** blanks the display after 30 seconds.

### Editing your entries

Hold the encoder button **while plugging in the USB cable**. The `CIRCUITPY` drive stays visible and you edit the `.txt` files directly. Boot without holding it and the drive is hidden — the device is only a keyboard.

**File format**, one entry per line, label and payload split by `|`:

```
Example email|user@example.com
Full login|user@example.com	Demo-Passw0rd!
```

A literal **Tab** character in the payload types as Tab — so `user⇥pass` fills a username field, tabs to the password field, and types that too, in one press. (`PWT_Demo.txt` has a working example.) A newline in the file is not sent; keep each entry on one line.

---

## Security

This matches the original, which means: **plaintext files, one PIN, no encryption.**

- Anyone who reboots into edit mode, or reads the flash chip directly, sees every stored string. The PIN and the hidden drive are convenience, not protection.
- Hiding the drive (`boot.py`) stops it *mounting* by default; it does not encrypt anything.
- A USB keyboard can be watched by a keylogger already on the host — the device can't prevent that.
- Fine for: low-value logins, bookmarks, boilerplate text, a demo. **Not** fine for banking, email, or anything whose loss matters.

If you want it to deserve the name "vault," the next version should derive a key from the PIN and encrypt the payloads at rest, so edit mode and a chip read both yield ciphertext. That's a planned variant, not this one — and this file says so rather than pretending otherwise.

---

## Status

Written and logic-tested (parsing, menu paging, PIN check, Tab-in-payload) against stubbed CircuitPython modules. **Not yet run on hardware** — it needs the encoder, and a Pico that boots standalone. The Pico this was developed with has a stuck BOOTSEL button and enters the bootloader on every reset, so it can't run an always-plugged-in device like this; a healthy Pico is required for real use.

## Related

- [pico-ssd1306-guide](https://github.com/Galaviz1/pico-ssd1306-guide) — why bit-banged I²C, and the wiring
- [Original project](https://www.instructables.com/Password-Safe-Keyboard-Injector-Version-50/) by Smurfy_CH

## License

MIT — see [LICENSE](LICENSE). Original concept and reference code by Smurfy_CH.
