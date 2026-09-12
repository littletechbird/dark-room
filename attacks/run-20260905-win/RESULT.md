# Windows desk PC OS-exclude smoke (2026-09-05)

## Method
WinForms window with lime canary `CANARY_DARKROOM_SECRET_7f3a`.
Capture via GDI `Graphics.CopyFromScreen` (same class of API many screen tools use).

## Results
| Condition | SetWindowDisplayAffinity | Lime canary pixels in crop |
| --- | --- | --- |
| WITH `WDA_EXCLUDEFROMCAPTURE` (0x11) | setOk=True | **0** |
| WITHOUT exclude (control) | n/a | **1602** |

## Verdict
**OS exclude WORKS on the local Windows desk** for GDI screen capture: API engages and canary text does not appear in the screenshot. Control run proves the canary is visible when exclude is off.

Note: not a proof against all capture paths (some layered APIs / cameras). Still the real OS mechanism we asked Grok Bot host to use (also via Electron `setContentProtection`).
