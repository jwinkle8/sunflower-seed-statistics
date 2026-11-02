# Datasheet: `seed_lengths.csv` (final)

The dataset used for the statistical analysis and the report. It is an unchanged copy of
`data/processed/seed_lengths.csv`, written by `src/analyze.py`, and must not be edited by hand. For composition, the
data dictionary, preprocessing, and known issues, see the processed datasheet,
[`data/processed/seed_lengths.md`](../processed/seed_lengths.md); for motivation, collection, and sampling, see the raw
datasheet, [`data/raw/seed_lengths.md`](../raw/seed_lengths.md).

## Uses

- All 1,608 rows are analyzed, including rows with `outlier_iqr = True` (the test is rank-based).
- `analysis_results.csv` in this folder holds the results computed from this file. Each run of `src/analyze.py`
  also writes `analysis_report_<YYYY-MM-DD_HHMMSS>.txt`, recording the run time, git commit, and every result. The
  most recent report matches the current files.

## Version history

| Date | Change |
|---|---|
| 2026-11-01 | Initial file: copy of the processed data (1,608 rows). |
