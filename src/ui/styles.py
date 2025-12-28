"""
SENTINEL AI - Modern Design System
Professional Tactical Dashboard Aesthetic
"""

import re


class Colors:
    """Modern Dark Theme - Professional Color Palette"""
    
    BG_PRIMARY = "#0d1117"
    BG_SECONDARY = "#161b22"
    BG_TERTIARY = "#21262d"
    BG_ELEVATED = "#1c2128"
    
    BORDER_DEFAULT = "rgba(48, 54, 61, 0.6)"
    BORDER_MUTED = "rgba(48, 54, 61, 0.4)"
    
    ACCENT_PRIMARY = "#58a6ff"
    ACCENT_SECONDARY = "#bc8cff"
    ACCENT_MUTED = "rgba(88, 166, 255, 0.15)"
    
    SUCCESS = "#238636"
    SUCCESS_BRIGHT = "#3fb950"
    SUCCESS_MUTED = "rgba(35, 134, 54, 0.15)"
    
    WARNING = "#d29922"
    WARNING_MUTED = "rgba(210, 153, 34, 0.15)"
    
    DANGER = "#f85149"
    DANGER_MUTED = "rgba(248, 81, 73, 0.15)"
    
    SECURE = "#6e40c9"
    SECURE_MUTED = "rgba(110, 64, 201, 0.15)"
    
    TEXT_PRIMARY = "#e6edf3"
    TEXT_SECONDARY = "#8b949e"
    TEXT_MUTED = "#6e7681"
    TEXT_PLACEHOLDER = "#484f58"


class Fonts:
    """Typography System"""
    
    MONO = "'JetBrains Mono', 'Fira Code', 'SF Mono', 'Consolas', monospace"
    SIZE_SM = "12px"
    SIZE_MD = "13px"
    SIZE_LG = "14px"


class InteractivePatterns:
    """Interaktif prompt algılama"""
    
    PASSWORD_PATTERNS = [
        r'(?:password|passwd).{0,40}:\s*$',
        r'(?:parola|şifre|sifre).{0,40}:\s*$',
        r'(?:passphrase).{0,40}:\s*$',
        r'(?:secret|token|pin).{0,20}:\s*$',
    ]
    
    YESNO_PATTERNS = [
        r'\[y/n\]\s*:?\s*$',
        r'\[Y/n\]\s*:?\s*$',
        r'\[y/N\]\s*:?\s*$',
        r'\[Y/N\]\s*:?\s*$',
        r'\(y/n\)\s*:?\s*$',
        r'\(Y/N\)\s*:?\s*$',
        r'\[yes/no\]\s*:?\s*$',
        r'\[E/H\]\s*:?\s*$',
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


MAIN_CONTAINER_STYLE = f"""
    QWidget {{
        background-color: {Colors.BG_PRIMARY};
        color: {Colors.TEXT_PRIMARY};
    }}
"""

TERMINAL_OUTPUT_STYLE = f"""
    QTextEdit {{
        background-color: {Colors.BG_PRIMARY};
        color: {Colors.TEXT_PRIMARY};
        font-family: {Fonts.MONO};
        font-size: {Fonts.SIZE_MD};
        border: 1px solid {Colors.BORDER_MUTED};
        border-radius: 8px;
        padding: 16px;
        selection-background-color: {Colors.ACCENT_MUTED};
    }}
    
    QScrollBar:vertical {{
        background-color: transparent;
        width: 8px;
        margin: 4px 2px;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {Colors.BG_TERTIARY};
        border-radius: 4px;
        min-height: 40px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {Colors.TEXT_MUTED};
    }}
    
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        background: none;
        height: 0px;
    }}
"""

HEADER_TITLE_STYLE = f"""
    QLabel {{
        color: {Colors.ACCENT_PRIMARY};
        font-family: {Fonts.MONO};
        font-size: {Fonts.SIZE_SM};
        font-weight: 700;
        letter-spacing: 1px;
    }}
"""

def get_badge_style(variant: str = "default") -> str:
    configs = {
        "default": (Colors.TEXT_MUTED, Colors.BG_TERTIARY),
        "success": (Colors.SUCCESS, Colors.SUCCESS_MUTED),
        "warning": (Colors.WARNING, Colors.WARNING_MUTED),
        "danger": (Colors.DANGER, Colors.DANGER_MUTED),
        "info": (Colors.ACCENT_PRIMARY, Colors.ACCENT_MUTED),
        "secure": (Colors.SECURE, Colors.SECURE_MUTED),
    }
    color, bg = configs.get(variant, configs["default"])
    
    return f"""
        QLabel {{
            color: {color};
            background-color: {bg};
            font-family: {Fonts.MONO};
            font-size: 11px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 10px;
        }}
    """

INPUT_CONTAINER_STYLE = f"""
    QFrame {{
        background-color: {Colors.BG_SECONDARY};
        border: 1px solid {Colors.BORDER_MUTED};
        border-radius: 8px;
    }}
"""

INPUT_CONTAINER_ACTIVE_STYLE = f"""
    QFrame {{
        background-color: {Colors.BG_SECONDARY};
        border: 1px solid {Colors.ACCENT_PRIMARY};
        border-radius: 8px;
    }}
"""

INPUT_CONTAINER_SECURE_STYLE = f"""
    QFrame {{
        background-color: {Colors.BG_SECONDARY};
        border: 1px solid {Colors.SECURE};
        border-radius: 8px;
    }}
"""

INPUT_FIELD_STYLE = f"""
    QLineEdit {{
        background-color: transparent;
        color: {Colors.TEXT_PRIMARY};
        font-family: {Fonts.MONO};
        font-size: {Fonts.SIZE_MD};
        border: none;
        padding: 8px;
    }}
    QLineEdit::placeholder {{
        color: {Colors.TEXT_PLACEHOLDER};
    }}
"""

BTN_ICON_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: {Colors.TEXT_MUTED};
        font-size: 14px;
        border: none;
        border-radius: 6px;
        padding: 6px;
        min-width: 28px;
        max-width: 28px;
        min-height: 28px;
        max-height: 28px;
    }}
    QPushButton:hover {{
        background-color: {Colors.BG_TERTIARY};
        color: {Colors.TEXT_PRIMARY};
    }}
