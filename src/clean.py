"""Data cleaning: data/raw/ -> data/processed/"""

import subprocess
import sys
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from textwrap import indent

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "raw" / "seed_lengths.csv"
PROCESSED_CSV = ROOT / "data" / "processed" / "seed_lengths.csv"
REPORT_DIR = ROOT / "data" / "processed"
FIG_DIR = ROOT / "figures" / "cleaning"

# Expected design (see data/raw/seed_lengths.md). Removing rows (e.g., an impossible value) will break these counts.
EXPECTED_BAG_COUNTS = {
    "bigs_1": 134, "bigs_2": 134, "bigs_3": 134,  # Pennsylvania
    "bigs_4": 134, "bigs_5": 134, "bigs_6": 134,  # Florida
    "david_1": 402,  # Pennsylvania
    "david_2": 402,  # Florida
}
EXPECTED_PRODUCT_COUNTS = {"BIGS": 804, "DAVID": 804}

ALLOWED_STATES = {"pa", "fl"}
BAG_PATTERN = r"^(bigs|david)_\d+$"  # lowercase brand, underscore, bag number
RESOLUTION_MM = 0.1  # caliper readings are recorded to 0.1 mm

IQR_MULTIPLIER = 1.5


# --- Load raw data ------------------------------------------------------------
def load_raw(path=RAW_CSV):
    """Return the raw main-experiment data exactly as recorded."""
    return pd.read_csv(path)


# --- Data summary -------------------------------------------------------------
def profile_data(df: pd.DataFrame):
    """Print a summary of a DataFrame."""
    print(f"Shape: {df.shape}")
    df.info()
    print()
    print(f"Descriptive statistics:\n{indent(str(df.describe(include='all')), '   ')}")


# --- Quality checks -----------------------------------------------------------
def check_overall_quality(df: pd.DataFrame):
    """Print duplicate, missing, and inconsistent-value checks for the full dataset, and assert expected counts."""
    # The raw data has no seed id, and lengths are recorded to 0.1 mm, so many distinct seeds from the same bag share
    # identical (seed_length, bag, state) rows. A non-zero count here is expected and is NOT evidence of duplicate
    # entries; this check can't distinguish the two.
    print(f"Duplicated rows: {df.duplicated().sum()} (expected; rows have no seed id, see note in clean.py)")
    print(f"Missing values (all columns): {df.isna().sum().sum()}")

    check_inconsistent_values(df)

    bag_counts = df["bag"].value_counts().to_dict()
    assert bag_counts == EXPECTED_BAG_COUNTS, f"Unexpected seeds per bag: {bag_counts}"
    print("Seeds per bag match the expected design.")


def check_inconsistent_values(df: pd.DataFrame):
    """Print rows whose labels or measurement precision don't follow the data dictionary."""
    checks = {
        "seed_length is not numeric": ~df["seed_length"].map(lambda v: isinstance(v, (int, float))),
        f"state not in {sorted(ALLOWED_STATES)}": ~df["state"].isin(ALLOWED_STATES),
        f"bag does not match '{BAG_PATTERN}'": ~df["bag"].astype(str).str.match(BAG_PATTERN),
        f"seed_length not a multiple of {RESOLUTION_MM} mm":
            ((pd.to_numeric(df["seed_length"], errors="coerce") / RESOLUTION_MM).round(6) % 1 != 0),
    }
    for description, mask in checks.items():
        print(f"Inconsistent values, {description}: {mask.sum()}")
        if mask.any():
            print(indent(df[mask].to_string(), "   "))

    # Each bag was bought in a single state.
    states_per_bag = df.groupby("bag")["state"].nunique()
    multi_state = states_per_bag[states_per_bag > 1]
    print(f"Inconsistent values, bags recorded in more than one state: {len(multi_state)}")
    if not multi_state.empty:
        print(indent(multi_state.to_string(), "   "))


# --- Derived columns ----------------------------------------------------------
def add_product(df: pd.DataFrame):
    """Return a copy of df with a `product` column (BIGS or DAVID) derived from the bag prefix."""
    out = df.copy()
    out["product"] = out["bag"].str.split("_").str[0].str.upper()
    product_counts = out["product"].value_counts().to_dict()
    assert product_counts == EXPECTED_PRODUCT_COUNTS, f"Unexpected seeds per product: {product_counts}"
    return out


# --- Outliers -----------------------------------------------------------------
def flag_outliers_iqr(df: pd.DataFrame):
    """Return a copy of df with an `outlier_iqr` column flagging values outside the IQR fences within each product.

    Fences are Q1 - 1.5 * IQR and Q3 + 1.5 * IQR. Flagged rows are kept; whether to remove or correct any of them
    (e.g., values that are physically impossible rather than just extreme) is decided and documented separately.
    """
    out = df.copy()
    grouped = out.groupby("product")["seed_length"]
    q1 = grouped.transform(lambda x: x.quantile(0.25))
    q3 = grouped.transform(lambda x: x.quantile(0.75))
    iqr = q3 - q1
    out["outlier_iqr"] = (out["seed_length"] < q1 - IQR_MULTIPLIER * iqr) | (out["seed_length"] > q3 + IQR_MULTIPLIER * iqr)
    return out


