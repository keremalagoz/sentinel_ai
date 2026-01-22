"""Test UI Integration - Action Planner v2.1

Minimal test window for ToolManager + TerminalView integration
PyQt6 version for Qt compatibility with QProcess
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLineEdit, QPushButton, QLabel, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QTextCursor

from src.core.sentinel_coordinator import SentinelCoordinator


class SimpleTerminal(QWidget):
    """Simple terminal output widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', monospace;
                font-size: 10pt;
                border: 1px solid #3e3e3e;
            }
        """)
        layout.addWidget(self.output)
    
    def log(self, text: str, color: str = "#d4d4d4"):
        """Append colored text"""
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(f"<span style='color: {color};'>{text}</span><br>")
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()


class TestWindow(QMainWindow):
    """Test window for UI integration"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("SENTINEL - Tool Integration Test")
        self.setMinimumSize(1000, 700)
        
        # Coordinator (replaces process_manager for tool execution)
        self.coordinator = SentinelCoordinator(db_path="test_sentinel.db")
        
        # Setup UI
        self._setup_ui()
    
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Control panel
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        
        # Target input
        control_layout.addWidget(QLabel("Target:"))
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("IP or hostname (e.g., 127.0.0.1)")
        control_layout.addWidget(self.target_input)
        
        # Tool buttons
        btn_ping = QPushButton("Ping")
        btn_ping.clicked.connect(self._on_ping)
        control_layout.addWidget(btn_ping)
        
        btn_sweep = QPushButton("Ping Sweep")
        btn_sweep.clicked.connect(self._on_sweep)
        control_layout.addWidget(btn_sweep)
        
        btn_portscan = QPushButton("Port Scan")
        btn_portscan.clicked.connect(self._on_portscan)
        control_layout.addWidget(btn_portscan)
        
        # Stats button
        btn_stats = QPushButton("Show Stats")
        btn_stats.clicked.connect(self._show_stats)
        control_layout.addWidget(btn_stats)
        
        layout.addWidget(control_panel)
        
        # Terminal output
        self.terminal = SimpleTerminal()
        layout.addWidget(self.terminal, stretch=1)
        
        # Connect coordinator signals
        self.coordinator.tool_started.connect(self._on_tool_started)
        self.coordinator.tool_completed.connect(self._on_tool_completed)
        self.coordinator.tool_error.connect(self._on_tool_error)
    
    @pyqtSlot(str, str)
    def _on_tool_started(self, tool_id: str, execution_id: str):
        """Tool started"""
        self.terminal.log(f"[START] {tool_id} ({execution_id})", "#00aaff")
    
    @pyqtSlot(str, object)
    def _on_tool_completed(self, tool_id: str, result):
        """Tool completed"""
        # Display stdout
        if result.stdout:
            self.terminal.log("=== STDOUT ===", "#888888")
            for line in result.stdout.strip().split('\n'):
                self.terminal.log(line, "#d4d4d4")
        
        # Display result
        if result.success:
            self.terminal.log(
                f"[OK] {tool_id}: {result.entities_created} entities, {result.duration:.2f}s",
                "#00ff00"
            )
        else:
            self.terminal.log(
                f"[FAIL] {tool_id}: {result.execution_status}",
                "#ff8800"
            )
            if result.error_message:
                self.terminal.log(f"  Error: {result.error_message}", "#ff0000")
    
    @pyqtSlot(str, str)
    def _on_tool_error(self, tool_id: str, error_message: str):
        """Tool error"""
        self.terminal.log(f"[ERROR] {tool_id}: {error_message}", "#ff0000")
    
    def _on_ping(self):
        """Execute ping"""
        target = self.target_input.text() or "127.0.0.1"
        self.terminal.log(f"$ ping {target}", "#00aaff")
        self.coordinator.execute_ping(target=target, count=4)
    
    def _on_sweep(self):
        """Execute ping sweep"""
        target = self.target_input.text() or "127.0.0.1/32"
        self.terminal.log(f"$ nmap -sn {target}", "#00aaff")
        self.coordinator.execute_ping_sweep(target=target)
    
    def _on_portscan(self):
        """Execute port scan"""
        target = self.target_input.text() or "127.0.0.1"
        self.terminal.log(f"$ nmap -sT -p 1-100 {target}", "#00aaff")
        self.coordinator.execute_port_scan(target=target, ports="1-100")
    
    def _show_stats(self):
        """Show backend statistics"""
        stats = self.coordinator.get_backend_stats()
        self.terminal.log("=== BACKEND STATS ===", "#888888")
        
        # Entity counts
        entities = stats.get('entities', {})
        total = sum(entities.values()) if entities else 0
        self.terminal.log(f"Total entities: {total}", "#d4d4d4")
        self.terminal.log(f"Hosts: {entities.get('host', 0)}", "#d4d4d4")
        self.terminal.log(f"Ports: {entities.get('port', 0)}", "#d4d4d4")
        self.terminal.log(f"Services: {entities.get('service', 0)}", "#d4d4d4")
        self.terminal.log(f"Executions: {stats.get('total_executions', 0)}", "#d4d4d4")
    
    def closeEvent(self, event):
        """Cleanup on close"""
        self.coordinator.cleanup()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
