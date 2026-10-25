"""Power analysis: justify the sample size before collecting data."""

from math import ceil

import matplotlib.pyplot as plt
import numpy as np
from statsmodels.stats.power import TTestIndPower


# --- Assumptions -------------------------------------------------------------
# State the planned test, effect size (and where it came from), alpha, and power.
# Planned test: Mann-Whitney U, two-sided, alpha = 0.05, power = 0.80 (chosen after the pilot assumption checks;
# see src/analyze.py).
# Pilot study results:
# BIGS: mean = 11.757, std = 0.942
# David: mean = 11.849, std = 1.049
# Pooled std ≈ 0.995

effect_size = (11.849 - 11.757) / 0.995  # Cohen's d ≈ 0.092


def main():
    # --- Solve for sample size -------------------------------------------------
    analysis = TTestIndPower()
    required_n = analysis.solve_power(
        effect_size=effect_size,
        alpha=0.05,
        power=0.80,
        alternative="two-sided",
    )
    sample_size = ceil(required_n)
    print(f"Required sample size per group: {sample_size}")

    # --- Sensitivity / power curve ---------------------------------------------
    effect_sizes = np.linspace(0.01, 0.1, 100)
    powers = analysis.power(
        effect_size=effect_sizes,
        nobs1=sample_size,
        alpha=0.05,
        alternative="two-sided",
    )
    plt.plot(effect_sizes, powers, label=f"{sample_size} observations per group")
    plt.axvline(effect_size, color="tab:orange", linestyle="--", label=" Main Study effect size")
    plt.axhline(0.80, color="tab:gray", linestyle=":", label="Target power (0.80)")
    plt.xlabel("Effect size (Cohen's d)")
    plt.ylabel("Power")
    plt.title("Sensitivity / power curve")
    plt.ylim(0, 1)
    plt.grid(True)
    plt.legend()
    plt.show()


if __name__ == "__main__":
    main()
