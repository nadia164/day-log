# Daylog

A personal Time In / Time Out tracker for Windows with a per-day accomplishments log.
It runs from the system tray and responds to global hotkeys, so you can log time and
wins without leaving what you're working on.

Built with Python 3.10+ and PySide6 (Qt). Data is stored locally in SQLite.

---

## Install

Run **`Daylog-Setup-<version>.exe`** (see [Building the installer](#building-the-installer)).

- Installs for your user only, no admin rights needed, into
  `C:\Users\<you>\AppData\Local\Programs\Daylog`.
- Adds **Daylog** to the Start Menu; optionally a Desktop icon and **Start Daylog when
  I sign in**.
- Afterwards, open it like any app: Start Menu → **Daylog**. Right-click it →
  **Pin to taskbar** or **Pin to Start**.

**"Windows protected your PC"?** The installer isn't code-signed (a signing certificate
costs money), so SmartScreen warns about it. Click **More info → Run anyway**.

**Uninstall:** Settings → Apps → Installed apps → Daylog → Uninstall. This removes the app
and its startup entry. **Your data is kept** (see [Where your data is stored](#where-your-data-is-stored)),
so reinstalling picks up where you left off.

**Upgrade:** run a newer installer over the old one. Quit Daylog first; the installer
asks you to if it's still running.

## Run and stop

| Action | How |
|---|---|
| Start | Start Menu → **Daylog** (or the Desktop icon) |
| Stop | Right-click the tray icon → **Quit Daylog** |

**Only one Daylog runs at a time.** If it's already in the tray (for example from
Launch at startup), opening it again just brings up the window.

Closing the window with **X** does *not* quit. Daylog keeps running in the tray.
Quitting does not clock you out; your session continues and is restored on next launch.

---

## Development (running from source)

```powershell
cd daylog_py
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python main.py
```

Stop it with **Ctrl+C** in the terminal. If PowerShell blocks `activate`, run this once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

> Quit the installed Daylog before running from source: only one copy runs at a time,
> so `python main.py` would just bring up the installed one's window.

## Building the installer

One-time setup: install **Inno Setup 6** from https://jrsoftware.org/isdl.php
(or `winget install JRSoftware.InnoSetup`).

Then, with the venv active:

```powershell
python build.py
```

| Step | Output |
|---|---|
| Draws the app icon | `assets\daylog.ico` |
| Bundles Python + PySide6 + the app (PyInstaller) and removes unused Qt files | `dist\Daylog\Daylog.exe` (the whole `dist\Daylog` folder is the app) |
| Wraps it into an installer (Inno Setup) | `installer_output\Daylog-Setup-1.0.0.exe` |

- If Inno Setup isn't installed, the build stops after step 2. You can still run
  `dist\Daylog\Daylog.exe` directly.
- **New release:** bump `__version__` in `daylog/__init__.py`, then run `python build.py`.
- **Changed `config.py`** (hotkeys, idle minutes, reminder time)? The installed app has its
  own copy, so rebuild and reinstall for the change to apply.
- If the app ever fails silently, check `C:\Users\<you>\AppData\Roaming\Daylog\error.log`.

---

## Global hotkeys

These work from **any app**, even when the Daylog window is hidden.

| Hotkey | What it does |
|---|---|
| **Ctrl+Alt+T** | Opens the **Time In / Time Out confirmation** dialog |
| **Ctrl+Alt+D** | Opens the **Add accomplishment** popup |

The tray menu shows the active hotkeys next to each item.

To change them, edit `daylog/config.py`:

```python
QUICK_ADD_HOTKEY = "Ctrl+Alt+D"
TOGGLE_CLOCK_HOTKEY = "Ctrl+Alt+T"
CONFIRM_CLOCK_HOTKEY = True
```

- **Format:** one or more modifiers plus a key, joined with `+`.
- **Modifiers:** `Ctrl`, `Alt`, `Shift`, `Win` (at least one is required).
- **Keys:** `A`–`Z`, `0`–`9`, `F1`–`F24`, `Space`, `Enter`, `Tab`, `Insert`, `Delete`,
  `Home`, `End`, `PageUp`, `PageDown`.
- Restart the app after changing them.

If another app already uses a combo, Daylog shows a **"Shortcut unavailable"** popup
and that hotkey is left out of the tray menu. Pick a different combo in `config.py`.

> Global hotkeys are Windows-only. On other systems the app still runs, just without them.

---

## Dialogs and popups

### Time In / Time Out confirmation (Ctrl+Alt+T)

Asks before changing anything, so an accidental key press is harmless.

- When clocked out, it asks **"Time in now?"** and shows the time the new session will start.
- When clocked in, it asks **"Time out now?"** and shows when you clocked in and today's total.

| Key / button | Result |
|---|---|
| **Enter** or **Time In / Time Out** | Confirms, then shows the confirmation popup |
| **Esc** or **Cancel** | Does nothing |
| Pressing **Ctrl+Alt+T** again while it's open | Brings the dialog back to the front (does not toggle) |

To skip the question and toggle instantly, set `CONFIRM_CLOCK_HOTKEY = False` in `config.py`.

### Add accomplishment popup (Ctrl+Alt+D or tray menu)

A small always-on-top box for logging a win in a few seconds.

| Key / button | Result |
|---|---|
| Type, then **Enter** or **Add** | Saves the accomplishment and closes |
| **Esc** or **Cancel** | Closes without saving |

- Always saves to **today**, even if the main window is showing a past day.
- Empty text is ignored.

### "You were away" dialog (idle detection)

While you're clocked in, Daylog watches for mouse and keyboard activity. If there's
none for **10 minutes** (or the PC sleeps), it counts as "away". When you come back
and touch the mouse or keyboard, this dialog appears:

> **You were away for 25 min**
> No activity from 8:47 AM to 9:12 AM while you were clocked in.

| Key / button | Result |
|---|---|
| **Keep time**, **Enter**, **Esc**, or closing the dialog | Nothing changes; the away time stays in your session |
| **Remove, keep working** | Ends your session when you left (8:47) and starts a new one when you came back (9:12). You stay clocked in |
| **Time out at 8:47 AM** | Ends your session when you left. You're clocked out |

- The away time starts from your **last input**, not from when the dialog appears.
- Only one dialog shows at a time; idle detection pauses while it's open.
- Nothing happens while you're clocked out.
- After removing time, a corner popup confirms it, e.g. "Removed 25 min of away time".

Change the threshold (or turn it off with `0`) in `daylog/config.py`:

```python
IDLE_MINUTES = 10
```

> Tip for testing: set `IDLE_MINUTES = 1`, clock in, wait a minute without touching
> anything, then move the mouse.

> Watching a video or reading without touching anything also counts as idle, so just
> click **Keep time** when that happens.

### End-of-day reminder

If you're still clocked in at **6:00 PM**, this dialog appears:

> **It's 6:00 PM. Still working?**
> Clocked in since 9:05 AM. 08:12:40 worked today.
> No accomplishments logged today yet. *(only shown if you haven't logged any)*

| Button | Result |
|---|---|
| **Time Out** | Clocks you out now (with the corner popup) |
| **Remind me in 30 min** | Asks again in 30 minutes |
| **Keep working** | No more reminders today |
| Closing the dialog (X) or **Esc** | Same as **Remind me in 30 min** |

- It appears on top but **doesn't take keyboard focus**, so it can't swallow what you're
  typing in another app. Click a button to answer.
- It has no Enter shortcut on purpose: a stray Enter should never clock you out.
- Nothing happens if you're already clocked out.
- If you open Daylog after 6:00 PM while still clocked in, it shows within a few seconds.

Change it in `daylog/config.py` (24-hour time, `""` turns it off):

```python
END_OF_DAY_REMINDER = "18:00"
SNOOZE_MINUTES = 30
```

### Corner popup (notifications)

A small dark card in the bottom-right corner, above the taskbar. It never takes focus,
so you can keep typing.

| Message | When |
|---|---|
| **Clocked in** (green dot): "Started at 9:05 AM" | After confirming Time In from the hotkey |
| **Clocked out** (gray dot): "03:12:45 worked today" | After confirming Time Out from the hotkey |
| **Daylog is still running** | The first time you close the window in a run |
| **Shortcut unavailable** | A hotkey is already taken by another app |
| **Removed 25 min of away time** | After choosing to remove time in the "You were away" dialog |
| **Launch at startup is on / off** | After toggling it in the tray menu |

It fades out after a few seconds. Click it to dismiss it sooner.

---

## System tray

The tray icon is a clock. A **green dot** on it means you're clocked in.

| Action | Result |
|---|---|
| **Hover** | Status and today's total, e.g. "Clocked in · 02:14:09 today" (updates every second) |
| **Left-click** | Opens the main window |
| **Right-click** | Opens the menu below |

**Tray menu**

| Item | What it does |
|---|---|
| Status line | Shows whether you're clocked in and today's total (not clickable) |
| **Time In / Time Out** | Toggles right away (no confirmation, since clicking is deliberate) |
| **Add accomplishment…** | Opens the Add accomplishment popup |
| **Reports…** | Opens the Reports window |
| **Launch at startup** ✓ | Starts Daylog in the tray when you sign in to Windows (click to turn on/off) |
| **Open Daylog** | Shows the main window |
| **Quit Daylog** | Exits the app |

**Tip:** Windows may hide new tray icons behind the **^** arrow near the clock. Drag the
icon onto the taskbar, or turn it on under **Settings → Personalization → Taskbar →
Other system tray icons** (listed as **Daylog**, or **python.exe** when running from source).

### Launch at startup

Right-click the tray icon and check **Launch at startup**. From then on, Daylog starts
automatically when you sign in, **straight to the tray** (no window, no console). If you
were clocked in when you shut down, you're still clocked in.

- It adds a `Daylog` entry under
  `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run` (per-user, no admin).
- You can also turn it off in **Task Manager → Startup apps**.
- The installer offers the same option (**Start Daylog when I sign in**), and the
  uninstaller removes the entry.
- If Daylog moves (e.g. from running from source to the installed app), the entry
  updates itself the next time Daylog runs.
- To start minimized manually: `Daylog.exe --minimized` (or `python main.py --minimized`)

---

## Main window

| Area | What it does |
|---|---|
| Date header | The day you're viewing |
| **Reports** | Opens the Reports window |
| **‹** / **›** | Previous / next day (can't go past today) |
| **Today** | Jumps back to today (only shown when viewing a past day) |
| Clock card | Status, live "Worked today" timer, **Time In / Time Out** button, and the day's sessions |
| Accomplishments | Type and press **Enter** or **Add**; **✕** deletes an item |

**Window shortcuts** (only while the window is focused)

| Shortcut | What it does |
|---|---|
| **Alt+Left** | Previous day |
| **Alt+Right** | Next day |
| **Ctrl+R** | Open Reports |
| **Enter** in the accomplishments box | Adds the accomplishment |

Notes:

- **Time In** always starts a session on **today**, even if you're viewing a past day.
- Accomplishments added from the main window go to the **day on screen**, so you can
  backfill a day you forgot to log.
- A day can have several sessions (e.g. morning, then afternoon after lunch).
- If you forget to clock out, the status shows the original date, e.g.
  "Clocked in since Oct 22, 9:00 AM".

---

## Reports

Open with the **Reports** button in the main window, **Ctrl+R**, or the tray menu →
**Reports…**

| Area | What it shows |
|---|---|
| **← Home** | Closes Reports and brings the main window to the front |
| **Week / Month** | Switch the period (weeks run Monday–Sunday) |
| **‹ / ›** (or **Alt+Left / Alt+Right**) | Previous / next week or month (can't go past the current one) |
| **This week / This month** | Jump back to the current period (only shown when viewing an older one) |
| Stat tiles | **Total time**, **Days worked**, **Daily average** (over days you worked, so days off don't lower it), **Accomplishments** |
| Hours per day | Bar chart. **Hover** a day for exact time and accomplishment count. The longest day is labeled; today's label is bold |
| Accomplishments | Everything you logged, grouped by day, newest first |

It updates live: Time In/Out or adding an accomplishment (even from the hotkey) shows
up right away, and today's running session keeps counting.

### Export

Click **Export**:

| Option | Result |
|---|---|
| **Save as CSV…** | One row per day: date, weekday, hours (decimal, easy to `SUM` in Excel), time worked, sessions, first in, last out, accomplishments. Opens cleanly in Excel / Google Sheets |
| **Save as Markdown…** | A readable report: totals, then each day's hours, time range and accomplishments |
| **Copy as Markdown** | Same report, copied to the clipboard, ready to paste into Slack, Notion, GitHub or an email |

Files are suggested in your Documents folder as
`daylog-2026-10-19-to-2026-10-25.csv` (or `.md`).

Example Markdown:

```markdown
# Daylog report: Oct 19 – 25, 2026

**Total:** 35h 04m · **Days worked:** 5 · **Daily average:** 7h 00m · **Accomplishments:** 5

## Monday, October 19, 2026
_7h 53m · 8:31 AM – 5:24 PM_

- Pair-programmed the sync logic
```

| Shortcut (Reports window) | What it does |
|---|---|
| **Alt+Left / Alt+Right** | Previous / next period |
| **Ctrl+W** | Close the Reports window (the main window is underneath) |

---

## Where your data is stored

```
C:\Users\<you>\AppData\Roaming\Daylog\daylog.db
```

Every action is saved immediately. Deleting this file resets all data.

The installed app and `python main.py` share this same file, and uninstalling doesn't
touch it. Errors (if any) are logged next to it in `error.log`.

---

## Project structure

```
daylog_py/
├── main.py                       # entry point: wires window, tray, hotkeys, idle
├── build.py                      # builds Daylog.exe and the installer
├── packaging/
│   └── installer.iss             # Inno Setup installer definition
├── requirements.txt              # to run the app
├── requirements-dev.txt          # + PyInstaller, to build it
├── .gitignore                    # keeps build output and .venv out of Git
├── README.md
├── assets/, build/, dist/, installer_output/   # created by build.py (not in Git)
└── daylog/
    ├── __init__.py               # app version
    ├── config.py                 # hotkeys, confirmation, idle, reminder
    ├── models.py                 # WorkSession, Accomplishment (plain data)
    ├── database.py               # SQLite + migrations (the only file with SQL)
    ├── store.py                  # all app logic; UI calls this and listens to signals
    ├── main_window.py            # main window + day navigation
    ├── session_card.py           # clock card and sessions list
    ├── accomplishments_section.py
    ├── tray.py                   # tray icon, menu, hotkey actions
    ├── hotkeys.py                # Windows RegisterHotKey via ctypes
    ├── quick_add_dialog.py       # Add accomplishment popup
    ├── confirm_clock_dialog.py   # Time In/Out confirmation
    ├── idle.py                   # idle detection (Windows GetLastInputInfo)
    ├── idle_dialog.py            # "You were away" dialog
    ├── reports.py                # week/month ranges and totals (plain Python)
    ├── reports_window.py         # Reports window
    ├── bar_chart.py              # hours-per-day chart (QPainter)
    ├── export.py                 # CSV and Markdown export
    ├── reminder.py               # end-of-day reminder + dialog
    ├── startup.py                # launch at sign-in (registry Run key)
    ├── single_instance.py        # one Daylog at a time (local named pipe)
    ├── toast.py                  # corner popup
    ├── icons.py                  # app and tray icons (drawn in code)
    ├── theme.py                  # stylesheet
    ├── formatting.py             # time/date/duration text
    └── qt_utils.py               # small Qt helpers
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `No module named PySide6` | Activate the venv: `.venv\Scripts\activate` |
| `can't open file main.py` | You're in the wrong folder. Run `dir` and `cd` into `daylog_py` |
| `No module named 'PySide6.QTWidgets'` | Typo: it's `QtWidgets` (lowercase *t*) |
| "Shortcut unavailable" on start | Another app (or an older Daylog still running) owns the combo. Quit the old one from the tray, or change the hotkey in `config.py` |
| Hotkey does nothing | Make sure Daylog is running (tray icon visible) and wasn't started before the last update |
| Can't find the tray icon | Check the **^** overflow area near the clock |
| Leftover tray icon after stopping | You force-closed it (VS Code trash icon). Hover over the icon and it disappears. Use Ctrl+C or **Quit Daylog** instead |
| Opening Daylog shows nothing new | It's already in the tray; opening it again brings up that window. To load new code, **Quit Daylog** first |
| "Windows protected your PC" when installing | The installer isn't code-signed. Click **More info → Run anyway** |
| Installer says Daylog is running | Right-click the tray icon → **Quit Daylog**, then click Retry |
| `python build.py` skips the installer | Install Inno Setup 6 (`winget install JRSoftware.InnoSetup`) and run it again |
| Packaged app does nothing / closes | Check `AppData\Roaming\Daylog\error.log` |
| Didn't start at sign-in | Check the tray menu shows **Launch at startup** ✓, and that it's enabled in Task Manager → Startup apps |
| "You were away" pops up while watching a video | Expected (no input = idle). Click **Keep time**, or raise `IDLE_MINUTES` |

---

## Roadmap

- [x] Time In / Time Out with live timer
- [x] Accomplishments per day
- [x] SQLite storage and day navigation
- [x] System tray
- [x] Global hotkeys with confirmation
- [x] Idle detection (keep or remove away time)
- [x] Launch on startup and end-of-day reminder
- [x] Reports (weekly/monthly) with CSV/Markdown export
- [x] Packaging: Daylog.exe, app icon, installer
- [ ] Auto-update (check GitHub Releases for a newer installer)
- [ ] Later: standup/weekly status generator, calendar heatmap