"""

BTN_STOP_STYLE = f"""
    QPushButton {{
        background-color: {Colors.DANGER_MUTED};
        color: {Colors.DANGER};
        font-size: 12px;
        font-weight: bold;
        border: none;
        border-radius: 6px;
        min-width: 32px;
        max-width: 32px;
        min-height: 32px;
        max-height: 32px;
    }}
    QPushButton:hover {{
        background-color: {Colors.DANGER};
        color: {Colors.TEXT_PRIMARY};
    }}
"""

ACTION_BTN_YES_STYLE = f"""
    QPushButton {{
        background-color: {Colors.SUCCESS_MUTED};
        color: {Colors.SUCCESS_BRIGHT};
        font-family: {Fonts.MONO};
        font-size: {Fonts.SIZE_MD};
        font-weight: 700;
        border: 2px solid {Colors.SUCCESS};
        border-radius: 6px;
        padding: 0px 20px;
        min-height: 34px;
        max-height: 34px;
    }}
    QPushButton:hover {{
        background-color: {Colors.SUCCESS};
        color: {Colors.TEXT_PRIMARY};
    }}
    QPushButton:pressed {{
        background-color: #1a7f37;
    }}
"""

ACTION_BTN_NO_STYLE = f"""
    QPushButton {{
        background-color: {Colors.BG_TERTIARY};
        color: {Colors.TEXT_SECONDARY};
        font-family: {Fonts.MONO};
        font-size: {Fonts.SIZE_MD};
        font-weight: 600;
        border: 2px solid {Colors.BORDER_DEFAULT};
        border-radius: 6px;
        padding: 0px 20px;
        min-height: 34px;
        max-height: 34px;
    }}
    QPushButton:hover {{
        background-color: {Colors.DANGER_MUTED};
        color: {Colors.DANGER};
        border-color: {Colors.DANGER};
    }}
    QPushButton:pressed {{
        background-color: {Colors.DANGER};
        color: {Colors.TEXT_PRIMARY};
    }}
"""
