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
    QPushButton, QSpinBox, QCheckBox, QFrame, QGroupBox
)
from PyQt6.QtCore import pyqtSignal, Qt

from src.ui.styles import Colors, Fonts


class SecuritySettingsDialog(QDialog):
    """
    Sprint 3: Guvenlik ve Temizlik Ayarlari Dialog
    """
    
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None, cleanup_handler=None):
        super().__init__(parent)
        self.setWindowTitle("Security Settings")
        self.setFixedSize(400, 350)
        self._cleanup_handler = cleanup_handler
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
        header = QLabel("Security Settings")
        header.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(header)
        
        # Session Cleanup Group
        cleanup_group = QGroupBox("Session Cleanup")
        cleanup_layout = QVBoxLayout(cleanup_group)
        
        # Auto-cleanup days
        days_layout = QHBoxLayout()
        days_label = QLabel("Delete sessions older than:")
        days_layout.addWidget(days_label)
        
        self._days_spin = QSpinBox()
        self._days_spin.setRange(1, 90)
        self._days_spin.setValue(7)
        self._days_spin.setSuffix(" days")
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
        self._secure_delete = QCheckBox("Use secure delete (overwrite before deletion)")
        self._secure_delete.setChecked(True)
        self._secure_delete.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        cleanup_layout.addWidget(self._secure_delete)
        
        layout.addWidget(cleanup_group)
        
        # Cleanup Actions Group
        actions_group = QGroupBox("Cleanup Actions")
        actions_layout = QVBoxLayout(actions_group)
        
        # Clean now button
        self._clean_btn = QPushButton("Clean Old Sessions Now")
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
        
        warning_text = QLabel("[!] Root files may require elevated privileges to delete")
        warning_text.setStyleSheet(f"color: {Colors.DANGER}; font-size: 11px;")
        warning_text.setWordWrap(True)
        warning_layout.addWidget(warning_text)
        
        layout.addWidget(warning_frame)
        
        layout.addStretch()
        
        # Dialog buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self._cancel_btn = QPushButton("Cancel")
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
        
        self._save_btn = QPushButton("Save")
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
        deleted = 0
        if self._cleanup_handler:
            deleted = self._cleanup_handler(days)
        
        if deleted > 0:
            self._status_label.setText(f"[OK] Deleted {deleted} old session(s)")
            self._status_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 11px;")
        else:
            self._status_label.setText("No sessions found to delete")
            self._status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
            
    def _on_save(self) -> None:
        """Save settings and close"""
        settings = {
            "cleanup_days": self._days_spin.value(),
            "secure_delete": self._secure_delete.isChecked()
        }
        self.settings_changed.emit(settings)
        self.accept()
        
    def get_settings(self) -> dict:
        """Return current settings"""
        return {
            "cleanup_days": self._days_spin.value(),
            "secure_delete": self._secure_delete.isChecked()
        }
