# DataViz Studio

An interactive desktop application for exploring and visualizing datasets, built with **Python and Tkinter**.
Upload a CSV or Excel file, preview and filter the data, view statistics, create charts and export your results —
all locally on your computer, with no web framework, database, backend or AI.

## Features

- **Upload** `.csv`, `.xlsx` and `.xls` files with a native file dialog (or load the bundled sample data)
- **Dataset preview** in a scrollable table, paged (200 rows at a time) so large files stay fast; click a heading to sort
- **Search & filter** by any column (or all columns): *Contains, Equals, Greater than, Less than*; one click restores all rows
- **Charts**: Bar, Line, Pie, Scatter and Histogram, shown inside the app with zoom / pan tools
- **Customisation**: chart title, axis labels, colour picker + presets, grid on/off, aggregation (Sum, Mean, Median, Min, Max, Count), histogram bins
- **Statistics**: row / column / missing / duplicate counts; mean, median, min, max, standard deviation and missing values for numeric columns; type, unique values and most common value for text and date columns
- **Export**: chart as PNG, current filtered / sorted dataset as CSV
- Friendly error messages for empty, malformed or unsupported files and for incompatible column choices
- Responsive layout (minimum window 1100 x 700)

## Technologies Used

| Technology | Purpose |
|---|---|
| Python 3.9+ | Core language |
| Tkinter / ttk | Desktop GUI |
| Pandas | Loading, filtering, statistics |
| Matplotlib | Charts (embedded with `FigureCanvasTkAgg`) |
| OpenPyXL / xlrd | Reading `.xlsx` / `.xls` files |

## Installation

```bash
python -m venv .venv
```

Activate the environment:

```bash
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

Install dependencies and run:

```bash
pip install -r requirements.txt
python main.py
```

> **Linux:** Tkinter is a separate system package. Install it with `sudo apt install python3-tk`.

## How to Use

1. **Home** - click **Browse...** to choose a file, or **Load Sample Data**. The filename, size and summary cards update.
2. **Data & Preview** - pick a column, a match type and a value, then **Apply Filter**. **Clear Filter** restores the original data. Click a column heading to sort.
3. **Visualize** - choose a chart type, X and Y columns, optional title / labels / colour / grid, then **Generate Chart**.
   Use the toolbar under the chart to zoom, pan or save.
4. **Statistics** - see summaries of the current (filtered) data.
5. **Export** - **Save Chart as PNG** or **Export Dataset as CSV** (exports exactly what the preview shows).

| Chart | X column | Y column |
|---|---|---|
| Bar | any column (categories) | numeric column, or *(Count of rows)* |
| Line | any column (dates / numbers work best) | numeric column |
| Pie | category column | numeric column, or *(Count of rows)* |
| Scatter | numeric column | numeric column |
| Histogram | numeric column | not used |

## File Structure

```text
dataviz-studio/
├── main.py              # Entry point
├── dashboard.py         # Main window, sidebar, all pages; connects every module
├── data_handler.py      # Load CSV/Excel, clean, search, filter, sort, paging
├── chart_generator.py   # Bar, Line, Pie, Scatter, Histogram figures
├── stats_calculator.py  # Statistics (the brief's "statistics.py", see note below)
├── export_handler.py    # Save PNG and CSV
├── styles.py            # Colours, fonts, ttk theme
├── widgets.py           # Small reusable widgets: Card, StatCard, ScrollableFrame
├── requirements.txt
├── README.md
└── sample_data.csv
```

> **Why `stats_calculator.py`?** A file called `statistics.py` would hide Python's built-in `statistics`
> module for every library in the project and can cause confusing import errors, so it was renamed.

## Sample Dataset

`sample_data.csv` contains 180 retail orders from 2025 with 11 columns: *Order ID, Date, Category, Product,
Region, Units Sold, Unit Price, Discount (%), Revenue, Customer Rating, Payment Method*.
It includes a few missing ratings and discounts so the statistics page has something to show.
Good charts to try: **Bar** Region vs Revenue, **Line** Date vs Revenue, **Pie** Category, **Scatter** Unit Price vs Revenue, **Histogram** Customer Rating.

## Screenshots

Add your own screenshots here after running the app:

| Home | Visualize | Statistics |
|---|---|---|
| `screenshots/home.png` | `screenshots/visualize.png` | `screenshots/statistics.png` |

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: tkinter` | Linux: `sudo apt install python3-tk`. Windows/macOS: reinstall Python from python.org with Tcl/Tk included. |
| `ModuleNotFoundError: pandas` (etc.) | Activate the virtual environment, then `pip install -r requirements.txt`. |
| Excel file will not open | Make sure `openpyxl` (`.xlsx`) or `xlrd` (`.xls`) is installed. Only the first sheet is read. |
| "File is empty" / "no data rows" | The file has no header or rows - open it in a spreadsheet to check. |
| Chart says a column is not numeric | Choose a number column for that axis (see the table above). |
| Chart says there are no rows | A filter removed every row - click **Clear Filter**. |
| Window looks blurry on Windows | The app enables high-DPI mode automatically; update your graphics driver if it persists. |

## Future Improvements

- Choose which Excel sheet to open
- More chart types (box plot, heat map, stacked bars) and Seaborn styling
- Colour per series and multiple Y columns
- Dark mode toggle
- Save and load chart settings
- Edit values or drop rows / columns inside the app
