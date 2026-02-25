# SENTINEL AI - Main Entry Point
# ================================
# Sprint 4: Next-Gen UI
# Yiğit (UI/UX Refactor)

import sys
import os

# Proje root'unu path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # Uygulama ikonu ve metadata buraya eklenebilir
    app.setApplicationName("Sentinel AI")
    app.setOrganizationName("MacsClub")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
