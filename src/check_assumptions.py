"""Check parametric test assumptions (independence, normality, equal variance) on the pilot data.

Reads data/pilot/pilot.csv and writes figures to figures/pilot/. Assumption test results print to stdout.

Checks are run at two levels:
  - product: BIGS (three bags pooled) vs. DAVID, the comparison the study is about;
  - bag: the three BIGS bags against each other, to judge whether pooling them is reasonable.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
PILOT_CSV = ROOT / "data" / "pilot" / "pilot.csv"
FIG_DIR = ROOT / "figures" / "pilot"

# Significance level for the assumption tests (Shapiro-Wilk, Levene).
ALPHA = 0.05

# Pilot columns -> bag ids matching data/raw/seed_lengths.csv. The summary-statistic columns are ignored.
BAG_COLUMNS = {
    "Bigs Bag 1 (mm)": "bigs_1",
    "Bigs Bag 2 (mm)": "bigs_2",
    "Bigs Bag 3 (mm)": "bigs_3",
    "David (mm)": "david",
}


# --- Load data ----------------------------------------------------------------


def load_pilot(path=PILOT_CSV):
    """Return the pilot data in long format: one row per seed, with columns order, bag, product, and seed_length."""
    wide = pd.read_csv(path, usecols=["Number", *BAG_COLUMNS])
    long = (
        wide.rename(columns={"Number": "order", **BAG_COLUMNS})
        .melt(id_vars="order", var_name="bag", value_name="seed_length")
        .dropna(subset=["seed_length"])
    )
    long["product"] = long["bag"].str.split("_").str[0].str.upper()
    return long.reset_index(drop=True)


def product_groups(df):
    return {name: g["seed_length"].to_numpy() for name, g in df.groupby("product")}


def bigs_bag_groups(df):
    bigs = df[df["product"] == "BIGS"]
    return {name: g["seed_length"].to_numpy() for name, g in bigs.groupby("bag")}


# --- Independence -------------------------------------------------------------
# Independence is a property of the design and can't be tested statistically. Reasoning to report:
#   - Each seed is measured once, so there are no repeated measures of the same unit.
#   - Seeds are clustered within bags. Seeds from the same bag share a production lot, so they may be more similar
#     to one another than to seeds from other bags. With one DAVID bag, product and bag are confounded for DAVID.
#   - Measurements were taken in order, so drift over time (caliper zeroing, measurer fatigue) could autocorrelate
#     them. The order plot below is a visual check for that.


def plot_measurement_order(df, path):
    bags = sorted(df["bag"].unique())
    fig, axes = plt.subplots(len(bags), 1, figsize=(8, 2.2 * len(bags)), sharey=True)
    for ax, bag in zip(axes, bags):
        g = df[df["bag"] == bag].sort_values("order")
        ax.plot(g["order"], g["seed_length"], marker="o", markersize=4, linewidth=1)
        ax.axhline(g["seed_length"].mean(), color="gray", linestyle="--", linewidth=1)
        ax.set_title(bag, loc="left", fontsize=10)
        ax.set_ylabel("Length (mm)")
    axes[-1].set_xlabel("Measurement order")
    fig.suptitle("Seed length vs. measurement order (dashed line = bag mean)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# --- Normality ----------------------------------------------------------------


def shapiro_table(groups):
    rows = []
    for name, x in groups.items():
        w, p = stats.shapiro(x)
        rows.append({"group": name, "n": len(x), "W": w, "p": p, "normal_at_alpha": p >= ALPHA})
    return pd.DataFrame(rows)


def plot_normality(groups, path, title):
    """Histogram (top row) and Q-Q plot (bottom row) for each group."""
    fig, axes = plt.subplots(2, len(groups), figsize=(4 * len(groups), 7), squeeze=False)
    for i, (name, x) in enumerate(groups.items()):
        hist_ax, qq_ax = axes[0, i], axes[1, i]
        hist_ax.hist(x, bins="auto", edgecolor="white")
        hist_ax.set_title(f"{name} (n = {len(x)})", fontsize=12)
        hist_ax.set_xlabel("Length (mm)", fontsize=10)
        hist_ax.set_ylabel("Count", fontsize=10)
        stats.probplot(x, dist="norm", plot=qq_ax)
        qq_ax.set_title(f"{name}: normal Q-Q", fontsize=12)
    fig.suptitle(title, fontsize=14, fontweight='bold')
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# --- Equal variance -----------------------------------------------------------


def levene_row(label, groups):
    stat, p = stats.levene(*groups.values(), center="median")
    return {"comparison": label, "W": stat, "p": p, "equal_var_at_alpha": p >= ALPHA}


# --- Report -------------------------------------------------------------------


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    df = load_pilot()
    products = product_groups(df)
    bags = bigs_bag_groups(df)

    print("Descriptive summary by bag")
    print(df.groupby("bag")["seed_length"].agg(["count", "mean", "std", "min", "max"]).round(3).to_string())

    plot_measurement_order(df, FIG_DIR / "measurement_order.png")

    print(f"\nShapiro-Wilk normality test (H0: data are normal; alpha = {ALPHA})")
    print("Product level:")
    print(shapiro_table(products).round(4).to_string(index=False))
    print("BIGS bag level:")
    print(shapiro_table(bags).round(4).to_string(index=False))
    plot_normality(products, FIG_DIR / "normality_product.png", "Normality-check plots by product")
    plot_normality(bags, FIG_DIR / "normality_bigs_bags.png", "Normality-check plots by BIGS bag")

    print(f"\nLevene's test, median-centered (H0: equal variances; alpha = {ALPHA})")
    levene = pd.DataFrame([
        levene_row("BIGS vs. DAVID", products),
        levene_row("bigs_1 vs. bigs_2 vs. bigs_3", bags),
    ])
    print(levene.round(4).to_string(index=False))

    print(f"\nFigures written to {FIG_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
