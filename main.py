"""
Main application for the FY3200S GUI.
"""
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QGroupBox, QVBoxLayout, QHBoxLayout
)
from PySide6.QtCore import QTimer
import serial.tools.list_ports
from fy3200s import FY3200S

class ChannelWidget(QWidget):
    """Widget for a single channel's controls."""
    def __init__(self, channel_name: str, main_window):
        super().__init__()
        self.channel_name = channel_name
        self.main_window = main_window
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        group_box = QGroupBox(self.channel_name)
        group_layout = QGridLayout()

        # Frequency
        group_layout.addWidget(QLabel("FREQ"), 0, 0)
        self.freq_input = QLineEdit("10000.00")
        group_layout.addWidget(self.freq_input, 0, 1)
        group_layout.addWidget(QLabel("Hz"), 0, 2)

        # Amplitude
        group_layout.addWidget(QLabel("AMPL"), 1, 0)
        self.ampl_input = QLineEdit("10.00")
        group_layout.addWidget(self.ampl_input, 1, 1)
        group_layout.addWidget(QLabel("V"), 1, 2)

        # Bias
        group_layout.addWidget(QLabel("BIAS"), 2, 0)
        self.bias_input = QLineEdit("0.00")
        group_layout.addWidget(self.bias_input, 2, 1)
        group_layout.addWidget(QLabel("V"), 2, 2)

        # Waveform
        group_layout.addWidget(QLabel("WAVE"), 3, 0)
        self.wave_combo = QComboBox()
        # Use different waveform lists depending on channel (Main vs Deputy)
        if self.channel_name == "CH1":
            # Main channel waveform list (IDs 0..20)
            self.wave_combo.addItems([
                "Sine",                 # 0
                "Square",               # 1
                "Pulse",                # 2
                "Triangle",             # 3
                "Sawtooth",             # 4
                "Reverse Sawtooth",     # 5
                "DC",                   # 6
                "Lorentz Pulse",        # 7 (Preset 1)
                "Multi-tone",           # 8 (Preset 2)
                "Periodic Random",      # 9 (Preset 3)
                "ECG",                  #10 (Preset 4)
                "Trapezoidal Pulse",    #11 (Preset 5)
                "Sinc Pulse",           #12 (Preset 6)
                "Narrow Pulse",         #13 (Preset 7)
                "Gaussian White Noise", #14 (Preset 8)
                "AM",                   #15 (Preset 9)
                "FM",                   #16 (Preset 10)
                "Arbitrary 1",          #17
                "Arbitrary 2",          #18
                "Arbitrary 3",          #19
                "Arbitrary 4",          #20
            ])
        else:
            # Deputy channel waveform list (IDs 0..19)
            self.wave_combo.addItems([
                "Sine",                 # 0
                "Square",               # 1
                "Triangle",             # 2
                "Sawtooth",             # 3
                "Reverse Sawtooth",     # 4
                "DC",                   # 5
                "Lorentz Pulse",        # 6 (Preset 1)
                "Multi-tone",           # 7 (Preset 2)
                "Periodic Random",      # 8 (Preset 3)
                "ECG",                  # 9 (Preset 4)
                "Trapezoidal Pulse",    #10 (Preset 5)
                "Sinc Pulse",           #11 (Preset 6)
                "Narrow Pulse",         #12 (Preset 7)
                "Gaussian White Noise", #13 (Preset 8)
                "AM",                   #14 (Preset 9)
                "FM",                   #15 (Preset 10)
                "Arbitrary 1",          #16
                "Arbitrary 2",          #17
                "Arbitrary 3",          #18
                "Arbitrary 4",          #19
            ])
        group_layout.addWidget(self.wave_combo, 3, 1, 1, 2)

        # Duty
        duty_layout = QHBoxLayout()
        group_layout.addLayout(duty_layout, 4, 0, 1, 3)
        duty_layout.addWidget(QLabel("Duty"))
        self.duty_input = QLineEdit("50.0")
        duty_layout.addWidget(self.duty_input)
        duty_layout.addWidget(QLabel("%"))

        if self.channel_name == "CH1":
            # Reference Phase
            ref_phase_layout = QHBoxLayout()
            group_layout.addLayout(ref_phase_layout, 5, 0, 1, 3)
            ref_phase_layout.addWidget(QLabel("Reference Phase"))
            self.ref_phase_input = QLineEdit("0")
            ref_phase_layout.addWidget(self.ref_phase_input)
            ref_phase_layout.addWidget(QLabel("°"))
        else:
            # Skewing
            skewing_layout = QHBoxLayout()
            group_layout.addLayout(skewing_layout, 5, 0, 1, 3)
            skewing_layout.addWidget(QLabel("Skewing"))
            self.skewing_input = QLineEdit("0")
            skewing_layout.addWidget(self.skewing_input)
            skewing_layout.addWidget(QLabel("°"))

        group_box.setLayout(group_layout)
        main_layout = QVBoxLayout()
        main_layout.addWidget(group_box)
        self.setLayout(main_layout)

    def connect_signals(self):
        channel_num = 1 if self.channel_name == "CH1" else 2
        self.freq_input.editingFinished.connect(lambda: self.main_window.update_frequency(channel_num))
        self.ampl_input.editingFinished.connect(lambda: self.main_window.update_amplitude(channel_num))
        self.bias_input.editingFinished.connect(lambda: self.main_window.update_offset(channel_num))
        self.wave_combo.currentIndexChanged.connect(lambda: self.main_window.update_waveform(channel_num))
        self.duty_input.editingFinished.connect(lambda: self.main_window.update_duty_cycle(channel_num))
        if self.channel_name == "CH2":
            self.skewing_input.editingFinished.connect(self.main_window.update_phase)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FY3200S Control")
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.device = None
        self.init_ui()
        self.scan_ports()

    def init_ui(self):
        main_layout = QGridLayout(self.central_widget)

        # Channels
        self.ch1 = ChannelWidget("CH1", self)
        self.ch2 = ChannelWidget("CH2", self)
        main_layout.addWidget(self.ch1, 0, 0)
        main_layout.addWidget(self.ch2, 0, 1)
        

        # Connection
        connection_group = QGroupBox("Port Connect")
        connection_layout = QHBoxLayout()
        self.port_combo = QComboBox()
        connection_layout.addWidget(QLabel("Port:"))
        connection_layout.addWidget(self.port_combo)
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection)
        connection_layout.addWidget(self.connect_button)
        connection_group.setLayout(connection_layout)
        # span across three columns now that we have a third column for Trigger
        main_layout.addWidget(connection_group, 2, 0, 1, 3)

        # --- Bottom Sections ---

        # (Save section removed — not implemented)

        # Sweep Frequency
        sweep_group = QGroupBox("Sweep Frequency")
        sweep_layout = QGridLayout()
        sweep_layout.addWidget(QLabel("Begin"), 0, 0)
        self.sweep_begin_input = QLineEdit("100.00")
        sweep_layout.addWidget(self.sweep_begin_input, 0, 1)
        sweep_layout.addWidget(QLabel("Hz"), 0, 2)
        self.lin_sweep_button = QPushButton("LIN-SWEEP")
        sweep_layout.addWidget(self.lin_sweep_button, 0, 3)
        sweep_layout.addWidget(QLabel("End"), 1, 0)
        self.sweep_end_input = QLineEdit("10000.00")
        sweep_layout.addWidget(self.sweep_end_input, 1, 1)
        sweep_layout.addWidget(QLabel("Hz"), 1, 2)
        self.log_sweep_button = QPushButton("LOG-SWEEP")
        sweep_layout.addWidget(self.log_sweep_button, 1, 3)
        sweep_layout.addWidget(QLabel("Time"), 2, 0)
        self.sweep_time_input = QLineEdit("2")
        sweep_layout.addWidget(self.sweep_time_input, 2, 1)
        sweep_layout.addWidget(QLabel("S"), 2, 2)
        self.sweep_stop_button = QPushButton("Stop")
        sweep_layout.addWidget(self.sweep_stop_button, 2, 3)
        # connect sweep buttons
        self.lin_sweep_button.clicked.connect(self.start_lin_sweep)
        self.log_sweep_button.clicked.connect(self.start_log_sweep)
        self.sweep_stop_button.clicked.connect(self.stop_sweep)
        sweep_group.setLayout(sweep_layout)
        main_layout.addWidget(sweep_group, 1, 1)

        # Trigger (placed in the top-right column)
        trigger_group = QGroupBox("Trigger")
        trigger_layout = QVBoxLayout()
        cycles_layout = QHBoxLayout()
        cycles_layout.addWidget(QLabel("Cycles"))
        self.trigger_cycles_input = QLineEdit("1000000")
        cycles_layout.addWidget(self.trigger_cycles_input)
        trigger_layout.addLayout(cycles_layout)
        trigger_buttons_layout = QGridLayout()
        self.trigger_manual_button = QPushButton("Manual")
        self.trigger_external_button = QPushButton("External")
        self.trigger_ch2_button = QPushButton("CH2")
        trigger_buttons_layout.addWidget(self.trigger_manual_button, 0, 0)
        trigger_buttons_layout.addWidget(self.trigger_external_button, 0, 1)
        trigger_buttons_layout.addWidget(self.trigger_ch2_button, 1, 0, 1, 2)
        trigger_layout.addLayout(trigger_buttons_layout)
        trigger_group.setLayout(trigger_layout)
        # place Trigger beside CH1/CH2
        main_layout.addWidget(trigger_group, 0, 2)

        # Measure (placed under Trigger)
        measure_group = QGroupBox("Measure")
        measure_layout = QGridLayout()
        measure_layout.addWidget(QLabel("Frequency"), 0, 0)
        self.measure_freq_input = QLineEdit("0")
        measure_layout.addWidget(self.measure_freq_input, 0, 1)
        measure_layout.addWidget(QLabel("Hz"), 0, 2)
        # Start/Stop toggle for frequency measurement
        self.measure_button = QPushButton("Start")
        measure_layout.addWidget(self.measure_button, 0, 3)

        measure_layout.addWidget(QLabel("Count"), 1, 0)
        self.measure_count_input = QLineEdit("0")
        measure_layout.addWidget(self.measure_count_input, 1, 1)
        # Start/Stop toggle for count measurement
        self.measure_count_button = QPushButton("Start")
        measure_layout.addWidget(self.measure_count_button, 1, 3)
        # Clear count (sends `bc`)
        self.measure_clear_button = QPushButton("Clear")
        measure_layout.addWidget(self.measure_clear_button, 1, 4)
        measure_group.setLayout(measure_layout)
        main_layout.addWidget(measure_group, 1, 2)
        # Connect trigger buttons to actions
        self.trigger_manual_button.clicked.connect(lambda: self.set_trigger_source(0))
        self.trigger_external_button.clicked.connect(lambda: self.set_trigger_source(1))
        self.trigger_ch2_button.clicked.connect(lambda: self.set_trigger_source(2))
        self.trigger_cycles_input.editingFinished.connect(self.set_trigger_cycles)

        # Timers for periodic measurement polling
        self._freq_timer = QTimer()
        self._freq_timer.setInterval(1000)
        self._freq_timer.timeout.connect(self._poll_measure_frequency)

        self._count_timer = QTimer()
        self._count_timer.setInterval(1000)
        self._count_timer.timeout.connect(self._poll_measure_count)

        # Connect measurement controls
        self.measure_button.clicked.connect(self.toggle_measure_frequency)
        self.measure_count_button.clicked.connect(self.toggle_measure_count)
        self.measure_clear_button.clicked.connect(self.clear_count)

        # Status Bar
        status_bar = self.statusBar()
        self.status_label = QLabel("")
        self.port_status_label = QLabel("Disconnected")
        status_bar.addWidget(self.status_label)
        status_bar.addPermanentWidget(self.port_status_label)

    def scan_ports(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(port.device)

    def toggle_connection(self):
        if self.device and self.device.ser and self.device.ser.is_open:
            # Disconnect and clear status
            self.device.disconnect()
            self.connect_button.setText("Connect")
            self.port_status_label.setText("Disconnected")
            self.status_label.setText("")
        else:
            port = self.port_combo.currentText()
            if port:
                self.device = FY3200S(port)
                if self.device.connect():
                    # Connected: show port and read model
                    self.connect_button.setText("Disconnect")
                    self.port_status_label.setText(port)
                    model = self.device.get_model()
                    if model:
                        self.status_label.setText(model)
                    else:
                        self.status_label.setText("")
                else:
                    self.device = None

    def update_frequency(self, channel: int):
        if self.device:
            widget = self.ch1 if channel == 1 else self.ch2
            try:
                freq_hz = float(widget.freq_input.text())
                freq_chz = int(freq_hz * 100)
                self.device.set_frequency(channel, freq_chz)
            except ValueError:
                print("Invalid frequency")

    def update_amplitude(self, channel: int):
        if self.device:
            widget = self.ch1 if channel == 1 else self.ch2
            try:
                ampl_v = float(widget.ampl_input.text())
                self.device.set_amplitude(channel, ampl_v)
            except ValueError:
                print("Invalid amplitude")

    def update_offset(self, channel: int):
        if self.device:
            widget = self.ch1 if channel == 1 else self.ch2
            try:
                offset_v = float(widget.bias_input.text())
                self.device.set_offset(channel, offset_v)
            except ValueError:
                print("Invalid offset")

    def update_waveform(self, channel: int):
        if self.device:
            widget = self.ch1 if channel == 1 else self.ch2
            wave_id = widget.wave_combo.currentIndex()
            self.device.set_waveform(channel, wave_id)

    def update_duty_cycle(self, channel: int):
        if self.device:
            widget = self.ch1 if channel == 1 else self.ch2
            try:
                duty_percent = float(widget.duty_input.text())
                duty_val = int(duty_percent * 10)
                self.device.set_duty_cycle(channel, duty_val)
            except ValueError:
                print("Invalid duty cycle")

    def update_phase(self):
        if self.device:
            try:
                phase_deg = int(self.ch2.skewing_input.text())
                self.device.set_phase(phase_deg)
            except ValueError:
                print("Invalid phase")

    # --- Trigger helpers ---
    def set_trigger_source(self, source: int):
        if not (self.device and self.device.ser and self.device.ser.is_open):
            print("Not connected: cannot set trigger source")
            return
        self.device.set_trigger_source(source)

    def set_trigger_cycles(self):
        if not (self.device and self.device.ser and self.device.ser.is_open):
            print("Not connected: cannot set trigger cycles")
            return
        text = self.trigger_cycles_input.text()
        try:
            cycles = int(text)
        except ValueError:
            print("Invalid cycles value")
            return
        self.device.set_trigger_cycles(cycles)

    # --- Sweep handlers ---
    def start_lin_sweep(self):
        if not (self.device and self.device.ser and self.device.ser.is_open):
            print("Not connected: cannot start sweep")
            return
        # Set start/stop frequencies from Begin/End fields and save to registers
        try:
            begin_hz = float(self.sweep_begin_input.text())
            end_hz = float(self.sweep_end_input.text())
            t = int(self.sweep_time_input.text())
        except ValueError:
            print("Invalid sweep Begin/End/Time value")
            return
        # convert Hz to cHz (0.01Hz units)
        begin_chz = int(begin_hz * 100)
        end_chz = int(end_hz * 100)
        # Use correct sweep setup: bb (begin), be (end), bt (time), bm (mode), br1 (start)
        self.device.set_sweep_begin(begin_chz)
        self.device.set_sweep_end(end_chz)
        self.device.set_sweep_time(t)
        self.device.set_sweep_mode(0)
        self.device.start_sweep()

    def start_log_sweep(self):
        if not (self.device and self.device.ser and self.device.ser.is_open):
            print("Not connected: cannot start sweep")
            return
        # Set start/stop frequencies from Begin/End fields and save to registers
        try:
            begin_hz = float(self.sweep_begin_input.text())
            end_hz = float(self.sweep_end_input.text())
            t = int(self.sweep_time_input.text())
        except ValueError:
            print("Invalid sweep Begin/End/Time value")
            return
        begin_chz = int(begin_hz * 100)
        end_chz = int(end_hz * 100)
        self.device.set_sweep_begin(begin_chz)
        self.device.set_sweep_end(end_chz)
        self.device.set_sweep_time(t)
        self.device.set_sweep_mode(1)
        self.device.start_sweep()

    def stop_sweep(self):
        if not (self.device and self.device.ser and self.device.ser.is_open):
            print("Not connected: cannot stop sweep")
            return
        self.device.stop_sweep()

    # --- Measurement polling ---
    def toggle_measure_frequency(self):
        if self._freq_timer.isActive():
            self._freq_timer.stop()
            self.measure_button.setText("Start")
        else:
            if not (self.device and self.device.ser and self.device.ser.is_open):
                print("Not connected: cannot start frequency measurement")
                return
            self._freq_timer.start()
            self.measure_button.setText("Stop")

    def toggle_measure_count(self):
        if self._count_timer.isActive():
            self._count_timer.stop()
            self.measure_count_button.setText("Start")
        else:
            if not (self.device and self.device.ser and self.device.ser.is_open):
                print("Not connected: cannot start count measurement")
                return
            self._count_timer.start()
            self.measure_count_button.setText("Stop")

    def _poll_measure_frequency(self):
        if not (self.device and self.device.ser and self.device.ser.is_open):
            return
        resp = self.device.measure_frequency()
        if resp is None:
            return
        # Extract the first numeric token from the response and format as Hz
        import re
        m = re.search(r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", resp)
        if not m:
            # non-numeric response — display raw
            self.measure_freq_input.setText(resp)
            return
        try:
            # Device returns frequency in centi-Hz (0.01 Hz units)
            val_chz = float(m.group(0))
        except ValueError:
            self.measure_freq_input.setText(resp)
            return
        # Convert centi-Hz to Hz and display with two decimals
        val_hz = val_chz / 100.0
        self.measure_freq_input.setText(f"{val_hz:.2f}")

    def _poll_measure_count(self):
        if not (self.device and self.device.ser and self.device.ser.is_open):
            return
        resp = self.device.measure_count()
        if resp is None:
            return
        # Extract integer from response
        import re
        m = re.search(r"[-+]?[0-9]+", resp)
        if not m:
            # non-numeric response — display raw
            self.measure_count_input.setText(resp)
            return
        try:
            n = int(m.group(0))
        except ValueError:
            self.measure_count_input.setText(resp)
            return
        self.measure_count_input.setText(str(n))

    def clear_count(self):
        if not (self.device and self.device.ser and self.device.ser.is_open):
            print("Not connected: cannot clear count")
            return
        self.device.clear_count()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
