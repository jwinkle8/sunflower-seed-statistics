"""Check the assumptions behind the main-study tests (Mann-Whitney U, Hodges-Lehmann CI, Brunner-Munzel effect size).

Reads data/processed/seed_lengths.csv and writes figures to figures/post_test/. 

Assumptions checked:
  - independence: seeds are clustered within bags, and the bags within each product are compared to judge whether pooling them is reasonable;
  - measurement scale: lengths are continuous but recorded to 0.1 mm, so ties are counted;
  - similar spread and shape: Levene and Fligner-Killeen tests, plus skewness, IQR, and a Kolmogorov-Smirnov shape comparison. The
    Hodges-Lehmann shift interpretation needs the two distributions to have the same shape, differing only in location;
  - normality (descriptive only): Shapiro-Wilk, to confirm why a rank-based test was used.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_CSV = ROOT / "data" / "processed" / "seed_lengths.csv"
FIG_DIR = ROOT / "figures" / "post_test"

# Significance level for the assumption tests (Shapiro-Wilk, Levene, Fligner-Killeen, Kruskal-Wallis, KS).
ALPHA = 0.05
GROUP_1, GROUP_2 = "BIGS", "DAVID"


# --- Load data ----------------------------------------------------------------


def load_processed(path=PROCESSED_CSV):
    """Return the processed data: one row per seed, with columns seed_length, bag, state, product, outlier_iqr."""
    return pd.read_csv(path)


def product_groups(df):
    return {name: g["seed_length"].to_numpy() for name, g in df.groupby("product")}


def bag_groups(df, product):
    sub = df[df["product"] == product]
    return {name: g["seed_length"].to_numpy() for name, g in sub.groupby("bag")}


# --- Independence -------------------------------------------------------------
# Independence is a property of the design and can't be tested statistically. Seeds are clustered within bags, so
# seeds from the same bag may be more alike than seeds from different bags. The intraclass correlation (ICC) on
# ranks quantifies that, and the design effect, 1 + (m - 1) * ICC with m the mean bag size, shows how much the
# variance of the test statistic is understated if the clustering is ignored. DAVID has one bag per state, so
# product and bag are confounded within DAVID.


def rank_icc(df):
    """Return the one-way ANOVA estimate of the ICC of the ranks across bags, with the mean bag size."""
    ranks = df["seed_length"].rank()
    groups = [ranks[idx].to_numpy() for idx in df.groupby("bag").groups.values()]
    k, n = len(groups), len(ranks)
    sizes = np.array([len(g) for g in groups])
    grand = ranks.mean()
    ss_between = sum(len(g) * (g.mean() - grand) ** 2 for g in groups)
    ss_within = sum(((g - g.mean()) ** 2).sum() for g in groups)
    ms_between, ms_within = ss_between / (k - 1), ss_within / (n - k)
    m0 = (n - (sizes ** 2).sum() / n) / (k - 1)
    icc = (ms_between - ms_within) / (ms_between + (m0 - 1) * ms_within)
    return icc, n / k


def clustering_table(df):
    rows = []
    subsets = [("All seeds", df)] + [(p, df[df["product"] == p]) for p in (GROUP_1, GROUP_2)]
    for label, sub in subsets:
        if sub["bag"].nunique() < 2:
            continue
        icc, m = rank_icc(sub)
        rows.append({"subset": label, "bags": sub["bag"].nunique(), "mean_bag_size": m, "rank_ICC": icc,
                     "design_effect": 1 + (m - 1) * icc})
    return pd.DataFrame(rows)


def kruskal_row(label, groups):
    h, p = stats.kruskal(*groups.values())
    return {"comparison": label, "H": h, "p": p, "same_distribution_at_alpha":     p >= ALPHA}


    # --- Measurement scale and ties -----------------------------------------------


def tie_summary(df):
    values = df["seed_length"].to_numpy()
    _, counts = np.unique(values, return_counts=True)
    return {
        "n": len(values),
        "distinct_values": len(counts),
        "share_of_seeds_in_tied_values": counts[counts > 1].sum() / len(values),
        "largest_tie_group": counts.max(),
    }


# --- Similar spread and shape -------------------------------------------------


def spread_shape_table(groups):
    rows = []
    for name, x in groups.items():
        q1, q3 = np.percentile(x, [25, 75])
        rows.append({"group": name, "n": len(x), "median": np.median(x), "IQR": q3 - q1,
                     "MAD": stats.median_abs_deviation(x), "skew": stats.skew(x), "kurtosis": stats.kurtosis(x)})
    return pd.DataFrame(rows)


def spread_tests(groups):
    lev_stat, lev_p = stats.levene(*groups.values(), center="median")
    fk_stat, fk_p = stats.fligner(*groups.values())
    return pd.DataFrame([
        {"test": "Levene (median-centered)", "statistic": lev_stat, "p": lev_p, "equal_spread_at_alpha": lev_p >= ALPHA},
        {"test": "Fligner-Killeen", "statistic": fk_stat, "p": fk_p, "equal_spread_at_alpha": fk_p >= ALPHA},
    ])


def shape_after_centering(groups):
    """Two-sample Kolmogorov-Smirnov test after removing each group's median. A large p-value is consistent with a
    pure location shift, which is how the Hodges-Lehmann estimate is interpreted. Ties make the p-value approximate."""
    x, y = groups[GROUP_1], groups[GROUP_2]
    res = stats.ks_2samp(x - np.median(x), y - np.median(y))
    return pd.DataFrame([{"test": "KS on median-centered lengths", "D": res.statistic, "p": res.pvalue,
                          "same_shape_at_alpha": res.pvalue >= ALPHA}])


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
    fig.suptitle(title, fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# --- Report -------------------------------------------------------------------


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    df = load_processed()
    products = product_groups(df)

    print("Descriptive summary by bag")
    print(df.groupby("bag")["seed_length"].agg(["count", "mean", "std", "min", "max"]).round(3).to_string())

    print("\nIndependence: clustering of seeds within bags (ICC on ranks)")
    print(clustering_table(df).round(4).to_string(index=False))
    print(f"\nKruskal-Wallis across bags within each product (H0: bags share a distribution; alpha = {ALPHA})")
    kruskal = pd.DataFrame([kruskal_row(f"{p} bags", bag_groups(df, p)) for p in (GROUP_1, GROUP_2)])
    print(kruskal.round(4).to_string(index=False))

    print("\nMeasurement scale and ties (lengths recorded to 0.1 mm)")
    print(pd.DataFrame([tie_summary(df)]).round(4).to_string(index=False))

    print("\nSpread and shape by product")
    print(spread_shape_table(products).round(4).to_string(index=False))
    print(f"\nEqual spread tests (H0: equal spread; alpha = {ALPHA})")
    print(spread_tests(products).round(4).to_string(index=False))
    print(f"\nSame-shape check for a pure location shift (H0: same shape; alpha = {ALPHA})")
    print(shape_after_centering(products).round(4).to_string(index=False))

    print(f"\nShapiro-Wilk normality test (H0: data are normal; alpha = {ALPHA})")
    print(shapiro_table(products).round(4).to_string(index=False))
    plot_normality(products, FIG_DIR / "normality_product.png", "Normality-check plots by product")

    print(f"\nFigures written to {FIG_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
