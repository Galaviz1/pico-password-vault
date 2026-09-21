# Runs before main.py. Start the USB keyboard here so USB re-enumerates exactly
# once, at power-on, rather than mid-session. builtin_driver=True keeps the REPL
# and the CIRCUITPY-style drive, so the board stays debuggable and its .txt
# databases stay editable over USB.
import hid
hid.start()
