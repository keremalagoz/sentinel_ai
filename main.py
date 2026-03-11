# SENTINEL AI - Main Entry Point
# ================================
# Sprint 3.2+: Production Mode
# Yigit (UI/UX) & Kerem (AI/Backend)

import sys
import os
import logging
from logging.handlers import RotatingFileHandler

# Proje root'unu path'e ekle
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)


def setup_logging() -> None:
    """Merkezi logging konfigurasyonu.

    Console + rotating file handler.
    Log dosyasi: logs/sentinel.log (max 5MB, 3 backup).
    """
    log_dir = os.path.join(PROJECT_ROOT, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "sentinel.log")

    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Onceki handler'lari temizle (test ortaminda cakisma engeli)
    root_logger.handlers.clear()

    # Console handler - INFO ve uzeri
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    root_logger.addHandler(console_handler)

    # File handler - DEBUG ve uzeri, rotating
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    root_logger.addHandler(file_handler)

    logging.getLogger(__name__).info(
        "Logging initialized - file: %s", log_file
    )


from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow


def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("SENTINEL AI starting (production mode)")

    app = QApplication(sys.argv)

    # Uygulama ikonu ve metadata
    app.setApplicationName("Sentinel AI")
    app.setOrganizationName("MacsClub")

    window = MainWindow()
    window.show()

    logger.info("UI ready")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
