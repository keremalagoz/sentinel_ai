"""
SENTINEL AI - Security Settings Dialog
Sprint 3: Guvenlik ve Temizlik Ayarlari

Ozellikler:
- Otomatik session temizleme suresi
- Guvenli silme (shredding) secenegi
- Temizleme buton
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSpinBox, QCheckBox, QFrame, QGroupBox, QComboBox
)
from PyQt6.QtCore import pyqtSignal, Qt

from src.ui.styles import Colors, Fonts
from src.ui.i18n import t, get_available_languages


class SecuritySettingsDialog(QDialog):
    """
    Sprint 3: Guvenlik ve Temizlik Ayarlari Dialog
    """
    
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None, cleanup_handler=None, clear_all_chats_handler=None):
        super().__init__(parent)
        self.setWindowTitle(t("settings.title"))
        self.setFixedSize(450, 780)
        self._cleanup_handler = cleanup_handler
        self._clear_all_chats_handler = clear_all_chats_handler
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_PRIMARY};
                color: {Colors.TEXT_PRIMARY};
            }}
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
            }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {Colors.BG_ELEVATED};
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: {Colors.TEXT_SECONDARY};
            }}
        """)
        
        self._setup_ui()
        
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header
        header = QLabel(t("settings.title"))
        header.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(header)
        
        # Session Cleanup Group
        cleanup_group = QGroupBox(t("settings.session_cleanup"))
        cleanup_layout = QVBoxLayout(cleanup_group)
        
        # Auto-cleanup days
        days_layout = QHBoxLayout()
        days_label = QLabel(t("settings.delete_older"))
        days_layout.addWidget(days_label)
        
        self._days_spin = QSpinBox()
        self._days_spin.setRange(1, 90)
        self._days_spin.setValue(7)
        self._days_spin.setSuffix(t("settings.days_suffix"))
        self._days_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BG_ELEVATED};
                border-radius: 4px;
                padding: 4px 8px;
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        days_layout.addWidget(self._days_spin)
        days_layout.addStretch()
        cleanup_layout.addLayout(days_layout)
        
        # Secure delete checkbox
        self._secure_delete = QCheckBox(t("settings.secure_delete"))
        self._secure_delete.setChecked(True)
        self._secure_delete.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        cleanup_layout.addWidget(self._secure_delete)
        
        layout.addWidget(cleanup_group)

        # Display Group
        display_group = QGroupBox(t("settings.display"))
        display_layout = QVBoxLayout(display_group)

        font_layout = QHBoxLayout()
        font_label = QLabel(t("settings.font_size"))
        font_layout.addWidget(font_label)

        self._font_spin = QSpinBox()
        self._font_spin.setRange(11, 24)
        self._font_spin.setValue(13)
        self._font_spin.setSuffix(t("settings.px_suffix"))
        self._font_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BG_ELEVATED};
                border-radius: 4px;
                padding: 4px 8px;
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        font_layout.addWidget(self._font_spin)
        font_layout.addStretch()
        display_layout.addLayout(font_layout)

        # Language selector
        lang_layout = QHBoxLayout()
        lang_label = QLabel(t("settings.language"))
        lang_layout.addWidget(lang_label)

        self._lang_combo = QComboBox()
        self._lang_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BG_ELEVATED};
                border-radius: 4px;
                padding: 4px 8px;
                color: {Colors.TEXT_PRIMARY};
                min-width: 140px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                selection-background-color: {Colors.ACCENT_PRIMARY};
            }}
        """)
        for code, name in get_available_languages():
            self._lang_combo.addItem(name, code)
        lang_layout.addWidget(self._lang_combo)
        lang_layout.addStretch()
        display_layout.addLayout(lang_layout)

        layout.addWidget(display_group)

        # Security Policy Group
        security_group = QGroupBox(t("settings.security_policy"))
        security_layout = QVBoxLayout(security_group)

        self._confirm_root = QCheckBox(t("settings.confirm_root"))
        self._confirm_root.setChecked(True)
        self._confirm_root.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        security_layout.addWidget(self._confirm_root)

        self._warn_high_risk = QCheckBox(t("settings.warn_high_risk"))
        self._warn_high_risk.setChecked(True)
        self._warn_high_risk.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        security_layout.addWidget(self._warn_high_risk)

        auto_layout = QHBoxLayout()
        auto_label = QLabel(t("settings.auto_cleanup"))
        auto_layout.addWidget(auto_label)

        self._auto_cleanup_combo = QComboBox()
        self._auto_cleanup_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BG_ELEVATED};
                border-radius: 4px;
                padding: 4px 8px;
                color: {Colors.TEXT_PRIMARY};
                min-width: 120px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                selection-background-color: {Colors.ACCENT_PRIMARY};
            }}
        """)
        self._auto_cleanup_combo.addItem(t("settings.auto_cleanup_off"), "off")
        self._auto_cleanup_combo.addItem(t("settings.auto_cleanup_daily"), "daily")
        self._auto_cleanup_combo.addItem(t("settings.auto_cleanup_weekly"), "weekly")
        auto_layout.addWidget(self._auto_cleanup_combo)
        auto_layout.addStretch()
        security_layout.addLayout(auto_layout)

        layout.addWidget(security_group)
        
        # Connection Status Group
        status_group = QGroupBox(t("settings.connection"))
        status_layout = QVBoxLayout(status_group)
        
        # Docker status
        docker_row = QHBoxLayout()
        docker_label = QLabel(t("settings.docker"))
        docker_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        docker_row.addWidget(docker_label)
        
        self._docker_status = QLabel(t("status.checking"))
        self._docker_status.setStyleSheet(f"color: {Colors.WARNING}; font-weight: bold;")
        docker_row.addWidget(self._docker_status)
        docker_row.addStretch()
        status_layout.addLayout(docker_row)
        
        # AI model status
        ai_row = QHBoxLayout()
        ai_label = QLabel(t("settings.ai_model"))
        ai_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        ai_row.addWidget(ai_label)
        
        self._ai_status = QLabel(t("msg.offline"))
        self._ai_status.setStyleSheet(f"color: {Colors.TEXT_DIM}; font-weight: bold;")
        ai_row.addWidget(self._ai_status)
        ai_row.addStretch()
        status_layout.addLayout(ai_row)
        
        # Execution mode
        mode_row = QHBoxLayout()
        mode_label = QLabel(t("settings.mode_label"))
        mode_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        mode_row.addWidget(mode_label)
        
        self._mode_status = QLabel(t("settings.native"))
        self._mode_status.setStyleSheet(f"color: {Colors.ACCENT_PRIMARY}; font-weight: bold;")
        mode_row.addWidget(self._mode_status)
        mode_row.addStretch()
        status_layout.addLayout(mode_row)
        
        layout.addWidget(status_group)
        
        # Cleanup Actions Group
        actions_group = QGroupBox(t("settings.cleanup_actions"))
        actions_layout = QVBoxLayout(actions_group)
        
        # Clean now button
        self._clean_btn = QPushButton(t("settings.clean_now"))
        self._clean_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clean_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_ELEVATED};
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_ELEVATED};
            }}
        """)
        self._clean_btn.clicked.connect(self._on_clean_now)
        actions_layout.addWidget(self._clean_btn)

        self._clear_all_btn = QPushButton(t("settings.delete_all"))
        self._clear_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.DANGER};
                border: 1px solid {Colors.DANGER};
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(239, 68, 68, 0.12);
            }}
        """)
        self._clear_all_btn.clicked.connect(self._on_clear_all_chats)
        actions_layout.addWidget(self._clear_all_btn)
        
        # Status label
        self._status_label = QLabel("")
        self._status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        actions_layout.addWidget(self._status_label)
        
        layout.addWidget(actions_group)
        
        # Security Warning
        warning_frame = QFrame()
        warning_frame.setStyleSheet(f"""
            background-color: rgba(239, 68, 68, 0.1);
            border: 1px solid {Colors.DANGER};
            border-radius: 6px;
            padding: 10px;
        """)
        warning_layout = QVBoxLayout(warning_frame)
        warning_layout.setContentsMargins(10, 10, 10, 10)
        
        warning_text = QLabel(t("settings.root_warning"))
        warning_text.setStyleSheet(f"color: {Colors.DANGER}; font-size: 11px;")
        warning_text.setWordWrap(True)
        warning_layout.addWidget(warning_text)
        
        layout.addWidget(warning_frame)
        
        layout.addStretch()
        
        # Dialog buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self._cancel_btn = QPushButton(t("btn.cancel"))
        self._cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: none;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)
        
        self._save_btn = QPushButton(t("btn.save"))
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ACCENT_PRIMARY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.ACCENT_HOVER};
            }}
        """)
        self._save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self._save_btn)
        
        layout.addLayout(btn_layout)
        
    def _on_clean_now(self) -> None:
        """Execute cleanup with current settings"""
        days = self._days_spin.value()
        secure_delete = self._secure_delete.isChecked()
        deleted = 0
        if self._cleanup_handler:
            try:
                deleted = self._cleanup_handler(days, secure_delete=secure_delete)
            except TypeError:
                deleted = self._cleanup_handler(days)
        
        if deleted > 0:
            self._status_label.setText(t("settings.deleted_sessions").format(n=deleted))
            self._status_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 11px;")
        else:
            self._status_label.setText(t("settings.no_sessions"))
            self._status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")

    def _on_clear_all_chats(self) -> None:
        deleted = 0
        if self._clear_all_chats_handler:
            deleted = int(self._clear_all_chats_handler() or 0)

        self._status_label.setText(t("settings.deleted_chats").format(n=deleted))
        self._status_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 11px;")
            
    def _on_save(self) -> None:
        """Save settings and close"""
        settings = {
            "cleanup_days": self._days_spin.value(),
            "secure_delete": self._secure_delete.isChecked(),
            "font_size": self._font_spin.value(),
            "language": self._lang_combo.currentData(),
            "confirm_root": self._confirm_root.isChecked(),
            "warn_high_risk": self._warn_high_risk.isChecked(),
            "auto_cleanup": self._auto_cleanup_combo.currentData(),
        }
        self.settings_changed.emit(settings)
        self.accept()
        
    def get_settings(self) -> dict:
        """Return current settings"""
        return {
            "cleanup_days": self._days_spin.value(),
            "secure_delete": self._secure_delete.isChecked(),
            "font_size": self._font_spin.value(),
            "language": self._lang_combo.currentData(),
            "confirm_root": self._confirm_root.isChecked(),
            "warn_high_risk": self._warn_high_risk.isChecked(),
            "auto_cleanup": self._auto_cleanup_combo.currentData(),
        }

    def set_settings(self, settings: dict) -> None:
        """Initialize dialog fields from saved settings."""
        self._days_spin.setValue(int(settings.get("cleanup_days", self._days_spin.value())))
        self._secure_delete.setChecked(bool(settings.get("secure_delete", self._secure_delete.isChecked())))
        self._font_spin.setValue(int(settings.get("font_size", self._font_spin.value())))
        self._confirm_root.setChecked(bool(settings.get("confirm_root", True)))
        self._warn_high_risk.setChecked(bool(settings.get("warn_high_risk", True)))
        auto_cleanup = str(settings.get("auto_cleanup", "off"))
        auto_idx = self._auto_cleanup_combo.findData(auto_cleanup)
        if auto_idx >= 0:
            self._auto_cleanup_combo.setCurrentIndex(auto_idx)
        lang = settings.get("language", "en")
        idx = self._lang_combo.findData(lang)
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)
        self._confirm_root.setChecked(bool(settings.get("confirm_root", True)))
        self._warn_high_risk.setChecked(bool(settings.get("warn_high_risk", True)))
        auto_idx = self._auto_cleanup_combo.findData(settings.get("auto_cleanup", "off"))
        if auto_idx >= 0:
            self._auto_cleanup_combo.setCurrentIndex(auto_idx)

    def update_connection_status(self, docker_running: bool, ai_status_text: str, exec_mode: str) -> None:
        """Updates the labels in the connection status group."""
        if docker_running:
            self._docker_status.setText(t("settings.docker_running"))
            self._docker_status.setStyleSheet(f"color: {Colors.SUCCESS}; font-weight: bold;")
        else:
            self._docker_status.setText(t("settings.docker_stopped"))
            self._docker_status.setStyleSheet(f"color: {Colors.DANGER}; font-weight: bold;")
            
        self._ai_status.setText(ai_status_text)
        if t("msg.offline") in ai_status_text:
            self._ai_status.setStyleSheet(f"color: {Colors.DANGER}; font-weight: bold;")
        else:
            self._ai_status.setStyleSheet(f"color: {Colors.SUCCESS}; font-weight: bold;")
            
        self._mode_status.setText(exec_mode)
        if exec_mode == "DOCKER":
            self._mode_status.setStyleSheet(f"color: {Colors.SUCCESS}; font-weight: bold;")
        else:
            self._mode_status.setStyleSheet(f"color: {Colors.ACCENT_PRIMARY}; font-weight: bold;")