def report_outliers(df: pd.DataFrame):
    """Print the IQR fences and the flagged rows for each product."""
    for product, g in df.groupby("product"):
        q1, q3 = g["seed_length"].quantile([0.25, 0.75])
        iqr = q3 - q1
        lower, upper = q1 - IQR_MULTIPLIER * iqr, q3 + IQR_MULTIPLIER * iqr
        flagged = g[g["outlier_iqr"]].sort_values("seed_length")
        print(f"{product}: fences [{lower:.2f}, {upper:.2f}] mm, {len(flagged)} flagged")
        if not flagged.empty:
            print(indent(flagged.to_string(), "   "))


def plot_outliers_boxplot(df: pd.DataFrame, path=FIG_DIR / "outliers_boxplot.png"):
    """Save a box-and-whisker plot of seed length per product, matching the IQR outlier rule.

    Whiskers use the same multiplier as `flag_outliers_iqr`, so the points beyond them are exactly the rows flagged
    in `outlier_iqr`. Whiskers stop at the most extreme value inside the fences.
    """
    products = sorted(df["product"].unique())
    data = [df.loc[df["product"] == p, "seed_length"] for p in products]

    labels = [f"{p}\nn = {len(x)}, {df.loc[df['product'] == p, 'outlier_iqr'].sum()} outliers flagged"
              for p, x in zip(products, data)]

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.boxplot(data, tick_labels=labels, whis=IQR_MULTIPLIER,
               flierprops={"marker": "o", "markersize": 4, "markerfacecolor": "tab:red", "markeredgecolor": "none"})
    ax.set_xticklabels(labels=labels, fontsize=10, fontweight='bold')
    ax.tick_params(axis='y', labelsize=8)
    ax.set_ylabel("Seed length (mm)", fontsize=10, fontweight="bold")
    ax.set_title(f"Seed length by product", fontsize=12, fontweight='bold')
    ax.grid(axis="y", alpha=0.3)

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Box plot saved to {path.relative_to(ROOT)}")


# --- Collection session comparison --------------------------------------------
# Pennsylvania and Florida were measured in separate sessions by different people. Compare each product's
# distribution across states, and each bag's, to look for a measurement difference between sessions.
def compare_sessions(df: pd.DataFrame):
    """Print seed length summaries by product and state, and by bag."""
    summary = ["count", "mean", "std", "min", "median", "max"]

    print("By product and state:")
    print(indent(df.groupby(["product", "state"])["seed_length"].agg(summary).round(3).to_string(), "   "))
    print("By bag:")
    print(indent(df.groupby(["product", "state", "bag"])["seed_length"].agg(summary).round(3).to_string(), "   "))


# --- Save processed data ------------------------------------------------------
def save_processed(df: pd.DataFrame, path=PROCESSED_CSV):
    """Write the processed data to data/processed/."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Wrote {len(df)} rows to {path.relative_to(ROOT)}")


def print_header(title: str):
    print(f"\n{title}\n{'-' * len(title)}")


# --- Cleaning report ----------------------------------------------------------
# Everything printed during a run is also written to a timestamped report in data/processed/, so each version of
# the processed data has a record of the checks and decisions that produced it.
class Tee:
    """Write to several streams at once (here: the terminal and the report file)."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, text):
        for stream in self.streams:
            stream.write(text)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def git_revision():
    """Return the current commit hash, marked if there are uncommitted changes, or 'unknown' outside git."""
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                                text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True,
                               text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return f"{commit} (with uncommitted changes)" if dirty else commit


def print_run_info(generated: datetime):
    print("Data cleaning report")
    print(f"Generated: {generated.isoformat(timespec='seconds')}")
    print(f"Script:    {Path(__file__).relative_to(ROOT)}")
    print(f"Commit:    {git_revision()}")
    print(f"Input:     {RAW_CSV.relative_to(ROOT)}")
    print(f"Output:    {PROCESSED_CSV.relative_to(ROOT)}")


def main():
    generated = datetime.now()
    report_path = REPORT_DIR / f"seed_lengths_cleaning_report_{generated:%Y-%m-%d_%H%M%S}.txt"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as report, redirect_stdout(Tee(sys.stdout, report)):
        print_run_info(generated)
        run_cleaning()
    print(f"Report written to {report_path.relative_to(ROOT)}")


def run_cleaning():
    """Run every cleaning step in order, printing results, and save the processed data."""
    df = load_raw()

    print_header("Overall profile")
    profile_data(df)

    print_header("Quality checks")
    check_overall_quality(df)

    df = add_product(df)

    print_header(f"Outliers (IQR x {IQR_MULTIPLIER}, within product)")
    df = flag_outliers_iqr(df)
    report_outliers(df)
    plot_outliers_boxplot(df)

    print_header("Collection session comparison (PA vs. FL)")
    compare_sessions(df)

    print_header("Save")
    save_processed(df)


if __name__ == "__main__":
    main()
