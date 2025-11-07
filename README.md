**FY3200S Control GUI**

A small Python PySide6 GUI to control the FY3200S two-channel function generator over a serial (ASCII) protocol.

**Overview**
- **Purpose**: Provide an easy GUI for configuring both channels, triggers, sweeps and measurement polling.
- **Files**: `main.py` (GUI), `fy3200s.py` (protocol wrapper), `FY3200S.md` (protocol reference).

<img width="941" height="481" alt="image" src="https://github.com/user-attachments/assets/efc55ded-4454-4547-9695-c83c8cb3468e" />

**Requirements**
- **Python**: 3.8+ (use a virtual environment).
- **Packages**: Listed in `requirements.txt` (at minimum `pyserial` and `PySide6`).

**Quick Setup**
- Create & activate a venv (or conda env) and install deps:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

- Run the GUI:

```powershell
python main.py
```

**Usage**
- Select the serial `Port:` and click `Connect`.
- Configure CH1 and CH2: frequency (Hz), amplitude (V), offset (V), waveform and duty.
- Triggers: set source and cycles.
- Sweep: set `Begin` and `End` in Hz and `Time` in seconds; press `LIN-SWEEP` or `LOG-SWEEP` to start. The app uses the device sweep sequence: `bb` (begin), `be` (end), `bt` (time), `bm` (mode), `br` (run).
- Measurements:
  - Frequency: press `Start` to begin polling once per second (sends `ce`). The returned value is interpreted as centi-Hz (0.01 Hz) and displayed in Hz with two decimals.
  - Count: press `Start` to begin polling once per second (sends `cc`) and view integer counts. Press `Clear` to send `bc` and zero the device counter.

  **Arbitrary Waveform Editor (ArbWave)**
  - The `ArbWave` tab provides a 2048-sample arbitrary waveform editor and uploader.
  - Canvas: draw a waveform sampled to 2048 points, amplitude range [-1.0, 1.0].
  - Tools: `Pen` (freehand strokes), `Line` (draw straight segments), `Pan` (move view).
  - View controls: toggle `Grid`, enable `Snap` (quantize vertical steps), `+`/`-` to zoom horizontally, and `Fit` to reset view.
  - Undo/Redo: per-stroke undo/redo is supported; the toolbar `Undo`/`Redo` buttons revert or reapply the last edits.
  - Banks & Upload: select one of four banks (`Arb 1..4`) and press `Upload to Bank` to send the waveform to the device.
    - Upload protocol: the GUI converts the 2048 float samples into the device's 12-bit binary format (4096 bytes, LSB-first) and performs the documented handshake (erase, begin, then data transfer). A progress dialog shows transfer progress.
    - Requirements: the device must be connected (`Connect`) before uploading. The upload shows progress; canceling the dialog will mark the operation cancelled in the UI, but mid-transfer abort behavior depends on the device and current implementation (the dialog can request cancel, but in-flight transfers may or may not be interrupted immediately).


**Protocol notes**
- Commands are ASCII lines terminated with LF (`\n`). The UI sends a short 100 ms pause after each command to avoid overrun of the device parser.
- Measured frequency responses are in centi-Hz; the GUI converts to Hz by dividing by 100 before display.
- Sweep setup uses 9-digit cHz values for `bb`/`be` as implemented in `fy3200s.py`.

**Troubleshooting**
- If PySide6 fails to import on Windows with a DLL error, check your PATH for other Python/Qt installations (e.g., Miniconda). A Qt DLL (like `Qt6Core.dll`) on PATH from another distribution can break the venv import. Use an isolated venv or a fresh conda env to avoid conflicts.
- If measurements don't update, verify the device is connected, the serial port is correct, and no other program is holding the port.

**Development / Extending**
- `fy3200s.py` implements helpers for common commands (frequency, amplitude, offset, waveform, duty, triggers, sweep methods and measurement helpers).
- the codebase includes placeholders to add register save/recall if you want to implement it.

**License & Author**
- GPLv3
