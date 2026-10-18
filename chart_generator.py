"""
chart_generator.py
------------------
Builds Matplotlib figures (Bar, Line, Pie, Scatter, Histogram) from a DataFrame.

The functions return a plain ``Figure`` object, so the GUI can embed it and the
export module can save it.  No Tkinter widgets are created here.
"""

from dataclasses import dataclass

import matplotlib.dates as mdates
import pandas as pd
from matplotlib.colors import is_color_like
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

import styles

CHART_TYPES = ["Bar", "Line", "Pie", "Scatter", "Histogram"]
AGGREGATIONS = {"Sum": "sum", "Mean": "mean", "Median": "median",
                "Min": "min", "Max": "max", "Count": "count"}
COUNT_OPTION = "(Count of rows)"   # Y choice meaning "just count the rows"
MAX_CATEGORIES = 20                # bars shown at most
MAX_PIE_SLICES = 8                 # extra slices are merged into "Other"

C = styles.COLORS


class ChartError(Exception):
    """Raised with a user-friendly message when a chart cannot be drawn."""


@dataclass
class ChartSpec:
    """Everything the user chose on the Visualize page."""
    chart_type: str
    x: str
    y: str = ""
    agg: str = "Sum"
    bins: int = 10
    title: str = ""
    xlabel: str = ""
    ylabel: str = ""
    color: str = "#2563EB"
    grid: bool = True


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def _is_count(y):
    return not y or y == COUNT_OPTION


def _is_numeric(series):
    return pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)


def _is_date(series):
    return pd.api.types.is_datetime64_any_dtype(series)


def _numeric(df, column):
    """Return a column as numbers, or raise a clear error."""
    if column not in df.columns:
        raise ChartError(f"Column '{column}' was not found in the dataset.")
    series = df[column]
    if _is_date(series) or pd.api.types.is_bool_dtype(series):
        raise ChartError(f"'{column}' is not a numeric column. Choose a number column here.")
    values = pd.to_numeric(series, errors="coerce")
    if values.notna().sum() == 0:
        raise ChartError(
            f"Column '{column}' contains no numbers, so it cannot be used here.\n"
            "Choose a numeric column (for example one with prices or counts)."
        )
    return values


def _require_column(df, column, role="X"):
    if not column:
        raise ChartError(f"Please choose a column for the {role} axis.")
    if column not in df.columns:
        raise ChartError(f"Column '{column}' was not found in the dataset.")


def _label(value):
    """Short text label for a category / date value."""
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _fmt_value(value):
    return f"{value:,.0f}" if abs(value) >= 1000 else f"{value:.4g}"


def _aggregate(df, x, y, agg, sort_keys=True):
    """Group by X and either count rows or aggregate the numeric Y column."""
    if _is_count(y):
        return df[x].dropna().value_counts(sort=False)
    frame = pd.DataFrame({"_x": df[x], "_y": _numeric(df, y)}).dropna(subset=["_x"])
    grouped = frame.groupby("_x", sort=sort_keys)["_y"]
    result = grouped.count() if agg == "Count" else grouped.agg(AGGREGATIONS[agg])
    result = result.dropna()
    if result.empty:
        raise ChartError("There are no values to plot after removing missing data.")
    return result


