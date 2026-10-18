"""
main.py
-------
Entry point for DataViz Studio.   Run with:   python main.py
"""

import sys


def main():
    # Make the window sharp on high-DPI Windows screens
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass  # not critical

    try:
        from dashboard import DashboardApp
    except ImportError as exc:
        print("A required package is missing:", exc)
        print("Install everything with:  pip install -r requirements.txt")
        sys.exit(1)

    app = DashboardApp()
    app.mainloop()


if __name__ == "__main__":
    main()
