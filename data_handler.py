"""
data_handler.py
---------------
Everything that deals with the dataset itself: loading CSV / Excel files,
cleaning, searching, filtering, sorting and preparing rows for the preview
table.  No Tkinter code lives here.
"""

import warnings
from pathlib import Path

import pandas as pd


class DataLoadError(Exception):
    """Raised when a file cannot be loaded into a usable dataset."""


class FilterError(Exception):
    """Raised when a search / filter request is invalid."""


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
ALL_COLUMNS = "All columns"
FILTER_MODES = ("Contains", "Equals", "Greater than", "Less than")


# --------------------------------------------------------------------------
# Loading and cleaning
# --------------------------------------------------------------------------
def _read_csv(path):
    """Read a CSV, trying a couple of text encodings and delimiters."""
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError:
            continue  # try the next encoding
        except pd.errors.ParserError:
            # Unusual delimiter (; or tab)? Let pandas sniff it.
            return pd.read_csv(path, encoding=encoding, sep=None, engine="python")
    raise DataLoadError("The file's text encoding could not be recognised.")


def _read_excel(path):
    """Read the first sheet of an Excel workbook."""
    try:
        return pd.read_excel(path)
    except ImportError as exc:
        raise DataLoadError(
            "Excel support needs extra packages.\n"
            "Run:  pip install openpyxl xlrd\n\n"
            f"Details: {exc}"
        ) from exc


def _unique_column_names(columns):
    """Return clean, non-empty, unique string column names."""
    names, seen = [], {}
    for index, col in enumerate(columns):
        name = str(col).strip()
        if not name or name.lower().startswith("unnamed:"):
            name = f"Column {index + 1}"
        if name in seen:
            seen[name] += 1
            name = f"{name} ({seen[name]})"
        else:
            seen[name] = 1
        names.append(name)
    return names


def _try_parse_dates(df):
    """Convert text columns that look like dates (name contains 'date')."""
    for col in df.columns:
        series = df[col]
        if "date" not in col.lower():
            continue
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parsed = pd.to_datetime(series, errors="coerce")
        non_empty = series.notna().sum()
        if non_empty and parsed.notna().sum() >= 0.8 * non_empty:
            df[col] = parsed
    return df


def format_cell(value):
    """Turn any cell value into a short string for the preview table."""
    if value is None or (not isinstance(value, (list, tuple)) and pd.isna(value)):
        return ""
    if isinstance(value, pd.Timestamp):
        if (value.hour, value.minute, value.second) == (0, 0, 0):
            return value.strftime("%Y-%m-%d")
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, float):
        return f"{value:,.4f}".rstrip("0").rstrip(".")
    return str(value)


# --------------------------------------------------------------------------
# Filtering helpers
# --------------------------------------------------------------------------
def _as_text(series):
    """Series -> lowercase-friendly strings, with missing values as ''."""
    return series.astype(str).where(series.notna(), "")


def _column_mask(series, mode, value):
    """Boolean mask of rows in one column matching the request."""
    if mode == "Contains":
        return _as_text(series).str.contains(value, case=False, regex=False)

    if mode == "Equals":
        text_match = _as_text(series).str.strip().str.lower() == value.lower()
        if pd.api.types.is_numeric_dtype(series):
            try:
                return text_match | (series == float(value))
            except ValueError:
                pass
        return text_match

    # "Greater than" / "Less than" need numbers or dates
    if pd.api.types.is_datetime64_any_dtype(series):
        try:
            limit = pd.to_datetime(value)
        except (ValueError, TypeError) as exc:
            raise FilterError(f"'{value}' is not a valid date (try 2024-01-31).") from exc
        values = series
    else:
        try:
            limit = float(value)
        except ValueError as exc:
            raise FilterError(f"'{value}' is not a number.") from exc
        values = pd.to_numeric(series, errors="coerce")
        if values.notna().sum() == 0:
            raise FilterError(
                f"Column '{series.name}' has no numeric values, so '{mode}' cannot be used."
            )
    return values > limit if mode == "Greater than" else values < limit


