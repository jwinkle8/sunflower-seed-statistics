"""Statistical analysis: test the hypotheses on the processed data. data/processed/ -> data/final/"""

import shutil
import sys
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from textwrap import indent

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.nonparametric import rank_compare_2indep

from clean import Tee, git_revision, print_header

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_CSV = ROOT / "data" / "processed" / "seed_lengths.csv"
FINAL_CSV = ROOT / "data" / "final" / "seed_lengths.csv"
RESULTS_CSV = ROOT / "data" / "final" / "analysis_results.csv"
REPORT_DIR = ROOT / "data" / "final"

# --- Hypotheses ---------------------------------------------------------------
# Fixed before main-study analysis, based on the pilot assumption checks (src/check_assumptions.py).
# H0: The BIGS Dill Pickle and DAVID Original Jumbo kernel length distributions are equal, i.e.,
#     P(BIGS > DAVID) = 0.5.
# H1: The BIGS Dill Pickle and DAVID Original Jumbo kernel length distributions are not equal, i.e.,
#     P(BIGS > DAVID) != 0.5.
# Two-sided.
# alpha: 0.05
# Groups: BIGS (six bags pooled) vs. DAVID (two bags pooled). Seeds are clustered within bags, and DAVID has one bag
# per state (see Limitations in data/processed/seed_lengths.md).
# All 1,608 rows are analyzed. IQR-flagged outliers are kept: the test is rank-based, so extreme values carry no
# more weight than any other value, and the flagged values look like genuinely small or large kernels.
# Direction: every result here is BIGS relative to DAVID (BIGS - DAVID, P(BIGS > DAVID)). The power analysis
# (src/power_analysis.py) uses P(DAVID > BIGS), which is 1 minus the value reported here.

ALPHA = 0.05
GROUP_1, GROUP_2 = "BIGS", "DAVID"


def load_processed(path=PROCESSED_CSV):
    """Return the processed data and the (BIGS, DAVID) seed lengths as arrays."""
    df = pd.read_csv(path)
    x = df.loc[df["product"] == GROUP_1, "seed_length"].to_numpy()
    y = df.loc[df["product"] == GROUP_2, "seed_length"].to_numpy()
    return df, x, y


# --- Descriptive statistics ---------------------------------------------------
def describe(df: pd.DataFrame):
    """Print seed length summaries by product, and by product and state."""
    def q1(s): return s.quantile(0.25)
    def q3(s): return s.quantile(0.75)
    summary = ["count", "mean", "std", "min", q1, "median", q3, "max"]

    print("By product:")
    print(indent(df.groupby("product")["seed_length"].agg(summary).round(3).to_string(), "   "))
    print("By product and state:")
    print(indent(df.groupby(["product", "state"])["seed_length"].agg(summary).round(3).to_string(), "   "))


# --- Hypothesis test ----------------------------------------------------------
# Planned test: Mann-Whitney U (Wilcoxon rank-sum), two independent groups.
# Rationale (pilot): Shapiro-Wilk rejected normality for both pooled groups (BIGS p = 0.004, DAVID p = 0.032);
# Q-Q plots show right skew. Levene did not reject equal variances (p = 0.536), so the groups have similar spread.
# Lengths are recorded to 0.1 mm, so there are many ties. The asymptotic (normal approximation) p-value is used,
# with scipy's tie correction to the variance and a continuity correction; the exact method assumes no ties.
def mann_whitney(x, y):
    """Return the two-sided Mann-Whitney U test of x vs. y. U is the statistic for x (BIGS)."""
    return stats.mannwhitneyu(x, y, alternative="two-sided", method="asymptotic", use_continuity=True)


# --- Confidence interval ------------------------------------------------------
# Hodges-Lehmann estimate of the location shift: the median of all n1 * n2 pairwise differences BIGS - DAVID.
# The confidence interval comes from inverting the Mann-Whitney test: it is the range of shifts d for which the
# test of (x - d) vs. y would not reject at alpha. With the normal approximation, that is the k-th smallest and
# k-th largest pairwise difference, where k = n1 * n2 / 2 - z * sd(U), using the tie-corrected sd(U).
# Because lengths are recorded to 0.1 mm, pairwise differences are multiples of 0.1 mm, and so are the estimate and
# the interval endpoints.
def tie_corrected_sd_u(x, y):
    """Return the standard deviation of U under H0, corrected for ties."""
    n1, n2 = len(x), len(y)
    n = n1 + n2
    _, tie_counts = np.unique(np.concatenate([x, y]), return_counts=True)
    tie_term = (tie_counts ** 3 - tie_counts).sum() / (n * (n - 1))
    return np.sqrt(n1 * n2 / 12 * ((n + 1) - tie_term))


def hodges_lehmann(x, y, alpha=ALPHA):
    """Return (estimate, lower, upper) for the BIGS - DAVID location shift."""
    diffs = np.sort(np.subtract.outer(x, y).ravel())
    n_pairs = len(diffs)
    z = stats.norm.ppf(1 - alpha / 2)
    k = int(np.floor(n_pairs / 2 - z * tie_corrected_sd_u(x, y)))
    # diffs is 0-indexed: the k-th smallest is diffs[k - 1], the k-th largest is diffs[n_pairs - k]
    estimate = np.round(np.median(diffs), 10)
    lower, upper = np.round(diffs[k - 1], 10), np.round(diffs[n_pairs - k], 10)
    return estimate, lower, upper


