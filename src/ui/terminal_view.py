from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QTextEdit, QPushButton, QLineEdit,
    QFrame, QLabel, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import pyqtSlot, pyqtSignal, Qt, QEvent
from PyQt6.QtGui import QTextCursor
from typing import List

from src.ui.styles import (
    Colors,
    Fonts,
    InteractivePatterns,
    MAIN_CONTAINER_STYLE,
    TERMINAL_OUTPUT_STYLE,
    HEADER_TITLE_STYLE,
    INPUT_CONTAINER_STYLE,
    INPUT_CONTAINER_ACTIVE_STYLE,
    INPUT_CONTAINER_SECURE_STYLE,
    INPUT_FIELD_STYLE,
    BTN_ICON_STYLE,
    BTN_STOP_STYLE,
    ACTION_BTN_YES_STYLE,
    ACTION_BTN_NO_STYLE,
    get_badge_style
)


class TerminalView(QWidget):
    """
    SENTINEL Terminal - Clean Professional UI
    
    Features:
    - Integrated action buttons for Yes/No prompts
    - Command history with Up/Down arrows
    - Secure password input mode
    - Tool integration with real-time output streaming
    """
    
    sig_command_requested = pyqtSignal(str)
    
    MODE_IDLE = "idle"
    MODE_RUNNING = "running"
    MODE_PASSWORD = "password"
    MODE_YESNO = "yesno"
    MODE_TOOL_RUNNING = "tool_running"
    
    def __init__(self, process_manager=None, coordinator=None, parent=None):
        super().__init__(parent)
        self._manager = process_manager
        self._coordinator = coordinator
        self._current_mode = self.MODE_IDLE
        self._current_tool_id = None
        
        self._command_history = []
        self._history_index = 0
        self._max_buffer_lines = 10000  # Maksimum satır sayısı
        
        self.setStyleSheet(MAIN_CONTAINER_STYLE)
        self._setup_ui()
        self._connect_signals()
        self._set_mode(self.MODE_IDLE)
    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(8)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 0, 4, 8)
        header_layout.setSpacing(12)
        
        self._title = QLabel("SENTINEL // TERMINAL")
        self._title.setStyleSheet(HEADER_TITLE_STYLE)
        header_layout.addWidget(self._title)
        
        header_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        self._status_badge = QLabel("Ready")
        self._status_badge.setStyleSheet(get_badge_style("default"))
        header_layout.addWidget(self._status_badge)
        
        self._btn_clear = QPushButton("⌫")
        self._btn_clear.setStyleSheet(BTN_ICON_STYLE)
        self._btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_clear.setToolTip("Clear")
        self._btn_clear.clicked.connect(self._clear_output)
        header_layout.addWidget(self._btn_clear)
        
        main_layout.addLayout(header_layout)
        
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setStyleSheet(TERMINAL_OUTPUT_STYLE)
        main_layout.addWidget(self._output, stretch=1)
        
        self._input_container = QFrame()
        self._input_container.setStyleSheet(INPUT_CONTAINER_STYLE)
        self._input_container.setFixedHeight(54)
        
        container_layout = QHBoxLayout(self._input_container)
        container_layout.setContentsMargins(8, 8, 8, 10)
        container_layout.setSpacing(10)
        
        self._prompt_icon = QLabel("›")
        self._prompt_icon.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-family: {Fonts.MONO}; font-size: 18px; font-weight: bold;")
        self._prompt_icon.setFixedWidth(16)
        container_layout.addWidget(self._prompt_icon)
        
        self._input_field = QLineEdit()
        self._input_field.setPlaceholderText("Enter command...")
        self._input_field.setStyleSheet(INPUT_FIELD_STYLE)
        self._input_field.returnPressed.connect(self._on_submit)
        self._input_field.textChanged.connect(self._on_text_changed)
        self._input_field.installEventFilter(self)
        container_layout.addWidget(self._input_field, stretch=1)
        
        self._action_container = QWidget()
        self._action_container.setFixedHeight(36)
        action_layout = QHBoxLayout(self._action_container)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(10)
        
        self._btn_yes = QPushButton("✓  YES")
        self._btn_yes.setStyleSheet(ACTION_BTN_YES_STYLE)
        self._btn_yes.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_yes.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._btn_yes.clicked.connect(lambda: self._send_response("y"))
        action_layout.addWidget(self._btn_yes)
        
        self._btn_no = QPushButton("✕  NO")
        self._btn_no.setStyleSheet(ACTION_BTN_NO_STYLE)
        self._btn_no.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_no.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._btn_no.clicked.connect(lambda: self._send_response("n"))
        action_layout.addWidget(self._btn_no)
        
        self._action_container.setVisible(False)
        container_layout.addWidget(self._action_container, stretch=1)
        
        self._btn_stop = QPushButton("■")
        self._btn_stop.setStyleSheet(BTN_STOP_STYLE)
        self._btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_stop.setToolTip("Stop")
        self._btn_stop.clicked.connect(self._stop_process)
        self._btn_stop.setVisible(False)
        container_layout.addWidget(self._btn_stop)
        
        main_layout.addWidget(self._input_container)
    
    def eventFilter(self, obj, event):
        """Handle keyboard events for command history."""
        if obj == self._input_field and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Up:
                self._history_up()
                return True
            elif event.key() == Qt.Key.Key_Down:
                self._history_down()
                return True
        return super().eventFilter(obj, event)
    
    def _history_up(self):
        """Navigate to older command."""
        if not self._command_history:
            return
        if self._history_index < len(self._command_history):
            self._history_index += 1
            cmd = self._command_history[-self._history_index]
            self._input_field.setText(cmd)
    
    def _history_down(self):
        """Navigate to newer command."""
        if self._history_index > 1:
            self._history_index -= 1
            cmd = self._command_history[-self._history_index]
            self._input_field.setText(cmd)
        elif self._history_index == 1:
            self._history_index = 0
            self._input_field.clear()
    
    def _connect_signals(self):
        if self._manager:
            self._manager.sig_output_stream.connect(self._on_output)
            self._manager.sig_process_finished.connect(self._on_finished)
            self._manager.sig_auth_failed.connect(self._on_auth_failed)
        
        if self._coordinator:
            self._coordinator.tool_started.connect(self._on_tool_started)
            self._coordinator.tool_completed.connect(self._on_tool_completed)
            self._coordinator.tool_error.connect(self._on_tool_error)
            # Subscribe to tool output from integrated tools
            if hasattr(self._coordinator.manager, 'signals'):
                self._coordinator.manager.signals.tool_finished.connect(self._on_tool_output)
    
    def _set_mode(self, mode: str):
        """Set UI mode."""
        self._current_mode = mode
        
        self._input_field.setEchoMode(QLineEdit.EchoMode.Normal)
        self._prompt_icon.setVisible(True)
        self._input_field.setVisible(True)
        self._action_container.setVisible(False)
        
        if mode == self.MODE_IDLE:
            self._input_container.setStyleSheet(INPUT_CONTAINER_STYLE)
            self._input_field.setPlaceholderText("Enter command...")
            self._prompt_icon.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-family: {Fonts.MONO}; font-size: 18px; font-weight: bold;")
            self._btn_stop.setVisible(False)
            self._status_badge.setText("Ready")
            self._status_badge.setStyleSheet(get_badge_style("default"))
            
        elif mode == self.MODE_RUNNING:
            self._input_container.setStyleSheet(INPUT_CONTAINER_ACTIVE_STYLE)
            self._input_field.setPlaceholderText("Send input...")
            self._prompt_icon.setStyleSheet(f"color: {Colors.ACCENT_PRIMARY}; font-family: {Fonts.MONO}; font-size: 18px; font-weight: bold;")
            self._btn_stop.setVisible(True)
            self._status_badge.setText("Running")
            self._status_badge.setStyleSheet(get_badge_style("info"))
            
        elif mode == self.MODE_TOOL_RUNNING:
            self._input_container.setStyleSheet(INPUT_CONTAINER_ACTIVE_STYLE)
            self._input_field.setPlaceholderText("Tool running...")
            self._input_field.setEnabled(False)
            self._prompt_icon.setStyleSheet(f"color: {Colors.ACCENT_PRIMARY}; font-family: {Fonts.MONO}; font-size: 18px; font-weight: bold;")
            self._btn_stop.setVisible(True)
            self._status_badge.setText("Tool Running")
            self._status_badge.setStyleSheet(get_badge_style("info"))
            
        elif mode == self.MODE_PASSWORD:
            self._input_container.setStyleSheet(INPUT_CONTAINER_SECURE_STYLE)
            self._input_field.setPlaceholderText("Enter password...")
            self._input_field.setEchoMode(QLineEdit.EchoMode.Password)
            self._prompt_icon.setStyleSheet(f"color: {Colors.SECURE}; font-family: {Fonts.MONO}; font-size: 18px; font-weight: bold;")
            self._btn_stop.setVisible(True)
            self._status_badge.setText("[SECURE]")
            self._status_badge.setStyleSheet(get_badge_style("secure"))
            
        elif mode == self.MODE_YESNO:
            self._input_container.setStyleSheet(INPUT_CONTAINER_ACTIVE_STYLE)
            self._prompt_icon.setVisible(False)
            self._input_field.setVisible(False)
            self._action_container.setVisible(True)
            self._btn_stop.setVisible(True)
            self._status_badge.setText("Confirm")
            self._status_badge.setStyleSheet(get_badge_style("warning"))
    
    def _on_text_changed(self, text: str):
        """Visual feedback on typing."""
        if self._current_mode == self.MODE_IDLE:
            if text:
                self._input_container.setStyleSheet(INPUT_CONTAINER_ACTIVE_STYLE)
                self._prompt_icon.setStyleSheet(f"color: {Colors.ACCENT_PRIMARY}; font-family: {Fonts.MONO}; font-size: 18px; font-weight: bold;")
            else:
                self._input_container.setStyleSheet(INPUT_CONTAINER_STYLE)
                self._prompt_icon.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-family: {Fonts.MONO}; font-size: 18px; font-weight: bold;")
    
    def _detect_prompt(self, text: str):
        """Detect interactive prompts."""
        if InteractivePatterns.is_password_prompt(text):
            self._set_mode(self.MODE_PASSWORD)
        elif InteractivePatterns.is_yesno_prompt(text):
            self._set_mode(self.MODE_YESNO)
    
    def _on_submit(self):
        """Handle input submission."""
        text = self._input_field.text()
        if not text:
            return
        
        if self._current_mode == self.MODE_IDLE:
            self._command_history.append(text)
            self._history_index = 0
            self.sig_command_requested.emit(text)
            self._log(f"$ {text}", Colors.TEXT_SECONDARY)
            self._set_mode(self.MODE_RUNNING)
        else:
            self._manager.write_input(text)
            if self._current_mode == self.MODE_PASSWORD:
                self._log("  ••••••••", Colors.TEXT_MUTED)
            else:
                self._log(f"  › {text}", Colors.ACCENT_SECONDARY)
            self._set_mode(self.MODE_RUNNING)
        
        self._input_field.clear()
    
    def _send_response(self, response: str):
        """Send Yes/No response."""
        self._manager.write_input(response)
        self._log(f"  › {response.upper()}", Colors.ACCENT_SECONDARY)
        self._set_mode(self.MODE_RUNNING)
    
    def _stop_process(self):
        """Stop running process."""
        self._manager.stop_process()
        self._log("Process terminated", Colors.DANGER)
        self._set_mode(self.MODE_IDLE)
        self._status_badge.setText("Stopped")
        self._status_badge.setStyleSheet(get_badge_style("danger"))
    
    def _log(self, text: str, color: str) -> None:
        """Append styled text to output."""
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if self._output.toPlainText():
            cursor.insertHtml("<br>")
        escaped = self._escape(text)
        cursor.insertHtml(f"<span style='color: {color};'>{escaped}</span>")
        self._output.setTextCursor(cursor)
        self._output.ensureCursorVisible()
    
    @pyqtSlot(str, str)
    def _on_output(self, text: str, channel: str):
        """Handle process output."""
        if self._current_mode == self.MODE_IDLE:
            self._set_mode(self.MODE_RUNNING)
        
        self._detect_prompt(text)
        
        color = Colors.DANGER if channel == "stderr" else Colors.TEXT_PRIMARY
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(f"<span style='color: {color};'>{self._escape(text)}</span>")
        self._output.setTextCursor(cursor)
        self._output.ensureCursorVisible()
        
        # Buffer limiti kontrolü
        doc = self._output.document()
        if doc.lineCount() > self._max_buffer_lines:
            # İlk 1000 satırı sil
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            for _ in range(1000):
                cursor.select(QTextCursor.SelectionType.LineUnderCursor)
                cursor.removeSelectedText()
                if cursor.atEnd():
                    break
                cursor.deleteChar()  # Newline'ı da sil
            
            # Bilgi mesajı ekle
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.insertHtml(f"<span style='color: {Colors.WARNING};'>[BUFFER] İlk 1000 satır temizlendi (limit: {self._max_buffer_lines})</span><br>")
    
    @pyqtSlot(int, str)
    def _on_finished(self, exit_code: int, log_path: str):
        """Handle process completion."""
        self._set_mode(self.MODE_IDLE)
        if exit_code == 0:
            self._status_badge.setText("Done")
            self._status_badge.setStyleSheet(get_badge_style("success"))
            self._log("[OK] Completed", Colors.SUCCESS)
        else:
            self._status_badge.setText(f"Exit {exit_code}")
            self._status_badge.setStyleSheet(get_badge_style("danger"))
            self._log(f"[X] Exit code {exit_code}", Colors.DANGER)
    
    @pyqtSlot()
    def _on_auth_failed(self):
        """Handle auth failure."""
        self._set_mode(self.MODE_IDLE)
        self._status_badge.setText("Auth Failed")
        self._status_badge.setStyleSheet(get_badge_style("danger"))
        self._log("[!] Authentication denied", Colors.WARNING)
    
    def _clear_output(self) -> None:
        """Clear terminal."""
        self._output.clear()
    
    def start_command(self, command: str, args: list, requires_root: bool = False) -> None:
        """Start command externally."""
        if self._manager:
            self._manager.start_process(command, args, requires_root)
            self._set_mode(self.MODE_RUNNING)
    
    # ========== Tool Integration Methods ==========
    
    def start_tool(self, tool_name: str, **kwargs):
        """
        Start integrated tool execution.
        
        Args:
            tool_name: Tool name (ping, nmap_ping_sweep, nmap_port_scan)
            **kwargs: Tool-specific parameters
        """
        if not self._coordinator:
            self._log("[!] Coordinator not initialized", Colors.DANGER)
            return
        
        tool_map = {
            "ping": self._coordinator.execute_ping,
            "nmap_ping_sweep": self._coordinator.execute_ping_sweep,
            "nmap_port_scan": self._coordinator.execute_port_scan
        }
        
        tool_func = tool_map.get(tool_name)
        if not tool_func:
            self._log(f"[!] Unknown tool: {tool_name}", Colors.DANGER)
            return
        
        self._log(f"$ Starting {tool_name}...", Colors.ACCENT_PRIMARY)
        success = tool_func(**kwargs)
        
        if not success:
            self._log(f"[!] Failed to start {tool_name}", Colors.DANGER)
            self._set_mode(self.MODE_IDLE)
    
    @pyqtSlot(str, str)
    def _on_tool_started(self, tool_id: str, execution_id: str):
        """Handle tool start event."""
        self._current_tool_id = tool_id
        self._set_mode(self.MODE_TOOL_RUNNING)
        self._status_badge.setText(f"Running: {tool_id}")
        self._status_badge.setStyleSheet(get_badge_style("info"))
        self._log(f"[EXEC] {execution_id}", Colors.TEXT_MUTED)
    
    @pyqtSlot(str, object)
    def _on_tool_output(self, tool_id: str, tool_result):
        """Handle tool execution output (from ToolResult)."""
        if hasattr(tool_result, 'stdout') and tool_result.stdout:
            # Display stdout
            lines = tool_result.stdout.strip().split('\n')
            for line in lines:
                if line.strip():
                    self._log(line, Colors.TEXT_PRIMARY)
        
        if hasattr(tool_result, 'stderr') and tool_result.stderr:
            # Display stderr
            lines = tool_result.stderr.strip().split('\n')
            for line in lines:
                if line.strip():
                    self._log(line, Colors.DANGER)
    
    @pyqtSlot(str, object)
    def _on_tool_completed(self, tool_id: str, result):
        """Handle tool completion."""
        self._current_tool_id = None
        self._set_mode(self.MODE_IDLE)
        
        # Display result summary
        if result.success:
            self._status_badge.setText("Tool Complete")
            self._status_badge.setStyleSheet(get_badge_style("success"))
            self._log(
                f"[✓] {tool_id} completed: {result.entities_created} entities created",
                Colors.SUCCESS
            )
        else:
            self._status_badge.setText("Tool Failed")
            self._status_badge.setStyleSheet(get_badge_style("warning"))
            self._log(
                f"[!] {tool_id} status: {result.execution_status}",
                Colors.WARNING
            )
            
            if result.error_message:
                self._log(f"    Error: {result.error_message}", Colors.DANGER)
        
        # Display execution details
        self._log(f"    Duration: {result.duration:.2f}s", Colors.TEXT_MUTED)
        self._log(f"    Exit code: {result.exit_code}", Colors.TEXT_MUTED)
    
    @pyqtSlot(str, str)
    def _on_tool_error(self, tool_id: str, error_message: str):
        """Handle tool error."""
        self._current_tool_id = None
        self._set_mode(self.MODE_IDLE)
        self._status_badge.setText("Error")
        self._status_badge.setStyleSheet(get_badge_style("danger"))
        self._log(f"[X] {tool_id} error: {error_message}", Colors.DANGER)
    
    @staticmethod
    def _escape(text: str) -> str:
        """Escape HTML."""
        return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
            .replace(" ", "&nbsp;"))
