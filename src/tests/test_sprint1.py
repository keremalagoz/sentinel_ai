import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import pyqtSlot
from src.core.process_manager import AdvancedProcessManager
from src.ui.terminal_view import TerminalView
from src.ui.styles import Colors


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SENTINEL AI - Terminal Test")
        self.setGeometry(100, 100, 900, 700)
        self.setStyleSheet(f"background-color: {Colors.BG_PRIMARY};")
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self._manager = AdvancedProcessManager(self)
        self._terminal = TerminalView(self._manager)
        
        self._terminal.sig_command_requested.connect(self._on_command_requested)
        
        layout.addWidget(self._terminal)
    
    @pyqtSlot(str)
    def _on_command_requested(self, command_text: str):
        """Kullanıcı yeni komut girdiğinde çalışır."""
        parts = command_text.split()
        if not parts:
            return
        
        command = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        self._terminal.start_command(command, args)


def main():
    app = QApplication(sys.argv)
    
    app.setStyle("Fusion")
    
    window = TestWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
