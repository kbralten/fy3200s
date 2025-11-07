"""
Main application for the FY3200S GUI.
"""
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QGroupBox, QVBoxLayout, QHBoxLayout, QTabWidget
)
from PySide6.QtCore import QTimer, Qt, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QPolygonF
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
        # Use a tabbed UI: Control + ArbWave
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.control_tab = QWidget()
        self.tabs.addTab(self.control_tab, "Control")
        # ArbWave tab for drawing arbitrary waveforms
        self.arb_tab = ArbWaveTab(self)
        self.tabs.addTab(self.arb_tab, "ArbWave")
        self.device = None
        self.init_ui()
        self.scan_ports()

    def init_ui(self):
        control_layout = QGridLayout(self.control_tab)

        # Channels
        self.ch1 = ChannelWidget("CH1", self)
        self.ch2 = ChannelWidget("CH2", self)
        control_layout.addWidget(self.ch1, 0, 0)
        control_layout.addWidget(self.ch2, 0, 1)
        

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
        control_layout.addWidget(connection_group, 2, 0, 1, 3)

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
        control_layout.addWidget(sweep_group, 1, 1)

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
        control_layout.addWidget(trigger_group, 0, 2)

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
        control_layout.addWidget(measure_group, 1, 2)
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

class ArbWaveTab(QWidget):
    def __init__(self, main_window: MainWindow):
        super().__init__()
        self.main_window = main_window
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Toolbar row
        tools = QHBoxLayout()
        self.pen_btn = QPushButton("Pen")
        self.line_btn = QPushButton("Line")
        self.undo_btn = QPushButton("Undo")
        self.redo_btn = QPushButton("Redo")
        self.pan_btn = QPushButton("Pan")
        self.grid_btn = QPushButton("Grid")
        self.grid_btn.setCheckable(True)
        self.grid_btn.setChecked(True)
        self.snap_btn = QPushButton("Snap")
        self.snap_btn.setCheckable(True)
        self.snap_btn.setChecked(False)
        self.zoom_in_btn = QPushButton("+")
        self.zoom_out_btn = QPushButton("-")
        self.fit_btn = QPushButton("Fit")

        for w in [self.pen_btn, self.line_btn, self.undo_btn, self.redo_btn, self.pan_btn,
                self.grid_btn, self.snap_btn, self.zoom_in_btn, self.zoom_out_btn, self.fit_btn]:
            tools.addWidget(w)

        layout.addLayout(tools)

        # Canvas
        self.canvas = ArbWaveCanvas()
        layout.addWidget(self.canvas, 1)

        # Bank selection + upload
        bank_row = QHBoxLayout()
        bank_row.addWidget(QLabel("Bank:"))
        self.bank_combo = QComboBox()
        self.bank_combo.addItems(["Arb 1", "Arb 2", "Arb 3", "Arb 4"])
        bank_row.addWidget(self.bank_combo)
        self.upload_btn = QPushButton("Upload to Bank")
        bank_row.addWidget(self.upload_btn)
        layout.addLayout(bank_row)

        # Wire controls
        self.pen_btn.clicked.connect(lambda: self.canvas.set_tool('pen'))
        self.line_btn.clicked.connect(lambda: self.canvas.set_tool('line'))
        self.undo_btn.clicked.connect(lambda: self.canvas.undo())
        self.redo_btn.clicked.connect(lambda: self.canvas.redo())
        self.pan_btn.clicked.connect(lambda: self.canvas.set_tool('pan'))
        self.grid_btn.toggled.connect(self.canvas.set_show_grid)
        self.snap_btn.toggled.connect(self.canvas.set_snap)
        self.zoom_in_btn.clicked.connect(lambda: self.canvas.zoom(1.25))
        self.zoom_out_btn.clicked.connect(lambda: self.canvas.zoom(0.8))
        self.fit_btn.clicked.connect(self.canvas.fit_view)
        self.upload_btn.clicked.connect(self._upload_waveform)
        # wire canvas to update undo/redo button state
        self.canvas.set_undo_redo_buttons(self.undo_btn, self.redo_btn)

    def get_points(self):
        return self.canvas.points[:]

    def _upload_waveform(self):
        # use main window device
        dev = self.main_window.device
        if not (dev and dev.ser and dev.ser.is_open):
            print("Not connected: cannot upload arbitrary waveform")
            return
        bank = self.bank_combo.currentIndex() + 1
        points = self.get_points()
        # Progress dialog
        dlg = ProgressDialog(self, f"Uploading to Bank {bank}")
        dlg.show()
        def progress(sent, total):
            dlg.set_progress(sent, total)
        ok = dev.upload_arbitrary(bank, points, progress_cb=progress)
        dlg.finish(ok)
        if ok:
            print("Upload completed")
        else:
            print("Upload failed")


class ArbWaveCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.points = [0.0] * 2048  # amplitude in [-1, 1]
        self.tool = 'pen'
        self.show_grid = True
        self.snap = False
        self.zoom_x = 1.0
        self.zoom_y = 1.0
        self.x0 = 0.0  # left sample index of view
        self._last_draw_idx = None
        self._line_start = None  # (idx, val)
        self._panning = False
        self._last_mouse_x = 0
        self._cursor_pos = None
        # Undo/Redo stacks: each action is {'idxs': [...], 'old': [...], 'new': [...]}
        self._undo_stack = []
        self._redo_stack = []
        self._max_undo = 200
        self._current_action = None  # dict mapping idx->old_value while drawing
        self._undo_btn = None
        self._redo_btn = None

    # --- Config ---
    def set_tool(self, name: str):
        self.tool = name
        if name != 'pan':
            self._panning = False
        if name != 'line':
            self._line_start = None
        # finalize any ongoing current action if tool changes
        if self._current_action is not None and len(self._current_action) > 0:
            self._finalize_current_action()

    def set_show_grid(self, on: bool):
        self.show_grid = on
        self.update()

    def set_snap(self, on: bool):
        self.snap = on

    def zoom(self, factor: float):
        # Zoom around center of view
        cx = self.x0 + self.view_width_samples() / 2.0
        self.zoom_x = max(1.0, min(16.0, self.zoom_x * factor))
        vw = self.view_width_samples()
        self.x0 = max(0.0, min(2048 - vw, cx - vw / 2.0))
        self.update()

    def fit_view(self):
        self.zoom_x = 1.0
        self.x0 = 0.0
        self.zoom_y = 1.0
        self.update()

    # --- Helpers ---
    def view_width_samples(self) -> float:
        return 2048.0 / self.zoom_x

    def index_to_x(self, idx: float) -> float:
        w = self.width()
        return (idx - self.x0) / max(1e-6, self.view_width_samples()) * w

    def value_to_y(self, val: float) -> float:
        h = self.height()
        return h * 0.5 - (val * self.zoom_y) * (h * 0.45)

    def x_to_index(self, x: float) -> int:
        idx = self.x0 + (x / max(1, self.width())) * self.view_width_samples()
        idx = int(max(0, min(2047, round(idx if not self.snap else round(idx / 8) * 8))) )
        return idx

    def y_to_value(self, y: float) -> float:
        h = max(1, self.height())
        val = (h * 0.5 - y) / (h * 0.45)
        val = val / max(1e-6, self.zoom_y)
        if self.snap:
            step = 0.05
            val = round(val / step) * step
        return float(max(-1.0, min(1.0, val)))

    # --- Painting ---
    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(18, 24, 33))

        # Grid
        if self.show_grid:
            grid_pen = QPen(QColor(45, 55, 70))
            grid_pen.setWidth(1)
            p.setPen(grid_pen)
            # vertical grid (16 columns in view)
            cols = 16
            for c in range(cols + 1):
                idx = self.x0 + c / cols * self.view_width_samples()
                x = self.index_to_x(idx)
                p.drawLine(int(x), 0, int(x), self.height())
            # horizontal grid
            rows = 8
            for r in range(rows + 1):
                y = self.value_to_y((r / rows) * 2 - 1)
                p.drawLine(0, int(y), self.width(), int(y))

        # Axis
        axis_pen = QPen(QColor(90, 110, 140))
        axis_pen.setWidth(1)
        p.setPen(axis_pen)
        p.drawLine(0, int(self.value_to_y(0.0)), self.width(), int(self.value_to_y(0.0)))

        # Waveform polyline
        wave_pen = QPen(QColor(64, 164, 255))
        wave_pen.setWidth(2)
        p.setPen(wave_pen)
        poly = QPolygonF()
        start = int(self.x0)
        end = int(min(2047, self.x0 + self.view_width_samples()))
        for i in range(start, end + 1):
            x = self.index_to_x(i)
            y = self.value_to_y(self.points[i])
            poly.append(QPointF(x, y))
        if len(poly) > 1:
            p.drawPolyline(poly)

        # Cursor readout
        if self._cursor_pos is not None:
            cx, cy = self._cursor_pos
            p.setPen(QPen(QColor(200, 200, 200, 120)))
            p.drawLine(int(cx), 0, int(cx), self.height())
            p.drawLine(0, int(cy), self.width(), int(cy))
            idx = self.x_to_index(cx)
            val = self.y_to_value(cy)
            txt = f"t={idx/2048:.3f}s  V={val:.2f}"
            p.setPen(QPen(QColor(220, 220, 220)))
            p.drawText(10, 20, txt)

    # Undo/Redo API
    def _finalize_current_action(self):
        if not self._current_action:
            self._current_action = None
            return
        # build action record
        idxs = sorted(self._current_action.keys())
        old = [self._current_action[i] for i in idxs]
        new = [self.points[i] for i in idxs]
        action = {'idxs': idxs, 'old': old, 'new': new}
        self._undo_stack.append(action)
        # cap undo stack
        if len(self._undo_stack) > self._max_undo:
            self._undo_stack.pop(0)
        # clear redo stack on new action
        self._redo_stack.clear()
        self._current_action = None
        self._update_undo_redo_buttons()

    def undo(self):
        if not self._undo_stack:
            return
        action = self._undo_stack.pop()
        # apply old values
        for i, v in zip(action['idxs'], action['old']):
            self.points[i] = v
        self._redo_stack.append(action)
        self.update()
        self._update_undo_redo_buttons()

    def redo(self):
        if not self._redo_stack:
            return
        action = self._redo_stack.pop()
        for i, v in zip(action['idxs'], action['new']):
            self.points[i] = v
        self._undo_stack.append(action)
        self.update()
        self._update_undo_redo_buttons()

    def set_undo_redo_buttons(self, undo_btn, redo_btn):
        self._undo_btn = undo_btn
        self._redo_btn = redo_btn
        self._update_undo_redo_buttons()

    def _update_undo_redo_buttons(self):
        if self._undo_btn is not None:
            self._undo_btn.setEnabled(bool(self._undo_stack))
        if self._redo_btn is not None:
            self._redo_btn.setEnabled(bool(self._redo_stack))

    # --- Mouse ---
    def mousePressEvent(self, e):
        self._cursor_pos = (e.position().x(), e.position().y())
        if e.button() == Qt.LeftButton:
            if self.tool == 'pan':
                self._panning = True
                self._last_mouse_x = e.position().x()
            elif self.tool == 'line':
                idx = self.x_to_index(e.position().x())
                val = self.y_to_value(e.position().y())
                self._line_start = (idx, val)
            elif self.tool == 'pen':
                # start a fresh current action for the stroke
                self._current_action = {}
                self._apply_draw_at(e.position().x(), e.position().y())
                self._last_draw_idx = self.x_to_index(e.position().x())
        self.update()

    def mouseMoveEvent(self, e):
        self._cursor_pos = (e.position().x(), e.position().y())
        if self.tool == 'pan' and self._panning:
            dx = e.position().x() - self._last_mouse_x
            self._last_mouse_x = e.position().x()
            vw = self.view_width_samples()
            self.x0 -= dx / max(1, self.width()) * vw
            self.x0 = max(0.0, min(2048 - vw, self.x0))
            self.update()
            return
        if e.buttons() & Qt.LeftButton and self.tool == 'pen':
            self._apply_draw_at(e.position().x(), e.position().y(), interpolate=True)
            self.update()

    def mouseReleaseEvent(self, e):
        if self.tool == 'pan' and self._panning and e.button() == Qt.LeftButton:
            self._panning = False
        elif self.tool == 'line' and e.button() == Qt.LeftButton and self._line_start is not None:
            i0, v0 = self._line_start
            i1 = self.x_to_index(e.position().x())
            v1 = self.y_to_value(e.position().y())
            # record old values for the affected indices before drawing
            # start a temporary action map
            self._current_action = {}
            self._draw_line_segment(i0, v0, i1, v1)
            # finalize action
            self._finalize_current_action()
            self._line_start = None
            self.update()
            return
        # finalize pen stroke action on release
        if self.tool == 'pen' and self._current_action is not None:
            self._finalize_current_action()

    def leaveEvent(self, _):
        self._cursor_pos = None
        self.update()

    # --- Drawing helpers ---
    def _apply_draw_at(self, x, y, interpolate=False):
        idx = self.x_to_index(x)
        # Only drawing behavior for pen tool; eraser removed
        val = self.y_to_value(y)
        # record old value
        if self._current_action is not None and idx not in self._current_action:
            self._current_action[idx] = self.points[idx]
        if interpolate and self._last_draw_idx is not None and self._last_draw_idx != idx:
            self._draw_line_segment(self._last_draw_idx, self.points[self._last_draw_idx], idx, val)
        else:
            self.points[idx] = val
        self._last_draw_idx = idx

    def _draw_line_segment(self, i0, v0, i1, v1):
        if i0 == i1:
            idx = max(0, min(2047, i0))
            if self._current_action is not None and idx not in self._current_action:
                self._current_action[idx] = self.points[idx]
            self.points[idx] = max(-1.0, min(1.0, v1))
            return
        if i0 > i1:
            i0, i1 = i1, i0
            v0, v1 = v1, v0
        length = i1 - i0
        for k in range(length + 1):
            t = k / max(1, length)
            val = v0 * (1 - t) + v1 * t
            idx = i0 + k
            if 0 <= idx < 2048:
                if self._current_action is not None and idx not in self._current_action:
                    self._current_action[idx] = self.points[idx]
                self.points[idx] = max(-1.0, min(1.0, val))
        # end ArbWaveCanvas

    # (device control methods were mistakenly placed here in previous patch)

    # end of ArbWaveCanvas class

    # NOTE: ArbWaveCanvas intentionally does not contain device control methods.
