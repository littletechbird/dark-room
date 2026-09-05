# Electron host sketch — OS exclude for Dark Room

**Product decision:** exclude **only the Dark Room `BrowserWindow`** from OS
capture. Do **not** disable screenshots globally for the whole agent host.

This is the production path Grok Bot / Cursor (or any Electron agent host)
should call so the Dark Room modal is omitted from screenshots, screen share,
and most app-level capture APIs on Windows and macOS.

## Minimal main-process snippet

```js
// main.js (Electron main process)
const { app, BrowserWindow } = require('electron')

let mainWindow
let darkRoomWindow

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    // Do NOT set content protection on the whole agent UI —
    // agents still need screenshots of the working desktop.
  })
  mainWindow.loadURL('https://agent-host.example/')
}

function openDarkRoom() {
  darkRoomWindow = new BrowserWindow({
    width: 480,
    height: 320,
    parent: mainWindow,
    modal: false,
    alwaysOnTop: true,
    show: false,
    title: 'Dark Room',
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  // *** OS-level exclude-from-capture for Dark Room only ***
  // Maps to:
  //   Windows: SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)
  //   macOS:   content protection / sharing exclusion APIs
  darkRoomWindow.setContentProtection(true) // Dark Room BrowserWindow only

  darkRoomWindow.once('ready-to-show', () => darkRoomWindow.show())
  darkRoomWindow.loadURL('app://dark-room/') // or file://…/dark-room.html

  darkRoomWindow.on('closed', () => {
    darkRoomWindow = null
    // Protection ends with the window; no global restore needed.
  })
}

app.whenReady().then(() => {
  createMainWindow()
  // e.g. ipcMain.handle('dark-room:open', () => openDarkRoom())
})
```

## Why this matters

| Layer | Role |
| --- | --- |
| `setContentProtection(true)` on Dark Room window | Real OS exclude (Win/macOS) |
| Python `CaptureShield` (Tk prototype) | Same intent for local demos; Linux stays UNAVAILABLE |
| Host geometry redaction (`darkroom.redact`) | Defense-in-depth when OS exclude is missing (Linux CI) |

On Linux Electron, `setContentProtection` may be a no-op depending on
compositor — keep redaction as fallback. Never rely on capture exclude alone:
agents must still only receive opaque `dr_sec_…` handles.

## References

- Electron docs: [`win.setContentProtection(enabled)`](https://www.electronjs.org/docs/latest/api/browser-window#winsetcontentprotectionenabled)
- Dark Room: [CAPTURE_NOTES.md](../CAPTURE_NOTES.md), `darkroom/capture.py`