def _apply_filter(df, column, mode, value):
    """Return only the rows of df that match the filter."""
    if mode not in FILTER_MODES:
        raise FilterError("Please choose a match type.")
    if not value:
        raise FilterError("Enter a value to search for.")

    if column == ALL_COLUMNS:
        if mode not in ("Contains", "Equals"):
            raise FilterError(f"'{mode}' needs a specific column. Pick one from the list.")
        mask = pd.Series(False, index=df.index)
        for col in df.columns:
            mask |= _column_mask(df[col], mode, value)
        return df[mask]

    if column not in df.columns:
        raise FilterError(f"Column '{column}' does not exist.")
    return df[_column_mask(df[column], mode, value)]


# --------------------------------------------------------------------------
# DataHandler: holds the dataset and its current view
# --------------------------------------------------------------------------
class DataHandler:
    """
    Keeps two versions of the data:

    * ``original`` - exactly what was loaded (never modified)
    * ``current``  - original + active filter + active sort (what the user sees)
    """

    def __init__(self):
        self.path = None
        self.original = None
        self.current = None
        self.filter_state = None   # (column, mode, value) or None
        self.sort_state = None     # (column, ascending) or None

    # ---- basic info -------------------------------------------------------
    @property
    def has_data(self):
        return self.original is not None

    @property
    def filename(self):
        return self.path.name if self.path else "No file selected"

    @property
    def is_filtered(self):
        return self.filter_state is not None

    def columns(self):
        return list(self.original.columns) if self.has_data else []

    def numeric_columns(self):
        if not self.has_data:
            return []
        return list(self.original.select_dtypes(include="number").columns)

    # ---- loading ----------------------------------------------------------
    def load_file(self, path):
        """Load a CSV/Excel file. Raises DataLoadError with a friendly message."""
        path = Path(path)
        if not path.is_file():
            raise DataLoadError(f"File not found:\n{path}")
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise DataLoadError(
                f"Unsupported file type '{path.suffix}'.\n"
                "Please choose a .csv, .xlsx or .xls file."
            )

        try:
            if path.suffix.lower() == ".csv":
                df = _read_csv(path)
            else:
                df = _read_excel(path)
        except DataLoadError:
            raise
        except pd.errors.EmptyDataError as exc:
            raise DataLoadError("The file is empty - there is nothing to load.") from exc
        except Exception as exc:  # malformed file, permission error, ...
            raise DataLoadError(f"The file could not be read.\n\nDetails: {exc}") from exc

        df = df.dropna(how="all").dropna(axis=1, how="all")
        if df.shape[1] == 0 or df.shape[0] == 0:
            raise DataLoadError("The file has no data rows or columns.")

        df.columns = _unique_column_names(df.columns)
        df = _try_parse_dates(df).reset_index(drop=True)

        self.path = path
        self.original = df
        self.filter_state = None
        self.sort_state = None
        self._rebuild_current()

    # ---- filter / sort ----------------------------------------------------
    def apply_filter(self, column, mode, value):
        """Filter the ORIGINAL data. Raises FilterError if the request is invalid."""
        value = (value or "").strip()
        _apply_filter(self.original, column, mode, value)  # validate first
        self.filter_state = (column, mode, value)
        self._rebuild_current()

    def clear_filter(self):
        """Remove the filter and restore every row."""
        self.filter_state = None
        self._rebuild_current()

    def sort_current(self, column, ascending=True):
        self.sort_state = (column, ascending)
        self._rebuild_current()

    def filter_description(self):
        if not self.filter_state:
            return ""
        column, mode, value = self.filter_state
        return f"{column} {mode.lower()} '{value}'"

    def _rebuild_current(self):
        df = self.original
        if self.filter_state:
            df = _apply_filter(df, *self.filter_state)
        if self.sort_state:
            column, ascending = self.sort_state
            try:
                df = df.sort_values(column, ascending=ascending, na_position="last",
                                    kind="mergesort")
            except TypeError:  # mixed text/number column
                df = df.sort_values(column, ascending=ascending, na_position="last",
                                    key=lambda s: s.astype(str), kind="mergesort")
        self.current = df.reset_index(drop=True)

    # ---- preview ----------------------------------------------------------
    def total_pages(self, page_size):
        if not self.has_data:
            return 1
        return max(1, -(-len(self.current) // page_size))

    def get_page_rows(self, page, page_size):
        """Return one page of the current data as lists of display strings."""
        start = page * page_size
        chunk = self.current.iloc[start:start + page_size]
        return [[format_cell(v) for v in row]
                for row in chunk.itertuples(index=False, name=None)]