# Simple progress dialog
from PySide6.QtWidgets import QDialog, QProgressBar

class ProgressDialog(QDialog):
    def __init__(self, parent=None, title="Progress"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        v = QVBoxLayout(self)
        self.label = QLabel("Starting...")
        v.addWidget(self.label)
        self.bar = QProgressBar()
        self.bar.setRange(0, 4096)
        v.addWidget(self.bar)
        self.cancel_btn = QPushButton("Cancel")
        v.addWidget(self.cancel_btn)
        self._cancelled = False
        self.cancel_btn.clicked.connect(self._on_cancel)

    def _on_cancel(self):
        self._cancelled = True
        self.label.setText("Cancelled")

    def cancelled(self):
        return self._cancelled

    def set_progress(self, sent, total):
        self.bar.setMaximum(total)
        self.bar.setValue(sent)
        pct = (sent / total) * 100 if total else 0
        self.label.setText(f"{sent}/{total} bytes ({pct:.1f}%)")
        QApplication.processEvents()

    def finish(self, ok: bool):
        if ok and not self._cancelled:
            self.label.setText("Done")
        elif not ok and not self._cancelled:
            self.label.setText("Failed")
        QApplication.processEvents()
        QTimer.singleShot(800, self.accept)

    
    
# Reinsert MainWindow device-related methods (moved out from ArbWaveCanvas)
def _mw_scan_ports(self: MainWindow):
    self.port_combo.clear()
    ports = serial.tools.list_ports.comports()
    for port in ports:
        self.port_combo.addItem(port.device)

def _mw_toggle_connection(self: MainWindow):
    if self.device and self.device.ser and self.device.ser.is_open:
        self.device.disconnect()
        self.connect_button.setText("Connect")
        self.port_status_label.setText("Disconnected")
        self.status_label.setText("")
    else:
        port = self.port_combo.currentText()
        if port:
            self.device = FY3200S(port)
            if self.device.connect():
                self.connect_button.setText("Disconnect")
                self.port_status_label.setText(port)
                model = self.device.get_model()
                self.status_label.setText(model or "")
            else:
                self.device = None

def _mw_update_frequency(self: MainWindow, channel: int):
    if self.device:
        widget = self.ch1 if channel == 1 else self.ch2
        try:
            freq_hz = float(widget.freq_input.text())
            freq_chz = int(freq_hz * 100)
            self.device.set_frequency(channel, freq_chz)
        except ValueError:
            print("Invalid frequency")

def _mw_update_amplitude(self: MainWindow, channel: int):
    if self.device:
        widget = self.ch1 if channel == 1 else self.ch2
        try:
            ampl_v = float(widget.ampl_input.text())
            self.device.set_amplitude(channel, ampl_v)
        except ValueError:
            print("Invalid amplitude")

def _mw_update_offset(self: MainWindow, channel: int):
    if self.device:
        widget = self.ch1 if channel == 1 else self.ch2
        try:
            offset_v = float(widget.bias_input.text())
            self.device.set_offset(channel, offset_v)
        except ValueError:
            print("Invalid offset")

def _mw_update_waveform(self: MainWindow, channel: int):
    if self.device:
        widget = self.ch1 if channel == 1 else self.ch2
        wave_id = widget.wave_combo.currentIndex()
        self.device.set_waveform(channel, wave_id)

def _mw_update_duty_cycle(self: MainWindow, channel: int):
    if self.device:
        widget = self.ch1 if channel == 1 else self.ch2
        try:
            duty_percent = float(widget.duty_input.text())
            duty_val = int(duty_percent * 10)
            self.device.set_duty_cycle(channel, duty_val)
        except ValueError:
            print("Invalid duty cycle")

def _mw_update_phase(self: MainWindow):
    if self.device:
        try:
            phase_deg = int(self.ch2.skewing_input.text())
            self.device.set_phase(phase_deg)
        except ValueError:
            print("Invalid phase")

def _mw_set_trigger_source(self: MainWindow, source: int):
    if not (self.device and self.device.ser and self.device.ser.is_open):
        print("Not connected: cannot set trigger source")
        return
    self.device.set_trigger_source(source)

def _mw_set_trigger_cycles(self: MainWindow):
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

def _mw_start_lin_sweep(self: MainWindow):
    if not (self.device and self.device.ser and self.device.ser.is_open):
        print("Not connected: cannot start sweep")
        return
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
    self.device.set_sweep_mode(0)
    self.device.start_sweep()

def _mw_start_log_sweep(self: MainWindow):
    if not (self.device and self.device.ser and self.device.ser.is_open):
        print("Not connected: cannot start sweep")
        return
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

def _mw_stop_sweep(self: MainWindow):
    if not (self.device and self.device.ser and self.device.ser.is_open):
        print("Not connected: cannot stop sweep")
        return
    self.device.stop_sweep()

def _mw_toggle_measure_frequency(self: MainWindow):
    if self._freq_timer.isActive():
        self._freq_timer.stop()
        self.measure_button.setText("Start")
    else:
        if not (self.device and self.device.ser and self.device.ser.is_open):
            print("Not connected: cannot start frequency measurement")
            return
        self._freq_timer.start()
        self.measure_button.setText("Stop")

def _mw_toggle_measure_count(self: MainWindow):
    if self._count_timer.isActive():
        self._count_timer.stop()
        self.measure_count_button.setText("Start")
    else:
        if not (self.device and self.device.ser and self.device.ser.is_open):
            print("Not connected: cannot start count measurement")
            return
        self._count_timer.start()
        self.measure_count_button.setText("Stop")

def _mw_poll_measure_frequency(self: MainWindow):
    if not (self.device and self.device.ser and self.device.ser.is_open):
        return
    resp = self.device.measure_frequency()
    if resp is None:
        return
    import re
    m = re.search(r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", resp)
    if not m:
        self.measure_freq_input.setText(resp)
        return
    try:
        val_chz = float(m.group(0))
    except ValueError:
        self.measure_freq_input.setText(resp)
        return
    val_hz = val_chz / 100.0
    self.measure_freq_input.setText(f"{val_hz:.2f}")

def _mw_poll_measure_count(self: MainWindow):
    if not (self.device and self.device.ser and self.device.ser.is_open):
        return
    resp = self.device.measure_count()
    if resp is None:
        return
    import re
    m = re.search(r"[-+]?[0-9]+", resp)
    if not m:
        self.measure_count_input.setText(resp)
        return
    try:
        n = int(m.group(0))
    except ValueError:
        self.measure_count_input.setText(resp)
        return
    self.measure_count_input.setText(str(n))

def _mw_clear_count(self: MainWindow):
    if not (self.device and self.device.ser and self.device.ser.is_open):
        print("Not connected: cannot clear count")
        return
    self.device.clear_count()

# Bind methods back onto MainWindow
MainWindow.scan_ports = _mw_scan_ports
MainWindow.toggle_connection = _mw_toggle_connection
MainWindow.update_frequency = _mw_update_frequency
MainWindow.update_amplitude = _mw_update_amplitude
MainWindow.update_offset = _mw_update_offset
MainWindow.update_waveform = _mw_update_waveform
MainWindow.update_duty_cycle = _mw_update_duty_cycle
MainWindow.update_phase = _mw_update_phase
MainWindow.set_trigger_source = _mw_set_trigger_source
MainWindow.set_trigger_cycles = _mw_set_trigger_cycles
MainWindow.start_lin_sweep = _mw_start_lin_sweep
MainWindow.start_log_sweep = _mw_start_log_sweep
MainWindow.stop_sweep = _mw_stop_sweep
MainWindow.toggle_measure_frequency = _mw_toggle_measure_frequency
MainWindow.toggle_measure_count = _mw_toggle_measure_count
MainWindow._poll_measure_frequency = _mw_poll_measure_frequency
MainWindow._poll_measure_count = _mw_poll_measure_count
MainWindow.clear_count = _mw_clear_count


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