# --- Effect size --------------------------------------------------------------
# Probability of superiority, p = P(BIGS > DAVID) + 0.5 * P(BIGS = DAVID), the quantity the hypotheses are stated
# in. Its point estimate equals U / (n1 * n2). The confidence interval uses the Brunner-Munzel variance (statsmodels
# rank_compare_2indep), which allows ties and unequal variances, with the normal distribution (n is large).
# Rank-biserial correlation r = 2p - 1 (range -1 to 1, 0 = no difference); its interval transforms p's endpoints.
def effect_size(x, y, alpha=ALPHA):
    """Return the probability of superiority and the rank-biserial correlation, each with a confidence interval."""
    res = rank_compare_2indep(x, y, use_t=False)
    p = res.prob1
    p_lower, p_upper = res.conf_int(alpha=alpha)
    return {
        "prob_superiority": p, "prob_superiority_ci_lower": p_lower, "prob_superiority_ci_upper": p_upper,
        "rank_biserial": 2 * p - 1, "rank_biserial_ci_lower": 2 * p_lower - 1,
        "rank_biserial_ci_upper": 2 * p_upper - 1,
    }


# --- Save results -------------------------------------------------------------
def save_final_data(src=PROCESSED_CSV, dst=FINAL_CSV):
    """Copy the processed data, unchanged, to data/final/ as the dataset used in the report."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    print(f"Copied {src.relative_to(ROOT)} to {dst.relative_to(ROOT)}")


def save_results(results: dict, path=RESULTS_CSV):
    """Write the test, confidence interval, and effect size results as a one-row CSV."""
    pd.DataFrame([results]).to_csv(path, index=False)
    print(f"Wrote results to {path.relative_to(ROOT)}")


def print_run_info(generated: datetime):
    print("Statistical analysis report")
    print(f"Generated: {generated.isoformat(timespec='seconds')}")
    print(f"Script:    {Path(__file__).relative_to(ROOT)}")
    print(f"Commit:    {git_revision()}")
    print(f"Input:     {PROCESSED_CSV.relative_to(ROOT)}")
    print(f"Output:    {FINAL_CSV.relative_to(ROOT)}, {RESULTS_CSV.relative_to(ROOT)}")


def main():
    generated = datetime.now()
    report_path = REPORT_DIR / f"analysis_report_{generated:%Y-%m-%d_%H%M%S}.txt"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as report, redirect_stdout(Tee(sys.stdout, report)):
        print_run_info(generated)
        run_analysis()
    print(f"Report written to {report_path.relative_to(ROOT)}")


def run_analysis():
    """Run every analysis step in order, printing results, and save the final data and results."""
    df, x, y = load_processed()

    print_header("Descriptive statistics")
    describe(df)

    print_header("Hypothesis test (Mann-Whitney U, two-sided)")
    test = mann_whitney(x, y)
    decision = "Reject H0" if test.pvalue < ALPHA else "Fail to reject H0"
    print(f"n: {GROUP_1} = {len(x)}, {GROUP_2} = {len(y)}")
    print(f"U ({GROUP_1}) = {test.statistic:.1f}, p = {test.pvalue:.4g}, alpha = {ALPHA}: {decision}")

    print_header(f"Location shift (Hodges-Lehmann, {GROUP_1} - {GROUP_2})")
    hl, hl_lower, hl_upper = hodges_lehmann(x, y)
    print(f"Median of pairwise differences: {hl:.2f} mm, {1 - ALPHA:.0%} CI [{hl_lower:.2f}, {hl_upper:.2f}] mm")

    print_header("Effect size")
    es = effect_size(x, y)
    print(f"P({GROUP_1} > {GROUP_2}) + 0.5 P(tie) = {es['prob_superiority']:.3f}, "
          f"{1 - ALPHA:.0%} CI [{es['prob_superiority_ci_lower']:.3f}, {es['prob_superiority_ci_upper']:.3f}]")
    print(f"U / (n1 * n2) = {test.statistic / (len(x) * len(y)):.3f} (should match the line above)")
    print(f"Rank-biserial r = {es['rank_biserial']:.3f}, "
          f"{1 - ALPHA:.0%} CI [{es['rank_biserial_ci_lower']:.3f}, {es['rank_biserial_ci_upper']:.3f}]")

    print_header("Save")
    save_final_data()
    save_results({
        "n_bigs": len(x), "n_david": len(y), "alpha": ALPHA,
        "u_bigs": test.statistic, "p_value": test.pvalue, "reject_h0": test.pvalue < ALPHA,
        "hl_shift_mm": hl, "hl_ci_lower_mm": hl_lower, "hl_ci_upper_mm": hl_upper,
        **es,
    })


if __name__ == "__main__":
    main()
