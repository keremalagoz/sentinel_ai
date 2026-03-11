"""
SENTINEL AI - Design System (Sprint 4)
Theme: Deep Space (Cursor/VSCode Inspired)
"""

import re

class Colors:
    """Modern Dark Theme Palette - Deep Space"""
    
    # Base Backgrounds
    BG_PRIMARY = "#09090b"      # App Background (Deepest Black)
    BG_SECONDARY = "#18181b"    # Panel Background (Chat/Terminal)
    BG_TERTIARY = "#27272a"     # Hover/Active States
    BG_ELEVATED = "#3f3f46"     # Borders / Dividers
    BG_HOVER = "#2d2d33"        # Subtle hover (between tertiary and elevated)
    
    # Accents
    ACCENT_PRIMARY = "#3b82f6"  # Bright Blue (Cursor Style)
    ACCENT_HOVER = "#2563eb"    # Darker Blue
    ACCENT_SUBTLE = "rgba(59, 130, 246, 0.1)" # Low Opacity Blue
    ACCENT_GLOW = "rgba(59, 130, 246, 0.25)"  # Blue glow for focus effects
    
    # Gradient
    GRADIENT_START = "#0f0f14"  # Header gradient start (subtle indigo-black)
    GRADIENT_END = "#09090b"    # Header gradient end
    
    # Text
    TEXT_PRIMARY = "#f4f4f5"    # Almost White
    TEXT_SECONDARY = "#a1a1aa"  # Muted Gray
    TEXT_DIM = "#71717a"        # Dim Gray
    
    # Status
    SUCCESS = "#22c55e"
    WARNING = "#eab308"
    DANGER = "#ef4444"
    SECURE = "#8b5cf6"          # Purple
    
    # Status Indicators
    STATUS_IDLE = "#52525b"     # Gray dot
    STATUS_RUNNING = "#22c55e"  # Green dot
    STATUS_ROOT = "#ef4444"     # Red dot

class Fonts:
    """Typography System"""
    UI = "'Inter', 'Segoe UI', system-ui, sans-serif"
    MONO = "'JetBrains Mono', 'Fira Code', 'Consolas', monospace"
    
    SIZE_XS = "11px"
    SIZE_SM = "12px"
    SIZE_MD = "13px"
    SIZE_LG = "14px"
    SIZE_XL = "16px"

# --- GLOBAL WIDGET STYLES ---

MAIN_WINDOW_STYLE = f"""
    QMainWindow {{
        background-color: {Colors.BG_PRIMARY};
    }}
    QWidget {{
        color: {Colors.TEXT_PRIMARY};
        font-family: {Fonts.UI};
    }}
    QToolTip {{
        background-color: {Colors.BG_TERTIARY};
        color: {Colors.TEXT_PRIMARY};
        border: 1px solid {Colors.BG_ELEVATED};
        padding: 4px;
    }}
"""

# Alias for backward compatibility
GLOBAL_STYLE = MAIN_WINDOW_STYLE

HEADER_STYLE = f"""
    QFrame#Header {{
        background-color: {Colors.BG_PRIMARY};
        border-bottom: 1px solid {Colors.BG_ELEVATED};
    }}
    QLabel#Logo {{
        color: {Colors.TEXT_PRIMARY};
        font-weight: bold;
        font-size: 14px;
    }}
    QPushButton#HeaderBtn {{
        background-color: transparent;
        color: {Colors.TEXT_SECONDARY};
        border: none;
        padding: 6px 12px;
        border-radius: 4px;
    }}
    QPushButton#HeaderBtn:hover {{
        background-color: {Colors.BG_TERTIARY};
        color: {Colors.TEXT_PRIMARY};
    }}
"""

TAB_BAR_STYLE = f"""
    QFrame#TabBar {{
        background-color: {Colors.BG_PRIMARY};
        border-bottom: 1px solid {Colors.BG_ELEVATED};
    }}
    QPushButton.tab {{
        background-color: transparent;
        color: {Colors.TEXT_SECONDARY};
        border: none;
        padding: 8px 16px;
        border-bottom: 2px solid transparent;
    }}
    QPushButton.tab:hover {{
        color: {Colors.TEXT_PRIMARY};
        background-color: {Colors.BG_TERTIARY};
    }}
    QPushButton.tab-active {{
        color: {Colors.TEXT_PRIMARY};
        border-bottom: 2px solid {Colors.ACCENT_PRIMARY};
    }}
    QPushButton#AddTab {{
        background-color: transparent;
        color: {Colors.TEXT_DIM};
        border: none;
        padding: 8px;
    }}
    QPushButton#AddTab:hover {{
        color: {Colors.ACCENT_PRIMARY};
    }}
"""

