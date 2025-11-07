"""
FY3200S Serial Communication Protocol Handler
"""
import serial
import time

class FY3200S:
    def __init__(self, port: str):
        self.port = port
        self.ser = None

    def connect(self):
        """Connects to the serial port."""
        try:
            self.ser = serial.Serial(
                self.port,
                baudrate=9600,
                timeout=1
            )
            return True
        except serial.SerialException as e:
            print(f"Error connecting to {self.port}: {e}")
            return False

    def disconnect(self):
        """Disconnects from the serial port."""
        if self.ser and self.ser.is_open:
            self.ser.close()

    def send_command(self, command: str):
        """Sends a command to the device."""
        if self.ser and self.ser.is_open:
            full_command = command + '\n'
            self.ser.write(full_command.encode('ascii'))
            # Small delay to avoid overrunning the device's parser/uart buffer.
            # The device needs a short pause between ASCII commands.
            time.sleep(0.1)
            # No reliable response for most commands, so we don't read.
        else:
            print("Serial port not connected.")

    def read_response(self):
        """Reads a response from the device."""
        if self.ser and self.ser.is_open:
            return self.ser.readline().decode('ascii').strip()
        else:
            print("Serial port not connected.")
            return None

    def get_model(self) -> str | None:
        """Reads the machine model."""
        self.send_command("a")
        return self.read_response()

    def set_waveform(self, channel: int, wave_id: int):
        """Sets the waveform for a channel."""
        prefix = 'b' if channel == 1 else 'd'
        self.send_command(f"{prefix}w{wave_id}")

    def set_frequency(self, channel: int, freq_chz: int):
        """Sets the frequency for a channel in cHz."""
        prefix = 'b' if channel == 1 else 'd'
        self.send_command(f"{prefix}f{freq_chz}")

    def set_amplitude(self, channel: int, ampl_volts: float):
        """Sets the amplitude for a channel in Volts."""
        prefix = 'b' if channel == 1 else 'd'
        self.send_command(f"{prefix}a{ampl_volts:.2f}")

    def set_offset(self, channel: int, offset_volts: float):
        """Sets the DC offset for a channel in Volts."""
        prefix = 'b' if channel == 1 else 'd'
        # Device accepts two decimal places for offset (e.g. 0.25)
        self.send_command(f"{prefix}o{offset_volts:.2f}")

    def set_duty_cycle(self, channel: int, duty: int):
        """Sets the duty cycle for a channel (0.1% resolution)."""
        prefix = 'b' if channel == 1 else 'd'
        self.send_command(f"{prefix}d{duty:03d}")

    def set_phase(self, phase_deg: int):
        """Sets the phase for the deputy channel in degrees."""
        self.send_command(f"dp{phase_deg:03d}")

    def set_trigger_source(self, source: int):
        """Sets the trigger source: 0=Manual, 1=External, 2=CH2."""
        if source in (0, 1, 2):
            self.send_command(f"tt{source}")

    def set_trigger_cycles(self, cycles: int):
        """Sets the number of trigger cycles. Sends as 7-digit padded number."""
        try:
            n = int(cycles)
        except (TypeError, ValueError):
            return
        # Format to 7 digits as observed in protocol traces
        self.send_command(f"tn{n:07d}")

    # --- Sweep control ---
    def set_sweep_mode(self, mode: int):
        """Set sweep scan mode: 0 = linear, 1 = logarithmic."""
        if mode in (0, 1):
            self.send_command(f"bm{mode}")

    def set_sweep_time(self, seconds: int):
        """Set sweep time in seconds (1-99)."""
        try:
            t = int(seconds)
        except (TypeError, ValueError):
            return
        # Format as two digits (btxx)
        self.send_command(f"bt{t:02d}")

    def start_sweep(self):
        """Start sweep operation."""
        self.send_command("br1")

    def stop_sweep(self):
        """Stop/pause sweep operation."""
        self.send_command("br0")

    def save_register(self, reg: int):
        """Save current settings to a register (bsn). reg is 0-99."""
        try:
            n = int(reg)
        except (TypeError, ValueError):
            return
        if n < 0 or n > 99:
            return
        # send without padding (bs1 or bs00 both accepted by device)
        self.send_command(f"bs{n}")

    def set_sweep_begin(self, freq_chz: int):
        """Set sweep beginning frequency in cHz (0.01Hz) as 9-digit value."""
        try:
            n = int(freq_chz)
        except (TypeError, ValueError):
            return
        # send as 9-digit padded cHz
        self.send_command(f"bb{n:09d}")

    def set_sweep_end(self, freq_chz: int):
        """Set sweep end frequency in cHz (0.01Hz) as 9-digit value."""
        try:
            n = int(freq_chz)
        except (TypeError, ValueError):
            return
        self.send_command(f"be{n:09d}")

    # --- Arbitrary waveform upload (binary protocol) ---
    def _write_bytes(self, data: bytes):
        if not (self.ser and self.ser.is_open):
            raise RuntimeError("Serial port not connected")
        self.ser.write(data)

    def _read_exact(self, n: int) -> bytes:
        if not (self.ser and self.ser.is_open):
            raise RuntimeError("Serial port not connected")
        buf = bytearray()
        while len(buf) < n:
            chunk = self.ser.read(n - len(buf))
            if not chunk:
                break
            buf.extend(chunk)
        return bytes(buf)

    def upload_arbitrary(self, bank: int, samples, progress_cb=None) -> bool:
        """Upload 2048-point arbitrary waveform to specified bank (1-4).

        samples: iterable of 2048 floats in [-1,1] or ints already in [0,4095].
        progress_cb(optional): callable(bytes_sent:int, total_bytes:int) -> None
        """
        if not (self.ser and self.ser.is_open):
            print("Not connected: cannot upload waveform")
            return False
        if bank not in (1, 2, 3, 4):
            print("Invalid bank; must be 1..4")
            return False
        # Prepare data buffer (2048 samples, 16-bit little-endian; use 12-bit range 0..4095)
        vals = []
        for v in samples:
            if isinstance(v, (int,)):
                iv = int(v)
            else:
                try:
                    fv = float(v)
                except Exception:
                    fv = 0.0
                iv = int(round((max(-1.0, min(1.0, fv)) + 1.0) * 2047.5))
            iv = max(0, min(4095, iv))
            vals.append(iv)
            if len(vals) == 2048:
                break
        if len(vals) != 2048:
            # pad or error; pad with midline
            vals += [2048] * (2048 - len(vals))
        # Build bytes (LSB first)
        data = bytearray()
        for iv in vals:
            data.append(iv & 0xFF)
            data.append((iv >> 8) & 0xFF)

        total = len(data)  # 4096
        def report(sent):
            if progress_cb:
                try:
                    progress_cb(sent, total)
                except Exception:
                    pass

        # Flush any pending input
        try:
            self.ser.reset_input_buffer()
        except Exception:
            pass

        # Step 1: Initialize upload: send magic + 0xA5, expect 'X'
        self._write_bytes(b'DDS_WAVE' + bytes([0xA5]))
        if self._read_exact(1) != b'X':
            print("Handshake failed (A5 -> X)")
            return False

        # Step 2: Erase memory slot: magic + 0xF{bank}, expect 'SE'
        self._write_bytes(b'DDS_WAVE' + bytes([0xF0 + bank]))
        if self._read_exact(2) != b'SE':
            print("Erase ack failed (expected 'SE')")
            return False

        # Step 3: Begin upload: magic + 0x0{bank}, expect 'W'
        self._write_bytes(b'DDS_WAVE' + bytes([0x00 + bank]))
        if self._read_exact(1) != b'W':
            print("Begin upload ack failed (expected 'W')")
            return False

        # Step 4: Send data with 'X' ack per byte; send in small chunks
        sent = 0
        chunk_size = 8 # 8 bytes per chunk seems to balance speed/reliability
        while sent < total:
            chunk = data[sent: sent + chunk_size]
            self._write_bytes(chunk)
            # Wait for same number of 'X' bytes
            acked = 0
            while acked < len(chunk):
                a = self._read_exact(len(chunk) - acked)
                if not a:
                    print("Timed out waiting for acks")
                    return False
                # Count only 'X' bytes
                acked += sum(1 for b in a if b == 0x58)
            sent += len(chunk)
            report(sent)

        return True

    # --- Measurement commands ---
    def measure_frequency(self) -> str | None:
        """Request the measured frequency. Sends `ce` and returns the device response as string."""
        if not (self.ser and self.ser.is_open):
            print("Serial port not connected.")
            return None
        self.send_command("ce")
        return self.read_response()

    def measure_count(self) -> str | None:
        """Request the measured count. Sends `cc` and returns the device response as string."""
        if not (self.ser and self.ser.is_open):
            print("Serial port not connected.")
            return None
        self.send_command("cc")
        return self.read_response()

    def clear_count(self):
        """Clear the count measurement by sending `bc`. No response expected."""
        if not (self.ser and self.ser.is_open):
            print("Serial port not connected.")
            return
        self.send_command("bc")
