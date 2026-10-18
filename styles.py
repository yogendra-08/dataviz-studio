"""
styles.py
---------
Central place for colours, fonts, spacing and the ttk theme.

Every other module imports its look-and-feel from here, so changing a colour
in COLORS changes the whole application.
"""

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

# --------------------------------------------------------------------------
# Colour palette
# --------------------------------------------------------------------------
COLORS = {
    # Dark navy used for the header and sidebar
    "navy": "#0B2545",
    "sidebar": "#102A52",
    "sidebar_hover": "#1A3A6B",
    "sidebar_active": "#234A85",
    "sidebar_text": "#C9D6EE",
    # Accent colours
    "accent": "#2563EB",
    "accent_dark": "#1D4ED8",
    "accent_soft": "#DBEAFE",
    "teal": "#0D9488",
    "amber": "#D97706",
    "rose": "#E11D48",
    "green": "#16A34A",
    "violet": "#7C3AED",
    # Surfaces and text
    "bg": "#F3F6FB",
    "card": "#FFFFFF",
    "border": "#DDE3EE",
    "row_alt": "#F7F9FC",
    "heading_bg": "#EAF0FA",
    "text": "#1E293B",
    "muted": "#64748B",
    "white": "#FFFFFF",
}

# Colours offered as quick presets in the chart colour picker, and used to
# colour the extra slices of a pie chart.
CHART_PALETTE = [
    "#2563EB", "#0D9488", "#F59E0B", "#E11D48",
    "#7C3AED", "#16A34A", "#0EA5E9", "#F97316",
    "#64748B",
]

STATUS_COLORS = {
    "info": COLORS["muted"],
    "success": COLORS["green"],
    "error": COLORS["rose"],
}

# --------------------------------------------------------------------------
# Spacing
# --------------------------------------------------------------------------
PAD = 16          # standard padding inside cards and pages
PAD_SMALL = 8     # tight spacing between related widgets

# --------------------------------------------------------------------------
# Fonts
# --------------------------------------------------------------------------
FONT_FAMILY = "Segoe UI"  # replaced in apply_theme() by the best available font
_PREFERRED_FONTS = ("Segoe UI", "SF Pro Text", "Helvetica Neue", "Inter",
                    "Ubuntu", "DejaVu Sans", "Arial")


def font(size=10, weight="normal"):
    """Return a Tk font tuple using the application font family."""
    return (FONT_FAMILY, size, weight)


def apply_theme(root):
    """Configure fonts and every ttk widget style. Call once after creating root."""
    global FONT_FAMILY
    available = set(tkfont.families(root))
    for name in _PREFERRED_FONTS:
        if name in available:
            FONT_FAMILY = name
            break
    else:
        FONT_FAMILY = tkfont.nametofont("TkDefaultFont").actual("family")

    for named in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        tkfont.nametofont(named).configure(family=FONT_FAMILY, size=10)

    c = COLORS
    root.configure(bg=c["bg"])
    style = ttk.Style(root)
    style.theme_use("clam")  # "clam" lets us colour widgets on every platform

    # --- Buttons ---------------------------------------------------------
    style.configure("Accent.TButton", background=c["accent"], foreground=c["white"],
                    font=font(10, "bold"), padding=(16, 8), borderwidth=0,
                    focusthickness=0, focuscolor=c["accent"])
    style.map("Accent.TButton",
              background=[("disabled", "#9DB7EE"), ("pressed", c["accent_dark"]),
                          ("active", c["accent_dark"])],
              foreground=[("disabled", c["white"])])

    style.configure("Secondary.TButton", background=c["card"], foreground=c["accent"],
                    font=font(10, "bold"), padding=(16, 8), bordercolor=c["accent"],
                    lightcolor=c["card"], darkcolor=c["card"], focuscolor=c["card"])
    style.map("Secondary.TButton",
              background=[("pressed", c["accent_soft"]), ("active", c["accent_soft"])],
              foreground=[("disabled", c["muted"])],
              bordercolor=[("disabled", c["border"])])

    # --- Inputs ----------------------------------------------------------
    field_opts = dict(fieldbackground=c["white"], foreground=c["text"],
                      bordercolor=c["border"], lightcolor=c["white"],
                      darkcolor=c["white"], padding=6)
    style.configure("TEntry", **field_opts)
    style.configure("TCombobox", arrowcolor=c["muted"], **field_opts)
    style.configure("TSpinbox", arrowcolor=c["muted"], **field_opts)
    style.map("TEntry", bordercolor=[("focus", c["accent"])])
    style.map("TCombobox", bordercolor=[("focus", c["accent"])],
              fieldbackground=[("readonly", c["white"]), ("disabled", c["bg"])],
              foreground=[("disabled", c["muted"])])
    style.map("TSpinbox", fieldbackground=[("disabled", c["bg"])],
              foreground=[("disabled", c["muted"])])
    root.option_add("*TCombobox*Listbox.font", font(10))
    root.option_add("*TCombobox*Listbox.selectBackground", c["accent"])

    style.configure("Card.TCheckbutton", background=c["card"], foreground=c["text"],
                    font=font(10))
    style.map("Card.TCheckbutton", background=[("active", c["card"])])

    # --- Table (Treeview) ------------------------------------------------
    style.configure("Treeview", background=c["white"], fieldbackground=c["white"],
                    foreground=c["text"], rowheight=28, borderwidth=0, font=font(10))
    style.configure("Treeview.Heading", background=c["heading_bg"], foreground=c["navy"],
                    font=font(10, "bold"), padding=(8, 7), relief="flat",
                    borderwidth=0)
    style.map("Treeview.Heading", background=[("active", c["accent_soft"])])
    style.map("Treeview", background=[("selected", c["accent"])],
              foreground=[("selected", c["white"])])

    # --- Scrollbars, paned window ---------------------------------------
    for orient in ("Vertical", "Horizontal"):
        style.configure(f"{orient}.TScrollbar", background="#C3CCDB",
                        troughcolor=c["bg"], bordercolor=c["bg"], arrowsize=14,
                        relief="flat", borderwidth=0)
        style.map(f"{orient}.TScrollbar", background=[("active", "#9AA7BD")])
    style.configure("TPanedwindow", background=c["bg"])
