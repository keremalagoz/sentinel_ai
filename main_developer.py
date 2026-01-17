# SENTINEL AI - Developer Mode Entry Point
# ==========================================
# DEVELOPMENT ONLY - Do NOT use in production
#
# Bu dosya development için optimize edilmiştir:
# ✅ Native Ollama (localhost:11434) - Docker'a gerek yok
# ✅ WSL/Docker kapalı - RAM tasarrufu (~6GB)
# ✅ Mock execution - Gerçek komut çalıştırmaz, sadece gösterir
# ✅ LLM yanıt süresi 2-3x daha hızlı
# ✅ Policy gate production ile aynı
#
# Gereksinimler:
# 1. Native Ollama kurulu olmalı: https://ollama.com/download
# 2. WhiteRabbitNeo model indirilmiş olmalı: ollama pull whiterabbitneo
#
# Kullanım:
#   python main_developer.py

import sys
import os

# Proje root'unu path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QLabel, QPushButton, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont

from src.ui.terminal_view import TerminalView
from src.ui.styles import Colors, Fonts
from src.ai.orchestrator import AIOrchestrator
from src.ai.schemas import AIResponse, RiskLevel


# =============================================================================
# DEVELOPER MODE BANNER
# =============================================================================

DEVELOPER_BANNER = """
╔════════════════════════════════════════════════════════════════════════╗
║                                                                        ║
║            🔧 SENTINEL AI - DEVELOPER MODE 🔧                          ║
║                                                                        ║
║  [✓] LLM: Native Ollama (localhost:11434) - NO DOCKER                ║
║  [✓] RAM: WSL Kapalı (~6GB tasarruf)                                  ║
║  [✓] Execution: MOCKED (komutlar çalıştırılmaz)                       ║
║  [✓] Speed: 2-3x daha hızlı yanıt                                     ║
║                                                                        ║
║  ⚠️  PRODUCTION KULLANIMI YASAK - Sadece UI/AI geliştirme için       ║
║                                                                        ║
╚════════════════════════════════════════════════════════════════════════╝
"""


# =============================================================================
# Developer Mode - Mock Process Manager
# =============================================================================

class MockProcessManager:
    """
    Development için sahte process manager.
    Komutları çalıştırmaz, sadece terminal'de gösterir.
    """
    
    def __init__(self, parent=None):
        self._parent = parent
        self._is_running = False
    
    def is_running(self) -> bool:
        return self._is_running
    
    def start_process(self, tool: str, arguments: list, requires_root: bool = False):
        """Komutu çalıştırmaz, sadece terminal'e yazar"""
        # Mock çıktı oluştur
        args_str = ' '.join(arguments)
        command_line = f"{tool} {args_str}"
        
        root_prefix = "[ROOT] " if requires_root else ""
        
        # Terminal'e yaz
        if hasattr(self._parent, '_terminal'):
            terminal = self._parent._terminal
            
            # Komut satırını göster
            terminal.append_output(f"\n{root_prefix}$ {command_line}", is_command=True)
            
            # Developer mode uyarısı
            terminal.append_output(
                "\n[DEVELOPER MODE] Komut gerçekte çalıştırılmadı.\n",
                is_warning=True
            )
            
            # Sahte çıktı
            mock_output = self._generate_mock_output(tool, arguments)
            if mock_output:
                terminal.append_output(f"\n{mock_output}\n", is_success=True)
            
            terminal.append_output(
                "\n[INFO] Production'da bu komut gerçek çıktı üretecek.\n",
                is_info=True
            )
    
    def stop_process(self):
        """Mock - hiçbir şey yapmaz"""
        pass
    
    def _generate_mock_output(self, tool: str, arguments: list) -> str:
        """Tool'a göre sahte çıktı üret"""
        
        if tool == "nmap":
            if "-sn" in arguments:
                return """Starting Nmap 7.94 ( https://nmap.org )
Nmap scan report for 192.168.1.1
Host is up (0.001s latency).
Nmap scan report for 192.168.1.100
Host is up (0.002s latency).
Nmap done: 256 IP addresses (2 hosts up) scanned in 2.50 seconds
"""
            elif "-p" in arguments or "-sS" in arguments:
                return """Starting Nmap 7.94 ( https://nmap.org )
Nmap scan report for scanme.nmap.org (45.33.32.156)
PORT     STATE SERVICE
22/tcp   open  ssh
80/tcp   open  http
443/tcp  open  https

Nmap done: 1 IP address (1 host up) scanned in 3.21 seconds
"""
            else:
                return "Nmap scan completed (mock output)"
        
        elif tool == "gobuster":
            return """===============================================================
Gobuster v3.6
===============================================================
[+] Url:                     http://example.com
[+] Wordlist:                /usr/share/wordlists/dirb/common.txt
[+] Status codes:            200,204,301,302,307,401,403
===============================================================
/admin                (Status: 301)
/images               (Status: 301)
/index.html           (Status: 200)
===============================================================
"""
        
        elif tool in ["nslookup", "dig"]:
            return """Server:  192.168.1.1
Address: 192.168.1.1#53

Non-authoritative answer:
Name:    example.com
Address: 93.184.216.34
"""
        
        elif tool == "whois":
            return """Domain Name: EXAMPLE.COM
Registry Domain ID: 2336799_DOMAIN_COM-VRSN
Registrar: RESERVED-Internet Assigned Numbers Authority
Creation Date: 1995-08-14T04:00:00Z
Registry Expiry Date: 2024-08-13T04:00:00Z
"""
        
        elif tool == "nikto":
            return """- Nikto v2.5.0
+ Target IP:          example.com
+ Target Hostname:    example.com
+ Target Port:        80
+ Start Time:         2026-01-17 12:00:00

+ Server: Apache/2.4.41 (Ubuntu)
+ Retrieved x-powered-by header: PHP/7.4.3
+ The anti-clickjacking X-Frame-Options header is not present.
"""
        
        else:
            return f"[Mock Output] {tool} execution completed successfully."


