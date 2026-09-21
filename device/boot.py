# boot.py runs once, before code.py, and is the only place USB modes can be set.
#
# Two modes, chosen by the encoder button at power-on:
#
#   button HELD while plugging in  -> the CIRCUITPY drive stays visible to the
#                                     host, so you can edit the .txt databases.
#   button NOT held (normal)       -> the drive is hidden and the device is a
#                                     USB keyboard only. Passwords are not
#                                     exposed as a mountable drive.
#
# Hiding the drive is convenience, not security: the files are still plaintext
# in flash and anyone who reboots into edit mode (or reads the chip) can see
# them. See the README.
import board
import digitalio
import storage

BUTTON_PIN = board.GP4  # encoder push-switch

btn = digitalio.DigitalInOut(BUTTON_PIN)
btn.switch_to_input(pull=digitalio.Pull.UP)  # pressed reads False

if btn.value:
    # Not pressed: hide the drive from the host. code.py can still read it.
    storage.disable_usb_drive()
# Pressed: do nothing, leaving the drive host-writable for editing.

btn.deinit()
