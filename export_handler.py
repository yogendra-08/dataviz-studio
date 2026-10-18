"""
export_handler.py
-----------------
Saving results to disk: charts as PNG images and datasets as CSV files.
"""

from pathlib import Path


class ExportError(Exception):
    """Raised when something cannot be exported (with a friendly message)."""


def _with_suffix(path, suffix):
    path = Path(path)
    return path if path.suffix.lower() == suffix else path.with_suffix(suffix)


def export_chart_png(figure, path):
    """Save a Matplotlib figure as a high-resolution PNG. Returns the saved Path."""
    if figure is None:
        raise ExportError("There is no chart to save yet. Generate one first.")
    path = _with_suffix(path, ".png")
    try:
        figure.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    except OSError as exc:
        raise ExportError(f"The chart could not be saved.\n\nDetails: {exc}") from exc
    return path


def export_dataset_csv(df, path):
    """Save a DataFrame (the current filtered view) as CSV. Returns the saved Path."""
    if df is None:
        raise ExportError("There is no dataset to export. Load a file first.")
    path = _with_suffix(path, ".csv")
    try:
        # utf-8-sig lets Excel open the file with correct characters
        df.to_csv(path, index=False, encoding="utf-8-sig")
    except OSError as exc:
        raise ExportError(f"The dataset could not be saved.\n\nDetails: {exc}") from exc
    return path
