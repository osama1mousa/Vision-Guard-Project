# ==========================================
# UI COLOR PALETTE & STYLES
# ==========================================
BG_DARK       = "#060A0F"
BG_PANEL      = "#0C1117"
BG_CARD       = "#111920"
BG_CARD_HOVER = "#172028"
BORDER_DIM    = "#1A2530"
BORDER_ACCENT = "#00D287"
ACCENT_CYAN   = "#00C8FF"
ACCENT_GREEN  = "#00D287"
ACCENT_RED    = "#FF4C6A"
ACCENT_AMBER  = "#FFB347"
TEXT_PRIMARY  = "#E8ECF0"
TEXT_SECONDARY= "#6B7B8D"
TEXT_DIM      = "#3D4F5F"

MAIN_STYLESHEET = f"""
    QMainWindow, QWidget#central_widget {{ background-color: {BG_DARK}; font-family: 'Segoe UI', system-ui, sans-serif; }}
    QFrame#sidebar {{ background-color: {BG_PANEL}; border-right: 1px solid {BORDER_DIM}; }}
    QFrame#panel {{ background-color: {BG_PANEL}; border-left: 1px solid {BORDER_DIM}; }}
    QFrame#card {{ background-color: {BG_CARD}; border: 1px solid {BORDER_DIM}; border-radius: 8px; }}
    QLabel {{ color: {TEXT_PRIMARY}; font-family: 'Segoe UI', system-ui, sans-serif; }}
    QLabel#text_dim {{ color: {TEXT_DIM}; letter-spacing: 1px; }}
    QLabel#text_sec {{ color: {TEXT_SECONDARY}; }}
    QPushButton {{ background-color: transparent; border: none; color: {TEXT_SECONDARY}; font-weight: bold; text-align: left; padding: 10px 15px; border-radius: 6px; }}
    QPushButton:hover {{ background-color: {BG_CARD_HOVER}; color: {TEXT_PRIMARY}; }}
    QPushButton#nav_active {{ background-color: {BG_CARD}; color: {ACCENT_GREEN}; border: 1px solid {BORDER_DIM}; }}
    QPushButton#filter_btn {{ border: 1px solid {BG_CARD_HOVER}; border-radius: 15px; text-align: center; }}
    QPushButton#filter_active {{ background-color: {BG_CARD}; color: {ACCENT_CYAN}; border: 1px solid {BORDER_DIM}; }}
    QScrollArea {{ border: none; background-color: transparent; }}
    QScrollBar:vertical {{ background: {BG_DARK}; width: 8px; }}
    QScrollBar::handle:vertical {{ background: {BORDER_DIM}; border-radius: 4px; }}
    QComboBox {{ background-color: {BG_CARD}; color: {TEXT_PRIMARY}; border: 1px solid {BORDER_DIM}; border-radius: 6px; padding: 5px 10px; font-weight: bold; }}
    QComboBox::drop-down {{ border: none; }}
"""