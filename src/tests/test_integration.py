# SENTINEL AI - Entegrasyon Testi
# Yiğit için örnek kullanım
#
# Bu dosya, AI + Docker + Process Manager entegrasyonunu gösterir.
# main.py yazarken bu örneği kullanabilirsin.

import sys
sys.path.insert(0, '.')

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLineEdit, QLabel
from PyQt6.QtCore import pyqtSlot

from src.core.process_manager import AdvancedProcessManager
from src.core.docker_runner import get_docker_command, is_container_running
from src.ui.terminal_view import TerminalView
from src.ai.orchestrator import get_orchestrator
from src.ai.schemas import ToolCommand


class TestWindow(QMainWindow):
    """
    Basit test penceresi.
    Yiğit, main.py'ı yazarken bu örneği kullanabilir.
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SENTINEL AI - Test")
        self.setMinimumSize(800, 600)
        
        # Process Manager
        self._process_manager = AdvancedProcessManager()
        
        # AI Orchestrator
        self._orchestrator = get_orchestrator()
        
        self._setup_ui()
    
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Hedef input
        self._target_input = QLineEdit()
        self._target_input.setPlaceholderText("Hedef IP (örn: 192.168.0.100)")
        layout.addWidget(QLabel("Hedef:"))
        layout.addWidget(self._target_input)
        
        # AI input
        self._ai_input = QLineEdit()
        self._ai_input.setPlaceholderText("AI'ya ne yapmak istediğini söyle...")
        self._ai_input.returnPressed.connect(self._on_ai_submit)
        layout.addWidget(QLabel("AI Komut:"))
        layout.addWidget(self._ai_input)
        
        # AI Sor butonu
        btn_ask = QPushButton("AI'ya Sor")
        btn_ask.clicked.connect(self._on_ai_submit)
        layout.addWidget(btn_ask)
        
        # Terminal
        self._terminal = TerminalView(self._process_manager)
        layout.addWidget(self._terminal)
        
        # Manuel komut bağlantısı
        self._terminal.sig_command_requested.connect(self._on_manual_command)
    
    @pyqtSlot(str)
    def _on_manual_command(self, command: str):
        """Terminal'den gelen manuel komut."""
        parts = command.split()
        if not parts:
            return
        
        tool = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        # Docker'da çalıştır
        if is_container_running():
            cmd, docker_args = get_docker_command(tool, args)
            self._process_manager.start_process(cmd, docker_args)
        else:
            # Docker yoksa direkt çalıştır
            self._process_manager.start_process(tool, args)
    
    def _on_ai_submit(self):
        """AI'ya soru sor ve komutu çalıştır."""
        user_input = self._ai_input.text().strip()
        target = self._target_input.text().strip() or None
        
        if not user_input:
            return
        
        # AI'dan yanıt al
        response = self._orchestrator.process(user_input, target)
        
        if response.command:
            # Komutu çalıştır
            cmd = response.command
            args = cmd.arguments
            
            # Hedef placeholder'ı değiştir
            if target:
                args = [arg.replace("{target}", target) for arg in args]
            
            # Docker'da çalıştır
            if is_container_running():
                command, docker_args = get_docker_command(cmd.tool, args)
                self._process_manager.start_process(command, docker_args)
            else:
                self._process_manager.start_process(cmd.tool, args)
        else:
            print(f"AI Mesajı: {response.message}")
        
        self._ai_input.clear()


def main():
    # Docker kontrolü
    if not is_container_running():
        print("⚠️  sentinel-tools container çalışmıyor!")
        print("Çalıştır: docker compose up -d tools-service")
        print("Devam ediliyor (araçlar çalışmayabilir)...")
    
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