# =============================================================================
# AI Worker Thread - Production ile aynı
# =============================================================================

class AIWorker(QThread):
    """
    AI çağrılarını arka planda çalıştırır.
    UI thread'ini bloklamaz.
    """
    result_ready = pyqtSignal(object)  # AIResponse
    error_occurred = pyqtSignal(str)
    
    def __init__(self, orchestrator, query: str, target: str = None):
        super().__init__()
        self._orchestrator = orchestrator
        self._query = query
        self._target = target
    
    def run(self):
        try:
            response = self._orchestrator.process(self._query, self._target)
            self.result_ready.emit(response)
        except Exception as e:
            self.error_occurred.emit(str(e))


# =============================================================================
# Developer Main Window
# =============================================================================

class SentinelDeveloperWindow(QMainWindow):
    """
    SENTINEL AI Developer Mode Penceresi
    
    Production ile farklar:
    - Native Ollama kullanır (Docker değil)
    - Komutları gerçekte çalıştırmaz (mock execution)
    - Docker/WSL kapatma seçeneği yok
    """
    
    def __init__(self):
        super().__init__()
        
        # Core bileşenler - DEVELOPER MODE
        self._process_manager = MockProcessManager(self)  # Mock!
        self._orchestrator = AIOrchestrator(model="whiterabbitneo")  # Native Ollama
        self._ai_worker: AIWorker = None
        self._pending_command = None
        
        # Pencere ayarları
        self.setWindowTitle("🔧 SENTINEL AI - DEVELOPER MODE 🔧")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(f"background-color: {Colors.BG_PRIMARY}; color: {Colors.TEXT_PRIMARY};")
        
        self._setup_ui()
        self._connect_signals()
        self._check_services()
    
    def closeEvent(self, event):
        """Temizlik - sadece thread'leri durdur"""
        # AI Worker çalışıyorsa durdur
        if self._ai_worker and self._ai_worker.isRunning():
            self._ai_worker.quit()
            self._ai_worker.wait(1000)
        
        # Docker temizliği YOK (developer mode)
        event.accept()
    
    def _setup_ui(self):
        """UI bileşenlerini oluştur."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        # === DEVELOPER MODE WARNING BANNER ===
        warning_banner = self._create_warning_banner()
        main_layout.addWidget(warning_banner)
        
        # === HEADER ===
        header = self._create_header()
        main_layout.addWidget(header)
        
        # === KONTROL PANELİ ===
        control_panel = self._create_control_panel()
        main_layout.addWidget(control_panel)
        
        # === ONAY PANELİ (başlangıçta gizli) ===
        self._approval_panel = self._create_approval_panel()
        self._approval_panel.setVisible(False)
        main_layout.addWidget(self._approval_panel)
        
        # === TERMİNAL ===
        self._terminal = TerminalView(self._process_manager)
        main_layout.addWidget(self._terminal, stretch=1)
        
        # Developer mode uyarısını terminal'e bas
        self._terminal.append_output(
            DEVELOPER_BANNER + "\n",
            is_info=True
        )
        self._terminal.append_output(
            "[INFO] Native Ollama bağlantısı kontrol ediliyor...\n",
            is_info=True
        )
    
    def _create_warning_banner(self) -> QWidget:
        """Developer mode uyarı banner'ı"""
        banner = QFrame()
        banner.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.WARNING_MUTED};
                border: 2px solid {Colors.WARNING};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(12, 6, 12, 6)
        
        icon = QLabel("⚠️")
        icon.setStyleSheet(f"color: {Colors.WARNING}; font-size: 20px;")
        layout.addWidget(icon)
        
        text = QLabel("DEVELOPER MODE - Komutlar çalıştırılmaz | Native Ollama | Docker Kapalı")
        text.setStyleSheet(f"""
            color: {Colors.WARNING};
            font-weight: bold;
            font-size: 13px;
        """)
        layout.addWidget(text)
        
        layout.addStretch()
        
        return banner
    
    def _create_header(self) -> QWidget:
        """Başlık ve durum göstergesi."""
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_MUTED};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # Logo/Başlık
        title = QLabel("🔧 SENTINEL AI [DEV]")
        title.setStyleSheet(f"""
            color: {Colors.WARNING};
            font-family: {Fonts.MONO};
            font-size: 18px;
            font-weight: bold;
        """)
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Servis durumu - sadece Native Ollama
        self._status_ollama = QLabel("● Native Ollama")
        self._status_ollama.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        layout.addWidget(self._status_ollama)
        
        return header
    
    def _create_control_panel(self) -> QWidget:
        """Hedef ve AI sorgu alanları."""
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER_MUTED};
                border-radius: 8px;
            }}
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        
        # Üst satır: Hedef IP
        target_row = QHBoxLayout()
        target_label = QLabel("🎯 Hedef:")
        target_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-weight: bold;")
        target_label.setFixedWidth(80)
        target_row.addWidget(target_label)
        
        self._target_input = QLineEdit()
        self._target_input.setPlaceholderText("IP adresi veya hostname (örn: 192.168.1.100, scanme.nmap.org)")
        self._target_input.setStyleSheet(self._get_input_style())
        target_row.addWidget(self._target_input)
        layout.addLayout(target_row)
        
        # Alt satır: AI Sorgu
        ai_row = QHBoxLayout()
        ai_label = QLabel("🤖 Komut:")
        ai_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-weight: bold;")
        ai_label.setFixedWidth(80)
        ai_row.addWidget(ai_label)
        
        self._ai_input = QLineEdit()
        self._ai_input.setPlaceholderText("Ne yapmak istiyorsun? (örn: 'Açık portları tara', 'Web dizinlerini keşfet')")
        self._ai_input.setStyleSheet(self._get_input_style())
        self._ai_input.returnPressed.connect(self._on_ai_submit)
        ai_row.addWidget(self._ai_input)
        
        self._btn_ask = QPushButton("AI'ya Sor")
        self._btn_ask.setStyleSheet(self._get_button_style())
        self._btn_ask.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_ask.clicked.connect(self._on_ai_submit)
        ai_row.addWidget(self._btn_ask)
        
        layout.addLayout(ai_row)
        
        return panel
    
    def _create_approval_panel(self) -> QWidget:
        """Komut onay paneli (AI önerisi gösterimi)."""
        panel = QFrame()
        panel.setObjectName("approvalPanel")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # Başlık
        header_row = QHBoxLayout()
        self._approval_title = QLabel("🔍 AI Önerisi")
        self._approval_title.setStyleSheet(f"color: {Colors.ACCENT_PRIMARY}; font-weight: bold; font-size: 14px;")
        header_row.addWidget(self._approval_title)
        
        header_row.addStretch()
        
        self._risk_badge = QLabel("LOW")
        header_row.addWidget(self._risk_badge)
        layout.addLayout(header_row)
        
        # Komut gösterimi
        self._command_display = QLabel()
        self._command_display.setStyleSheet(f"""
            background-color: {Colors.BG_PRIMARY};
            color: {Colors.SUCCESS_BRIGHT};
            font-family: {Fonts.MONO};
            font-size: 13px;
            padding: 10px;
            border-radius: 4px;
        """)
        self._command_display.setWordWrap(True)
        layout.addWidget(self._command_display)
        
        # AI açıklaması
        self._explanation_label = QLabel()
        self._explanation_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
        self._explanation_label.setWordWrap(True)
        layout.addWidget(self._explanation_label)
        
        # Developer mode uyarısı
        dev_warning = QLabel("⚠️ DEV MODE: Komut gerçekte çalıştırılmayacak (mock çıktı gösterilecek)")
        dev_warning.setStyleSheet(f"""
            color: {Colors.WARNING};
            font-size: 11px;
            font-style: italic;
            padding: 4px;
        """)
        layout.addWidget(dev_warning)
        
        # Butonlar
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        self._btn_reject = QPushButton("✕ İptal")
        self._btn_reject.setStyleSheet(self._get_button_style(danger=True))
        self._btn_reject.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_reject.clicked.connect(self._on_reject_command)
        btn_row.addWidget(self._btn_reject)
        
        self._btn_approve = QPushButton("✓ Mock Göster")
        self._btn_approve.setStyleSheet(self._get_button_style(success=True))
        self._btn_approve.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_approve.clicked.connect(self._on_approve_command)
        btn_row.addWidget(self._btn_approve)
        
        layout.addLayout(btn_row)
        
        return panel
    
    def _get_input_style(self) -> str:
        return f"""
            QLineEdit {{
                background-color: {Colors.BG_PRIMARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: 6px;
                padding: 10px 12px;
                font-family: {Fonts.MONO};
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {Colors.ACCENT_PRIMARY};
            }}
            QLineEdit::placeholder {{
                color: {Colors.TEXT_MUTED};
            }}
        """
    
    def _get_button_style(self, success=False, danger=False) -> str:
        if success:
            bg = Colors.SUCCESS
            hover = Colors.SUCCESS_BRIGHT
        elif danger:
            bg = Colors.DANGER
            hover = "#ff6b6b"
        else:
            bg = Colors.ACCENT_PRIMARY
            hover = "#79b8ff"
        
        return f"""
            QPushButton {{
                background-color: {bg};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:disabled {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_MUTED};
            }}
        """
    
    def _get_risk_style(self, risk: RiskLevel) -> str:
        """Risk seviyesine göre badge stili."""
        colors = {
            RiskLevel.LOW: (Colors.SUCCESS, Colors.SUCCESS_MUTED),
            RiskLevel.MEDIUM: (Colors.WARNING, Colors.WARNING_MUTED),
            RiskLevel.HIGH: (Colors.DANGER, Colors.DANGER_MUTED),
        }
        fg, bg = colors.get(risk, (Colors.TEXT_MUTED, Colors.BG_TERTIARY))
        
        return f"""
            QLabel {{
                color: {fg};
                background-color: {bg};
                padding: 4px 10px;
                border-radius: 10px;
                font-weight: bold;
                font-size: 11px;
            }}
        """
    
    def _connect_signals(self):
        """Sinyal bağlantıları."""
        self._terminal.sig_command_requested.connect(self._on_manual_command)
    
    def _check_services(self):
        """Native Ollama durumunu kontrol et."""
        try:
            available = self._orchestrator._intent_resolver.check_available()
            
            if available:
                self._status_ollama.setText("● Native Ollama")
                self._status_ollama.setStyleSheet(f"color: {Colors.SUCCESS_BRIGHT};")
                self._terminal.append_output(
                    "[OK] Native Ollama (localhost:11434) bağlantı başarılı.\n",
                    is_success=True
                )
            else:
                self._status_ollama.setText("○ Native Ollama")
                self._status_ollama.setStyleSheet(f"color: {Colors.DANGER};")
                self._terminal.append_output(
                    "[ERROR] Native Ollama bağlantı hatası!\n"
                    "        Çözüm: ollama serve\n",
                    is_error=True
                )
        except Exception as e:
            self._status_ollama.setText("○ Native Ollama")
            self._status_ollama.setStyleSheet(f"color: {Colors.DANGER};")
            self._terminal.append_output(
                f"[ERROR] Ollama kontrol hatası: {str(e)}\n",
                is_error=True
            )
    
    # =========================================================================
    # Event Handlers - Production ile aynı
    # =========================================================================
    
    def _on_ai_submit(self):
        """AI'ya sorgu gönder."""
        query = self._ai_input.text().strip()
        if not query:
            return
        
        target = self._target_input.text().strip() or None
        
        # UI'yı devre dışı bırak
        self._btn_ask.setEnabled(False)
        self._btn_ask.setText("Düşünüyor...")
        self._ai_input.setEnabled(False)
        
        # AI çağrısını arka planda yap
        self._ai_worker = AIWorker(self._orchestrator, query, target)
        self._ai_worker.result_ready.connect(self._on_ai_result)
        self._ai_worker.error_occurred.connect(self._on_ai_error)
        self._ai_worker.start()
    
    @pyqtSlot(object)
    def _on_ai_result(self, response: AIResponse):
        """AI yanıtı geldiğinde."""
        # UI'yı tekrar aktif et
        self._btn_ask.setEnabled(True)
        self._btn_ask.setText("AI'ya Sor")
        self._ai_input.setEnabled(True)
        
        if response.command:
            # Komut var - onay panelini göster
            self._pending_command = response.command
            self._show_approval_panel(response)
        else:
            # Komut yok - mesajı göster
            QMessageBox.information(
                self, 
                "AI Yanıtı", 
                response.message
            )
        
        if response.needs_clarification:
            self._ai_input.setFocus()
    
    @pyqtSlot(str)
    def _on_ai_error(self, error: str):
        """AI hata durumunda."""
        self._btn_ask.setEnabled(True)
        self._btn_ask.setText("AI'ya Sor")
        self._ai_input.setEnabled(True)
        
        QMessageBox.critical(
            self,
            "AI Hatası",
            f"AI işlemi başarısız:\n{error}\n\n"
            f"Native Ollama çalışıyor mu kontrol et:\n"
            f"  > ollama serve"
        )
    
    def _show_approval_panel(self, response: AIResponse):
        """Komut onay panelini göster."""
        cmd = response.command
        
        # Risk badge
        risk_text = cmd.risk_level.value.upper()
        self._risk_badge.setText(risk_text)
        self._risk_badge.setStyleSheet(self._get_risk_style(cmd.risk_level))
        
        # Komut gösterimi
        target = self._target_input.text().strip()
        args_display = [arg.replace("{target}", target) if target else arg for arg in cmd.arguments]
        full_command = f"{cmd.tool} {' '.join(args_display)}"
        self._command_display.setText(f"$ {full_command}")
        
        # Açıklama
        explanation = cmd.explanation or response.message
        root_warning = " ⚠️ (Root yetkisi gerekli)" if cmd.requires_root else ""
        self._explanation_label.setText(f"{explanation}{root_warning}")
        
        # Panel stilini risk seviyesine göre ayarla
        border_color = {
            RiskLevel.LOW: Colors.SUCCESS,
            RiskLevel.MEDIUM: Colors.WARNING,
            RiskLevel.HIGH: Colors.DANGER,
        }.get(cmd.risk_level, Colors.BORDER_DEFAULT)
        
        self._approval_panel.setStyleSheet(f"""
            QFrame#approvalPanel {{
                background-color: {Colors.BG_SECONDARY};
                border: 2px solid {border_color};
                border-radius: 8px;
            }}
        """)
        
        self._approval_panel.setVisible(True)
        self._btn_approve.setFocus()
    
    def _on_approve_command(self):
        """Komutu onayla ve MOCK çalıştır."""
        if not hasattr(self, '_pending_command') or not self._pending_command:
            return
        
        cmd = self._pending_command
        target = self._target_input.text().strip()
        
        # Hedef placeholder'ı değiştir
        args = [arg.replace("{target}", target) if target else arg for arg in cmd.arguments]
        
        # Mock execution - gerçek komut çalıştırmaz
        self._process_manager.start_process(cmd.tool, args, requires_root=cmd.requires_root)
        
        self._approval_panel.setVisible(False)
        self._pending_command = None
        self._ai_input.clear()
    
    def _on_reject_command(self):
        """Komutu reddet."""
        self._approval_panel.setVisible(False)
        self._pending_command = None
        self._ai_input.setFocus()
    
    @pyqtSlot(str)
    def _on_manual_command(self, command: str):
        """Terminal'den gelen manuel komut - MOCK"""
        parts = command.split()
        if not parts:
            return
        
        tool = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        # Mock execution
        self._process_manager.start_process(tool, args)


# =============================================================================
# Entry Point
# =============================================================================

def main():
    # Print banner to console
    print(DEVELOPER_BANNER)
    
    # High DPI desteği
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    print("[*] SENTINEL AI DEVELOPER MODE baslatiliyor...")
    print("    Native Ollama (localhost:11434) bekleniyor...")
    print("    Docker/WSL GEREKMIYOR - RAM tasarrufu aktif.")
    print()
    
    window = SentinelDeveloperWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