SPLITTER_STYLE = f"""
    QSplitter::handle {{
        background-color: {Colors.BG_PRIMARY};
    }}
    QSplitter::handle:horizontal {{
        width: 1px;
    }}
    QSplitter::handle:vertical {{
        height: 1px;
    }}
"""

# --- CHAT INTERFACE STYLES ---

CHAT_CONTAINER_STYLE = f"""
    QWidget {{
        background-color: {Colors.BG_SECONDARY};
    }}
"""

CHAT_BUBBLE_USER = f"""
    QFrame {{
        background-color: {Colors.ACCENT_PRIMARY};
        border-radius: 12px;
        padding: 10px;
        border-top-right-radius: 2px;
    }}
    QLabel {{
        color: white;
        selection-background-color: white;
        selection-color: {Colors.ACCENT_PRIMARY};
    }}
"""

CHAT_BUBBLE_AI = f"""
    QFrame {{
        background-color: {Colors.BG_TERTIARY};
        border-radius: 12px;
        padding: 10px;
        border-top-left-radius: 2px;
    }}
    QLabel {{
        color: {Colors.TEXT_PRIMARY};
    }}
"""

CHAT_INPUT_AREA = f"""
    QFrame {{
        background-color: {Colors.BG_PRIMARY};
        border-top: 1px solid {Colors.BG_ELEVATED};
        padding: 16px;
    }}
    QTextEdit {{
        background-color: {Colors.BG_TERTIARY};
        border-radius: 8px;
        border: 1px solid transparent;
        padding: 8px;
        color: {Colors.TEXT_PRIMARY};
        font-family: {Fonts.UI};
    }}
    QTextEdit:focus {{
        border: 1px solid {Colors.ACCENT_PRIMARY};
    }}
"""

# --- TERMINAL STYLES ---

TERMINAL_THEME = f"""
    QTextEdit {{
        background-color: {Colors.BG_SECONDARY};
        color: {Colors.TEXT_SECONDARY};
        font-family: {Fonts.MONO};
        border: none;
        selection-background-color: {Colors.BG_ELEVATED};
    }}
"""

SCROLLBAR_MODERN = f"""
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {Colors.BG_ELEVATED};
        min-height: 20px;
        border-radius: 5px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {Colors.TEXT_DIM};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}
"""

# --- STATUS BAR ---

STATUS_BAR_STYLE = f"""
    QFrame#StatusBar {{
        background-color: {Colors.BG_PRIMARY};
        border-top: 1px solid {Colors.BG_ELEVATED};
    }}
    QLabel {{
        color: {Colors.TEXT_DIM};
        font-size: {Fonts.SIZE_XS};
        background: transparent;
        border: none;
    }}
"""

# --- ROOT BADGE ---

ROOT_BADGE_STYLE = f"""
    QLabel#RootBadge {{
        background-color: rgba(239, 68, 68, 0.15);
        color: {Colors.DANGER};
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 4px;
        padding: 2px 6px;
        font-size: {Fonts.SIZE_XS};
        font-weight: bold;
    }}
"""

# --- COMMAND CARD ENHANCED ---

COMMAND_CARD_STYLE = f"""
    QFrame#CommandCard {{
        background-color: {Colors.BG_PRIMARY};
        border: 1px solid {Colors.BG_ELEVATED};
        border-radius: 8px;
    }}
    QFrame#CommandCard:hover {{
        border: 1px solid {Colors.ACCENT_PRIMARY};
    }}
"""

# --- UTILS ---

class InteractivePatterns:
    """Legacy Pattern matching for Terminal (Keep for backward compatibility)"""
    PASSWORD_PATTERNS = [
        r'(?:password|passwd).{0,40}:\s*$',
        r'(?:parola|şifre|sifre).{0,40}:\s*$',
    ] 
    YESNO_PATTERNS = [
        r'\[y/n\]\s*:?\s*$',
        r'(?:continue|proceed|confirm).{0,20}\?\s*$',
    ]
    
    COMPILED_PASSWORD = re.compile('|'.join(PASSWORD_PATTERNS), re.IGNORECASE | re.MULTILINE)
    COMPILED_YESNO = re.compile('|'.join(YESNO_PATTERNS), re.IGNORECASE | re.MULTILINE)
    
    @classmethod
    def is_password_prompt(cls, text: str) -> bool:
        last_line = text.strip().split('\n')[-1] if text.strip() else ""
        return bool(cls.COMPILED_PASSWORD.search(last_line))
    
    @classmethod
    def is_yesno_prompt(cls, text: str) -> bool:
        last_line = text.strip().split('\n')[-1] if text.strip() else ""
        return bool(cls.COMPILED_YESNO.search(last_line))
