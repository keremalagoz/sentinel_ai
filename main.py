# SENTINEL AI - Main Entry Point
# Sprint 2.3: AI + Process Manager Entegrasyonu
#
# Akış:
# 1. Kullanıcı terminal'e doğal dilde komut yazar
# 2. AI Orchestrator komutu JSON'a çevirir
# 3. Kullanıcıya onay için gösterilir
# 4. Onaylanırsa Process Manager çalıştırır

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFrame, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont

from src.core.process_manager import AdvancedProcessManager
from src.ui.terminal_view import TerminalView
from src.ai.orchestrator import get_orchestrator
from src.ai.schemas import ToolCommand, RiskLevel


class MainWindow(QMainWindow):
    """
    SENTINEL AI Ana Pencere.
    
    Bileşenler:
    - Header: Logo ve durum göstergesi
    - Terminal: Komut çıktıları
    - AI Input: Doğal dil girişi
    - Command Preview: AI'ın ürettiği komutu gösterme
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SENTINEL AI - Security Testing Assistant")
        self.setMinimumSize(900, 700)
        
        # Core bileşenler
        self._process_manager = AdvancedProcessManager()
        self._orchestrator = get_orchestrator()
        self._pending_command: ToolCommand | None = None
        self._current_target: str | None = None
        
        self._setup_ui()
        self._setup_styles()
        self._connect_signals()
        self._check_ai_status()
    
    def _setup_ui(self):
        """UI bileşenlerini oluştur."""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # === HEADER ===
        header = QFrame()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 12, 20, 12)
        
        # Logo
        logo = QLabel("⚔️ SENTINEL AI")
        logo.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_layout.addWidget(logo)
        
        header_layout.addStretch()
        
        # AI Durum
        self._ai_status = QLabel("AI: Checking...")
        self._ai_status.setObjectName("aiStatus")
        header_layout.addWidget(self._ai_status)
        
        main_layout.addWidget(header)
        
        # === CONTENT AREA ===
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)
        
        # Target Input
        target_frame = QFrame()
        target_frame.setObjectName("targetFrame")
        target_layout = QHBoxLayout(target_frame)
        target_layout.setContentsMargins(12, 8, 12, 8)
        
        target_label = QLabel("🎯 Hedef:")
        target_layout.addWidget(target_label)
        
        self._target_input = QLineEdit()
        self._target_input.setPlaceholderText("IP adresi veya hostname (örn: 192.168.1.100)")
        self._target_input.textChanged.connect(self._on_target_changed)
        target_layout.addWidget(self._target_input, stretch=1)
        
        content_layout.addWidget(target_frame)
        
        # Terminal View
        self._terminal = TerminalView(self._process_manager)
        content_layout.addWidget(self._terminal, stretch=1)
        
        # === AI INPUT AREA ===
        ai_frame = QFrame()
        ai_frame.setObjectName("aiFrame")
        ai_layout = QVBoxLayout(ai_frame)
        ai_layout.setContentsMargins(12, 12, 12, 12)
        ai_layout.setSpacing(8)
        
        ai_label = QLabel("🤖 AI Komut Asistanı")
        ai_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        ai_layout.addWidget(ai_label)
        
        # AI Input Row
        input_row = QHBoxLayout()
        
        self._ai_input = QLineEdit()
        self._ai_input.setPlaceholderText("Ne yapmak istiyorsun? (örn: 'Açık portları tara', 'Web dizinlerini bul')")
        self._ai_input.returnPressed.connect(self._on_ai_submit)
        input_row.addWidget(self._ai_input, stretch=1)
        
        self._btn_ask = QPushButton("🔮 Sor")
        self._btn_ask.setObjectName("btnAsk")
        self._btn_ask.clicked.connect(self._on_ai_submit)
        input_row.addWidget(self._btn_ask)
        
        ai_layout.addLayout(input_row)
        
        # Command Preview
        self._preview_frame = QFrame()
        self._preview_frame.setObjectName("previewFrame")
        self._preview_frame.setVisible(False)
        preview_layout = QVBoxLayout(self._preview_frame)
        preview_layout.setContentsMargins(12, 12, 12, 12)
        preview_layout.setSpacing(8)
        
        self._preview_label = QLabel()
        self._preview_label.setWordWrap(True)
        preview_layout.addWidget(self._preview_label)
        
        self._preview_command = QLabel()
        self._preview_command.setObjectName("previewCommand")
        self._preview_command.setFont(QFont("Consolas", 11))
        self._preview_command.setWordWrap(True)
        preview_layout.addWidget(self._preview_command)
        
        # Preview Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        self._btn_cancel = QPushButton("❌ İptal")
        self._btn_cancel.clicked.connect(self._cancel_command)
        btn_row.addWidget(self._btn_cancel)
        
        self._btn_execute = QPushButton("✅ Çalıştır")
        self._btn_execute.setObjectName("btnExecute")
        self._btn_execute.clicked.connect(self._execute_command)
        btn_row.addWidget(self._btn_execute)
        
        preview_layout.addLayout(btn_row)
        ai_layout.addWidget(self._preview_frame)
        
        content_layout.addWidget(ai_frame)
        main_layout.addWidget(content)
    
    def _setup_styles(self):
        """Stil tanımları."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0d1117;
            }
            
            #header {
                background-color: #161b22;
                border-bottom: 1px solid #30363d;
            }
            
            #header QLabel {
                color: #f0f6fc;
            }
            
            #aiStatus {
                color: #8b949e;
                padding: 4px 12px;
                background-color: #21262d;
                border-radius: 12px;
            }
            
            #targetFrame {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
            
            #targetFrame QLabel {
                color: #f0f6fc;
            }
            
            #targetFrame QLineEdit {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 8px;
                color: #f0f6fc;
            }
            
            #targetFrame QLineEdit:focus {
                border-color: #58a6ff;
            }
            
            #aiFrame {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
            
            #aiFrame QLabel {
                color: #f0f6fc;
            }
            
            #aiFrame QLineEdit {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 10px;
                color: #f0f6fc;
                font-size: 13px;
            }
            
            #aiFrame QLineEdit:focus {
                border-color: #58a6ff;
            }
            
            #btnAsk {
                background-color: #238636;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }
            
            #btnAsk:hover {
                background-color: #2ea043;
            }
            
            #previewFrame {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 6px;
            }
            
            #previewCommand {
                color: #7ee787;
                background-color: #161b22;
                padding: 8px;
                border-radius: 4px;
            }
            
            #btnExecute {
                background-color: #238636;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            
            #btnExecute:hover {
                background-color: #2ea043;
            }
            
            QPushButton {
                background-color: #21262d;
                color: #f0f6fc;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 16px;
            }
            
            QPushButton:hover {
                background-color: #30363d;
            }
        """)
    
    def _connect_signals(self):
        """Sinyal bağlantıları."""
        # Terminal'den gelen manuel komutlar
        self._terminal.sig_command_requested.connect(self._on_manual_command)
    
    def _check_ai_status(self):
        """AI servislerinin durumunu kontrol et."""
        status = self._orchestrator.get_status()
        
        local = "✓" if status["local"]["available"] else "✗"
        cloud = "✓" if status["cloud"]["available"] else "✗"
        
        self._ai_status.setText(f"Local: {local} | Cloud: {cloud}")
        
        if status["local"]["available"] or status["cloud"]["available"]:
            self._ai_status.setStyleSheet("""
                color: #7ee787;
                padding: 4px 12px;
                background-color: #238636;
                border-radius: 12px;
            """)
        else:
            self._ai_status.setStyleSheet("""
                color: #f85149;
                padding: 4px 12px;
                background-color: #da3633;
                border-radius: 12px;
            """)
    
    def _on_target_changed(self, text: str):
        """Hedef değiştiğinde."""
        self._current_target = text if text.strip() else None
    
    @pyqtSlot(str)
    def _on_manual_command(self, command: str):
        """Terminal'den gelen manuel komut."""
        # Basit komut parse (ilk kelime = tool, geri kalan = args)
        parts = command.split()
        if not parts:
            return
        
        tool = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        self._process_manager.start_process(tool, args)
    
    def _on_ai_submit(self):
        """AI'ya soru gönder."""
        user_input = self._ai_input.text().strip()
        if not user_input:
            return
        
        # AI'dan yanıt al
        try:
            response = self._orchestrator.process(user_input, self._current_target)
            
            if response.needs_clarification:
                QMessageBox.information(
                    self,
                    "Daha Fazla Bilgi Gerekli",
                    response.message
                )
                return
            
            if response.command:
                self._show_command_preview(response.command, response.message)
            else:
                QMessageBox.information(
                    self,
                    "AI Yanıtı",
                    response.message
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "AI Hatası",
                f"AI işleme hatası: {str(e)}"
            )
    
    def _show_command_preview(self, command: ToolCommand, message: str):
        """Komutu önizleme olarak göster."""
        self._pending_command = command
        
        # Risk seviyesi rengi
        risk_colors = {
            RiskLevel.LOW: "#7ee787",
            RiskLevel.MEDIUM: "#d29922",
            RiskLevel.HIGH: "#f85149"
        }
        risk_color = risk_colors.get(command.risk_level, "#8b949e")
        
        # Önizleme metni
        preview_text = f"""
        <p style="color: #f0f6fc;">{message}</p>
        <p style="color: {risk_color};">
            ⚠️ Risk: {command.risk_level.value.upper()}
            {'| 🔒 Root gerekli' if command.requires_root else ''}
        </p>
        """
        self._preview_label.setText(preview_text)
        
        # Komut
        full_command = f"{command.tool} {' '.join(command.arguments)}"
        self._preview_command.setText(f"$ {full_command}")
        
        # Göster
        self._preview_frame.setVisible(True)
        self._ai_input.clear()
    
    def _cancel_command(self):
        """Komutu iptal et."""
        self._pending_command = None
        self._preview_frame.setVisible(False)
    
    def _execute_command(self):
        """Komutu çalıştır."""
        if not self._pending_command:
            return
        
        cmd = self._pending_command
        
        # Hedef placeholder'ı değiştir
        args = []
        for arg in cmd.arguments:
            if "{target}" in arg and self._current_target:
                arg = arg.replace("{target}", self._current_target)
            args.append(arg)
        
        # Terminal'e başlat
        self._terminal.start_command(
            cmd.tool,
            args,
            cmd.requires_root
        )
        
        # Temizle
        self._pending_command = None
        self._preview_frame.setVisible(False)
    
    def closeEvent(self, event):
        """Pencere kapanırken çalışan process'i durdur."""
        if self._process_manager.is_running():
            self._process_manager.stop_process()
        event.accept()


def main():
    """Uygulama başlangıç noktası."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
