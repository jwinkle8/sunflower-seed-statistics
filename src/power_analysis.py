"""Power analysis: statistical power of the planned test at the sample size collected."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from statsmodels.stats.nonparametric import samplesize_rank_compare_onetail

ROOT = Path(__file__).resolve().parents[1]
PILOT_CSV = ROOT / "data" / "pilot" / "pilot.csv"
FIG_DIR = ROOT / "figures" / "pilot"

# --- Assumptions -------------------------------------------------------------
# Planned test: Mann-Whitney U, two-sided, alpha = 0.05 (chosen after the pilot assumption checks; see src/analyze.py).
# Method: Happ et al. (2019), via statsmodels samplesize_rank_compare_onetail. It does not assume normality.
#   statsmodels only solves this method for sample size, so power is found by solving for the power at which
#   the required sample size equals the n per group we collected.
# Effect size: the relative effect P(DAVID > BIGS) + 0.5 * P(DAVID = BIGS), estimated from the pilot study
#   (not the main study: power computed from the data being tested is circular). The pilot BIGS sample (three bags
#   pooled) is the reference; the pilot DAVID sample stands in for the "synthetic" sample under H1.

ALPHA = 0.05
TARGET_POWER = 0.80
NOBS_RATIO = 1  # balanced design: equal seeds per product
N_PER_GROUP = 804  # 402 Pennsylvania + 402 Florida seeds per product

BIGS_COLUMNS = ["Bigs Bag 1 (mm)", "Bigs Bag 2 (mm)", "Bigs Bag 3 (mm)"]
DAVID_COLUMN = "David (mm)"


def load_pilot(path=PILOT_CSV):
    """Return (bigs, david) pilot kernel lengths in mm. BIGS bags are pooled."""
    wide = pd.read_csv(path)
    bigs = wide[BIGS_COLUMNS].stack().to_numpy()  # stack() drops the empty cells
    david = wide[DAVID_COLUMN].dropna().to_numpy()
    return bigs, david


def required_n(synthetic, reference, power):
    """Required n per group (Happ et al., 2019) to reach `power`."""
    return samplesize_rank_compare_onetail(
        synthetic_sample=synthetic,
        reference_sample=reference,
        alpha=ALPHA,
        power=power,
        nobs_ratio=NOBS_RATIO,
        alternative="two-sided",
    ).nobs_treat


def power_at_n(synthetic, reference, n_per_group):
    """Power of the two-sided Mann-Whitney U test with `n_per_group` seeds per group.

    Required n rises with power above the point where it bottoms out at zero, so search that range for the power
    whose required n equals `n_per_group`.
    """
    grid = np.linspace(0.001, 0.999, 999)
    ns = np.array([required_n(synthetic, reference, p) for p in grid])
    lower = grid[np.argmin(ns)]
    if n_per_group >= ns[-1]:
        return grid[-1]
    return brentq(lambda p: required_n(synthetic, reference, p) - n_per_group, lower, grid[-1])


def main():
    bigs, david = load_pilot()

    # Solve for power
    effect = samplesize_rank_compare_onetail(david, bigs, alpha=ALPHA, power=TARGET_POWER).relative_effect
    power = power_at_n(david, bigs, N_PER_GROUP)

    # Plot power across sample sizes for the pilot effect size
    powers = np.linspace(0.05, 0.95, 91)
    ns = [required_n(david, bigs, p) for p in powers]

    plt.plot(ns, powers, label=f"Effect size, from pilot (relative effect = {effect:.3f})")
    plt.scatter([N_PER_GROUP], [power], color="tab:orange", zorder=3,
                label=f"{N_PER_GROUP} seeds per group (power = {power:.2f})")
    plt.axhline(TARGET_POWER, color="tab:gray", linestyle=":", label=f"Target power ({TARGET_POWER})")
    plt.xlabel("Seeds per group",
               fontsize=10,
               fontweight="bold")
    plt.ylabel("Power",
               fontsize=10,
               fontweight="bold")
    plt.title(f"Power curve (alpha = {ALPHA}, two-sided)",
                fontsize=12,
                fontweight="bold")
    plt.xticks(fontsize=8)
    plt.yticks(fontsize=8)
    plt.ylim(0, 1)
    plt.grid(True)
    plt.legend(loc="lower right")

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    plt.savefig(FIG_DIR / "power_curve.png", dpi=150, bbox_inches="tight")
    plt.show()


if __name__ == "__main__":
    main()
