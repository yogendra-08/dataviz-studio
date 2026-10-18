"""
stats_calculator.py
-------------------
Statistical summaries of a pandas DataFrame.

NOTE: this is the "statistics" module from the project brief.  It is called
stats_calculator.py because a file named statistics.py would hide Python's
built-in `statistics` module and can break other libraries.
"""

import pandas as pd

NUMERIC_COLUMNS = ["Column", "Count", "Mean", "Median", "Min", "Max", "Std Dev", "Missing"]
CATEGORY_COLUMNS = ["Column", "Type", "Unique", "Most Common", "Frequency", "Missing"]


def dataset_overview(df):
    """Headline numbers for the statistics cards."""
    return {
        "rows": len(df),
        "columns": df.shape[1],
        "missing": int(df.isna().sum().sum()),
        "duplicates": int(df.duplicated().sum()),
        "numeric_columns": len(df.select_dtypes(include="number").columns),
    }


def numeric_summary(df):
    """One row per numeric column: count, mean, median, min, max, std, missing."""
    rows = []
    for col in df.select_dtypes(include="number").columns:
        s = df[col]
        rows.append({
            "Column": col,
            "Count": int(s.count()),
            "Mean": s.mean(),
            "Median": s.median(),
            "Min": s.min(),
            "Max": s.max(),
            "Std Dev": s.std(),  # NaN when there are fewer than 2 values
            "Missing": int(s.isna().sum()),
        })
    return pd.DataFrame(rows, columns=NUMERIC_COLUMNS)


def _friendly_type(series):
    if pd.api.types.is_datetime64_any_dtype(series):
        return "Date"
    if pd.api.types.is_bool_dtype(series):
        return "Boolean"
    return "Text"


def _display(value):
    """Dates without the 00:00:00 time part; everything else as text."""
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    return str(value)


def categorical_summary(df):
    """One row per non-numeric column: type, unique values, most common value."""
    rows = []
    for col in df.columns.difference(df.select_dtypes(include="number").columns, sort=False):
        s = df[col]
        counts = s.dropna().value_counts()
        rows.append({
            "Column": col,
            "Type": _friendly_type(s),
            "Unique": int(s.nunique()),
            "Most Common": _display(counts.index[0]) if len(counts) else "-",
            "Frequency": int(counts.iloc[0]) if len(counts) else 0,
            "Missing": int(s.isna().sum()),
        })
    return pd.DataFrame(rows, columns=CATEGORY_COLUMNS)


def format_number(value, decimals=2):
    """Readable number for tables: 1,234.57 ; whole numbers without decimals."""
    if value is None or pd.isna(value):
        return "-"
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.{decimals}f}"
