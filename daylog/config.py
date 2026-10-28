"""User-adjustable settings. (A Settings screen will edit these later.)

Hotkey format: modifiers + key, e.g. "Ctrl+Alt+D", "Ctrl+Shift+F9", "Win+Alt+L".
Modifiers: Ctrl, Alt, Shift, Win. At least one is required.
"""

QUICK_ADD_HOTKEY = "Ctrl+Alt+D"     # open the "Add accomplishment" popup
TOGGLE_CLOCK_HOTKEY = "Ctrl+Alt+T"  # Time In / Time Out

# Ask "Time In/Out now?" before the hotkey changes anything.
# Set to False if you'd rather it act instantly.
CONFIRM_CLOCK_HOTKEY = True

# Idle detection: while you're clocked in, this many minutes with no mouse or
# keyboard input counts as "away". When you come back, Daylog asks whether to
# keep or remove that time. Set to 0 to turn idle detection off.
IDLE_MINUTES = 10

# End-of-day reminder: if you're still clocked in at this time (24-hour HH:MM),
# Daylog asks whether to time out. Set to "" to turn it off.
END_OF_DAY_REMINDER = "18:00"
SNOOZE_MINUTES = 30