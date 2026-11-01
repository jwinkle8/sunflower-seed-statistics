"""Statistical analysis: test the hypotheses on the processed data."""


# --- Hypotheses ---------------------------------------------------------------
# Fixed before main-study analysis, based on the pilot assumption checks (src/check_assumptions.py).
# H0: The BIGS Dill Pickle and DAVID Original Jumbo kernel length distributions are equal, i.e.,
#     P(BIGS > DAVID) = 0.5.
# H1: The BIGS Dill Pickle and DAVID Original Jumbo kernel length distributions are not equal, i.e.,
#     P(BIGS > DAVID) != 0.5.
# Two-sided.
# alpha: 0.05
# Groups: BIGS (three bags pooled) vs. DAVID. Seeds clustered within bags; DAVID is a single bag (see Limitations).

# --- Descriptive statistics ---------------------------------------------------


# --- Assumption checks --------------------------------------------------------


# --- Hypothesis test ----------------------------------------------------------
# Planned test: Mann-Whitney U (Wilcoxon rank-sum), two independent groups.
# Rationale (pilot): Shapiro-Wilk rejected normality for both pooled groups (BIGS p = 0.004, DAVID p = 0.032);
# Q-Q plots show right skew. Levene did not reject equal variances (p = 0.536), so the groups have similar spread.


# --- Confidence interval ------------------------------------------------------


# --- Effect size --------------------------------------------------------------


# --- Save results -------------------------------------------------------------


def main():
    pass


if __name__ == "__main__":
    main()
