# SENTINEL AI - Main Entry Point
# ================================
# Sprint 2.3: AI Entegrasyonu
# Yiğit (System/UI/Security)
#
# Bu dosya tüm bileşenleri bir araya getirir:
# - PyQt6 GUI
# - AI Orchestrator (Hibrit: Local Llama 3 + Cloud GPT-4o-mini)
# - Process Manager (QProcess tabanlı)
# - Docker Runner (Güvenlik araçları container'da)

import sys
import os
import subprocess

# Proje root'unu path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QLabel, QPushButton, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont

from src.core.process_manager import AdvancedProcessManager
from src.ui.terminal_view import TerminalView
from src.ui.styles import Colors, Fonts
from src.ai.orchestrator import get_orchestrator
from src.ai.schemas import AIResponse, RiskLevel
from src.core.cleaner import get_cleaner


# =============================================================================
# AI Worker Thread - UI donmasını önler
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
# Ana Pencere
# =============================================================================

class SentinelMainWindow(QMainWindow):
    """
    SENTINEL AI Ana Penceresi
    
    Bileşenler:
    - Üst: Hedef IP ve AI sorgu alanları
    - Alt: Terminal görünümü
    """
    
    def __init__(self):
        super().__init__()
        
        # Core bileşenler
        self._process_manager = AdvancedProcessManager(self)
        self._orchestrator = get_orchestrator()
        self._ai_worker: AIWorker = None
        self._pending_command = None  # AI'dan gelen onay bekleyen komut
        
        # Pencere ayarları
        self.setWindowTitle("SENTINEL AI - Hibrit Güvenlik Test Aracı")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(f"background-color: {Colors.BG_PRIMARY}; color: {Colors.TEXT_PRIMARY};")
        
        self._setup_ui()
        self._connect_signals()
        self._check_services()

    def closeEvent(self, event):
        """Temizlik - thread'leri durdur, Docker ve WSL'i arka planda kapat."""
        # AI Worker çalışıyorsa durdur
        if self._ai_worker and self._ai_worker.isRunning():
            self._ai_worker.quit()
            self._ai_worker.wait(1000)
        
        # Process çalışıyorsa durdur
        if self._process_manager.is_running():
            self._process_manager.stop_process()
            
        # Geçici dosyaları temizle (Secure Cleaner)
        try:
            deleted = get_cleaner().cleanup_old_sessions(days=3)
            print(f"🧹 Temizlik: {deleted} eski session silindi.")
        except Exception as e:
            print(f"🧹 Temizlik hatası: {e}")
        
        # Docker kapatma seçenekleri
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # Kullanıcıya sor
            reply = QMessageBox.question(
                self, 
                "Docker Temizliği", 
                "Docker Motoru (VmmemWSL) tamamen kapatılsın mı?\n\n"
                "✅ Evet: RAM (~2GB) temizlenir. Sonraki açılış uzun sürer.\n"
                "❌ Hayır: Sadece servisler durur. Sonraki açılış hızlı olur.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Tam temizlik: Fişi çek!
                # Vakit kaybetmeden ve takılmadan direkt öldür.
                # docker compose down'ı beklemek bazen takılıyor.
                cmd = ["cmd", "/c", "taskkill /IM \"Docker Desktop.exe\" /F & wsl --shutdown"]
            else:
                # Standart temizlik: Sadece Docker down
                cmd = ["docker", "compose", "down"]

            # Arka planda çalıştır
            subprocess.Popen(
                cmd,
                cwd=os.getcwd(),
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        
        event.accept()
    
    def _setup_ui(self):
        """UI bileşenlerini oluştur."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
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
        title = QLabel("⚔️ SENTINEL AI")
        title.setStyleSheet(f"""
            color: {Colors.ACCENT_PRIMARY};
            font-family: {Fonts.MONO};
            font-size: 18px;
            font-weight: bold;
        """)
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Servis durumu
        self._status_local = QLabel("● Local AI")
        self._status_local.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        layout.addWidget(self._status_local)
        
        self._status_cloud = QLabel("● Cloud AI")
        self._status_cloud.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        layout.addWidget(self._status_cloud)
        
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
        
        # Butonlar
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        self._btn_reject = QPushButton("✕ İptal")
        self._btn_reject.setStyleSheet(self._get_button_style(danger=True))
        self._btn_reject.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_reject.clicked.connect(self._on_reject_command)
        btn_row.addWidget(self._btn_reject)
        
        self._btn_approve = QPushButton("✓ Çalıştır")
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
        """AI servis durumlarını kontrol et."""
        try:
            local_ok, cloud_ok = self._orchestrator.check_services()
            
            if local_ok:
                self._status_local.setText("● Local AI")
                self._status_local.setStyleSheet(f"color: {Colors.SUCCESS_BRIGHT};")
            else:
                self._status_local.setText("○ Local AI")
                self._status_local.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
            
            if cloud_ok:
                self._status_cloud.setText("● Cloud AI")
                self._status_cloud.setStyleSheet(f"color: {Colors.SUCCESS_BRIGHT};")
            else:
                self._status_cloud.setText("○ Cloud AI")
                self._status_cloud.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        except Exception:
            pass
    
    # =========================================================================
    # Event Handlers
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
            f"AI işlemi başarısız:\n{error}"
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
        """Komutu onayla ve çalıştır."""
        if not hasattr(self, '_pending_command') or not self._pending_command:
            return
        
        cmd = self._pending_command
        target = self._target_input.text().strip()
        
        # Hedef placeholder'ı değiştir
        args = [arg.replace("{target}", target) if target else arg for arg in cmd.arguments]
        
        # Komutu çalıştır (ProcessManager -> ExecutionManager otomatik halleder)
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
        """Terminal'den gelen manuel komut."""
        parts = command.split()
        if not parts:
            return
        
        tool = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        # Komutu çalıştır (ExecutionManager otomatik yönlendirir)
        self._process_manager.start_process(tool, args)


# =============================================================================
# Entry Point
# =============================================================================

def main():
    # High DPI desteği
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    print("🛡️  SENTINEL AI başlatılıyor...")
    print("   Docker servisleri başlatılıyor (Bekleyiniz)...")
    
    # Docker servislerini başlat ve BEKLE
    if os.name == 'nt':
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(
                ["docker", "compose", "up", "-d"],
                cwd=os.getcwd(),
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW,
                check=True  # Hata varsa exception fırlat
            )
            print("✅ Docker servisleri hazır.")
        except subprocess.CalledProcessError:
            print("❌ Docker başlatılamadı! Lütfen Docker Desktop'ın açık olduğundan emin olun.")
            # İsterseniz burada sys.exit() diyerek uygulamayı kapatabiliriz
            # ama belki kullanıcı local tool kullanmak ister diye devam ediyoruz.
        except Exception as e:
            print(f"❌ Beklenmedik hata: {str(e)}")
    
    window = SentinelMainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