def _style_axes(ax, spec, y_numbers=True):
    """Apply the shared clean look to a set of axes."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(C["border"])
    ax.tick_params(colors=C["muted"], labelsize=9)
    if spec.grid:
        ax.grid(True, color="#E2E8F0", linestyle="--", linewidth=0.8)
        ax.set_axisbelow(True)
    else:
        ax.grid(False)
    if y_numbers:
        ax.yaxis.set_major_formatter(
            FuncFormatter(lambda v, _: f"{v:,.0f}" if abs(v) >= 1000 else f"{v:g}"))


def _set_texts(ax, spec, default_title, default_x, default_y):
    ax.set_title(spec.title or default_title, fontsize=14, fontweight="bold",
                 color=C["navy"], pad=14)
    ax.set_xlabel(spec.xlabel or default_x, fontsize=10, color=C["text"], labelpad=8)
    ax.set_ylabel(spec.ylabel or default_y, fontsize=10, color=C["text"], labelpad=8)


# --------------------------------------------------------------------------
# One drawing function per chart type
# --------------------------------------------------------------------------
def _draw_bar(fig, df, spec):
    _require_column(df, spec.x)
    series = _aggregate(df, spec.x, spec.y, spec.agg)
    if _is_numeric(df[spec.x]) or _is_date(df[spec.x]):
        series = series.sort_index()
    else:
        series = series.sort_values(ascending=False)

    total = len(series)
    series = series.head(MAX_CATEGORIES)
    labels = [_label(v) for v in series.index]

    ax = fig.add_subplot(111)
    bars = ax.bar(range(len(series)), series.values, color=spec.color, width=0.65)
    ax.set_xticks(range(len(series)))
    rotate = len(series) > 6 or max(len(t) for t in labels) > 8
    ax.set_xticklabels(labels, rotation=40 if rotate else 0, ha="right" if rotate else "center")
    if len(series) <= 12:
        ax.bar_label(bars, labels=[_fmt_value(v) for v in series.values],
                     padding=3, fontsize=8, color=C["muted"])

    if _is_count(spec.y):
        default_title, default_y = f"Count by {spec.x}", "Count"
    else:
        default_title = f"{spec.agg} of {spec.y} by {spec.x}"
        default_y = f"{spec.agg} of {spec.y}"
    default_x = spec.x + (f"  (top {MAX_CATEGORIES} of {total} shown)" if total > MAX_CATEGORIES else "")
    _style_axes(ax, spec)
    _set_texts(ax, spec, default_title, default_x, default_y)


def _draw_line(fig, df, spec):
    _require_column(df, spec.x)
    if _is_count(spec.y):
        raise ChartError("Line charts need a numeric Y column. Choose one from the Y-axis list.")
    y_values = _numeric(df, spec.y)
    x_raw = df[spec.x]
    is_date = _is_date(x_raw)

    if is_date or _is_numeric(x_raw):
        frame = pd.DataFrame({"_x": x_raw, "_y": y_values}).dropna()
        if frame.empty:
            raise ChartError("There are no complete (X, Y) pairs to plot.")
        if frame["_x"].duplicated().any():          # several rows per X: aggregate
            series = frame.groupby("_x")["_y"].agg(AGGREGATIONS[spec.agg])
        else:
            series = frame.sort_values("_x").set_index("_x")["_y"]
        xs, tick_labels = series.index.to_numpy(), None
    else:                                           # text X: keep original order
        series = _aggregate(df, spec.x, spec.y, spec.agg, sort_keys=False)
        xs, tick_labels = list(range(len(series))), [_label(v) for v in series.index]

    ax = fig.add_subplot(111)
    marker = "o" if len(series) <= 40 else None
    ax.plot(xs, series.values, color=spec.color, linewidth=2.2, marker=marker,
            markersize=5, markerfacecolor="white", markeredgewidth=1.8)
    ax.fill_between(xs, series.values, alpha=0.08, color=spec.color)

    if tick_labels is not None:
        ax.set_xticks(xs)
        ax.set_xticklabels(tick_labels, rotation=40, ha="right")
    elif is_date:
        locator = mdates.AutoDateLocator()
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))

    _style_axes(ax, spec)
    _set_texts(ax, spec, f"{spec.y} over {spec.x}", spec.x, spec.y)


def _draw_pie(fig, df, spec):
    _require_column(df, spec.x, role="category")
    series = _aggregate(df, spec.x, spec.y, spec.agg)
    series = series[series > 0].sort_values(ascending=False)
    if series.empty:
        raise ChartError("A pie chart needs positive values, but none were found.")
    if len(series) > MAX_PIE_SLICES:
        other = series.iloc[MAX_PIE_SLICES:].sum()
        series = pd.concat([series.iloc[:MAX_PIE_SLICES], pd.Series({"Other": other})])

    # The chosen colour first, then the palette (without a duplicate)
    colors = [spec.color] + [c for c in styles.CHART_PALETTE if c.lower() != spec.color.lower()]
    labels = [_label(v) for v in series.index]

    ax = fig.add_subplot(111)
    wedges, _texts, autotexts = ax.pie(
        series.values, colors=colors[:len(series)], startangle=90, counterclock=False,
        autopct=lambda p: f"{p:.1f}%" if p >= 4 else "", pctdistance=0.78,
        wedgeprops={"edgecolor": "white", "linewidth": 2},
        textprops={"color": "white", "fontsize": 9, "fontweight": "bold"})
    ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1.0, 0.5),
              frameon=False, fontsize=9, labelcolor=C["text"])
    ax.set_title(spec.title or (f"Share of {spec.x}" if _is_count(spec.y)
                                else f"{spec.agg} of {spec.y} by {spec.x}"),
                 fontsize=14, fontweight="bold", color=C["navy"], pad=14)
    ax.axis("equal")


def _draw_scatter(fig, df, spec):
    if _is_count(spec.y):
        raise ChartError("Scatter charts need a numeric column for both X and Y.")
    _require_column(df, spec.x)
    _require_column(df, spec.y, role="Y")
    if not _is_numeric(df[spec.x]):
        raise ChartError(f"'{spec.x}' is not numeric. Scatter charts need numeric X and Y columns.")
    frame = pd.DataFrame({"_x": df[spec.x], "_y": _numeric(df, spec.y)}).dropna()
    if frame.empty:
        raise ChartError("There are no complete (X, Y) pairs to plot.")

    ax = fig.add_subplot(111)
    ax.scatter(frame["_x"], frame["_y"], color=spec.color, alpha=0.75,
               s=46 if len(frame) < 500 else 16, edgecolors="white", linewidths=0.6)
    _style_axes(ax, spec)
    ax.xaxis.set_major_formatter(
        FuncFormatter(lambda v, _: f"{v:,.0f}" if abs(v) >= 1000 else f"{v:g}"))
    _set_texts(ax, spec, f"{spec.y} vs {spec.x}", spec.x, spec.y)


def _draw_histogram(fig, df, spec):
    _require_column(df, spec.x)
    if not _is_numeric(df[spec.x]):
        raise ChartError(f"'{spec.x}' is not numeric. Histograms need a numeric column.")
    if not 1 <= spec.bins <= 200:
        raise ChartError("The number of bins must be between 1 and 200.")
    values = df[spec.x].dropna()
    if values.empty:
        raise ChartError(f"Column '{spec.x}' has no values to plot.")

    ax = fig.add_subplot(111)
    ax.hist(values, bins=spec.bins, color=spec.color, edgecolor="white", linewidth=1.2)
    _style_axes(ax, spec)
    _set_texts(ax, spec, f"Distribution of {spec.x}", spec.x, "Frequency")


_DRAWERS = {
    "Bar": _draw_bar, "Line": _draw_line, "Pie": _draw_pie,
    "Scatter": _draw_scatter, "Histogram": _draw_histogram,
}


# --------------------------------------------------------------------------
# Public function
# --------------------------------------------------------------------------
def create_chart(df, spec):
    """
    Validate the request and return a finished Matplotlib Figure.
    Raises ChartError (friendly message) if the chart cannot be created.
    """
    if df is None or df.shape[1] == 0:
        raise ChartError("Load a dataset first (Home > Browse).")
    if df.empty:
        raise ChartError("There are no rows to plot. Clear the filter and try again.")
    if spec.chart_type not in _DRAWERS:
        raise ChartError(f"Unknown chart type '{spec.chart_type}'.")
    if spec.agg not in AGGREGATIONS:
        raise ChartError(f"Unknown aggregation '{spec.agg}'.")
    if not is_color_like(spec.color):
        raise ChartError(f"'{spec.color}' is not a valid colour.")

    fig = Figure(figsize=(7.5, 4.8), dpi=100, facecolor="white", layout="constrained")
    _DRAWERS[spec.chart_type](fig, df, spec)
    return fig
