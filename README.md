**FY3200S Control GUI**

A small Python PySide6 GUI to control the FY3200S two-channel function generator over a serial (ASCII) protocol.

**Overview**
- **Purpose**: Provide an easy GUI for configuring both channels, triggers, sweeps and measurement polling.
- **Files**: `main.py` (GUI), `fy3200s.py` (protocol wrapper), `FY3200S.md` (protocol reference).

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
