import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

print("Testing UI Imports...")

try:
    print("1. Importing Styles...", end="")
    from src.ui.styles import Colors, Fonts, MAIN_WINDOW_STYLE
    print(" OK")

    print("2. Importing ChatInterface...", end="")
    from src.ui.chat_interface import ChatInterface
    print(" OK")

    print("3. Importing TerminalView...", end="")
    from src.ui.terminal_view import TerminalView
    print(" OK")

    print("4. Importing SecuritySettingsDialog...", end="")
    from src.ui.settings_dialog import SecuritySettingsDialog
    print(" OK")

    print("5. Importing MainWindow...", end="")
    from src.ui.main_window import MainWindow
    print(" OK")

    print("\nALL UI IMPORTS SUCCESSFUL")

except ImportError as e:
    print(f"\nFAIL: Import Error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\nFAIL: Unexpected Error: {e}")
    sys.exit(1)
