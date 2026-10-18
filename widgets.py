"""
widgets.py
----------
Small reusable Tkinter building blocks: Card, StatCard and ScrollableFrame.
"""

import sys
import tkinter as tk
from tkinter import ttk

import styles

C = styles.COLORS


class Card(tk.Frame):
    """A white panel with a thin border and an optional title.  Put content in .body"""

    def __init__(self, parent, title=None, padding=styles.PAD):
        super().__init__(parent, bg=C["card"], highlightthickness=1,
                         highlightbackground=C["border"], highlightcolor=C["border"], bd=0)
        top_pad = padding
        if title:
            tk.Label(self, text=title, bg=C["card"], fg=C["text"],
                     font=styles.font(12, "bold")).pack(anchor="w", padx=padding,
                                                         pady=(padding - 2, 0))
            tk.Frame(self, bg=C["border"], height=1).pack(fill="x", padx=padding, pady=(8, 0))
            top_pad = 12
        self.body = tk.Frame(self, bg=C["card"])
        self.body.pack(fill="both", expand=True, padx=padding, pady=(top_pad, padding))


class StatCard(tk.Frame):
    """A small card with a coloured top stripe, a big number and a caption."""

    def __init__(self, parent, caption, accent):
        super().__init__(parent, bg=C["card"], highlightthickness=1,
                         highlightbackground=C["border"], highlightcolor=C["border"], bd=0)
        tk.Frame(self, bg=accent, height=4).pack(fill="x")
        self._value = tk.Label(self, text="-", bg=C["card"], fg=C["navy"],
                               font=styles.font(22, "bold"))
        self._value.pack(anchor="w", padx=16, pady=(10, 0))
        tk.Label(self, text=caption, bg=C["card"], fg=C["muted"],
                 font=styles.font(10)).pack(anchor="w", padx=16, pady=(0, 12))

    def set(self, value):
        self._value.configure(text=value)


class ScrollableFrame(tk.Frame):
    """A vertically scrollable area. Add widgets to the .inner frame."""

    def __init__(self, parent, bg=None, width=300):
        bg = bg or C["card"]
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0, width=width)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(self.canvas, bg=bg)
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self._window, width=e.width))

        # Mouse wheel works only while the pointer is over this frame
        self.bind("<Enter>", self._bind_wheel)
        self.bind("<Leave>", self._unbind_wheel)

    def _bind_wheel(self, _event=None):
        self.bind_all("<MouseWheel>", self._on_wheel)
        self.bind_all("<Button-4>", self._on_wheel)   # Linux scroll up
        self.bind_all("<Button-5>", self._on_wheel)   # Linux scroll down

    def _unbind_wheel(self, event=None):
        # Moving onto a child widget also fires <Leave>; ignore that case.
        if event is not None:
            try:
                widget = self.winfo_containing(event.x_root, event.y_root)
            except KeyError:
                widget = None
            if widget is not None and str(widget).startswith(str(self)):
                return
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.unbind_all(sequence)

    def _on_wheel(self, event):
        if self.inner.winfo_reqheight() <= self.canvas.winfo_height():
            return  # everything already fits
        if event.num == 4:
            step = -1
        elif event.num == 5:
            step = 1
        elif sys.platform == "darwin":
            step = -event.delta
        else:
            step = -int(event.delta / 120)
        self.canvas.yview_scroll(step, "units")
