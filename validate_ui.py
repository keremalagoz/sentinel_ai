
import sys
import os

print("Testing UI Imports...")

try:
    print("1. Importing Styles...", end="")
    from src.ui.styles import Colors, Fonts, MAIN_WINDOW_STYLE
    print(" OK")
    
    print("2. Importing Sidebar...", end="")
    from src.ui.sidebar import ModernSidebar
    print(" OK")
    
    print("3. Importing ChatInterface...", end="")
    from src.ui.chat_interface import ChatInterface
    print(" OK")
    
    print("4. Importing TerminalView...", end="")
    from src.ui.terminal_view import TerminalView
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
