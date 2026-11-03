# Datasheet: `seed_lengths.csv`

Metadata for the raw sunflower seed kernel measurements, following the *Datasheets for Datasets* framework
(Gebru et al., 2018). This file describes the raw data exactly as collected. Cleaning steps are recorded
in `src/clean.py` and in the metadata for downstream files in `data/processed/` and `data/final/`.

## Motivation

- **Purpose:** Test whether mean kernel length differs between two competing sunflower seed products,
  BIGS Dill Pickle and DAVID Original Jumbo.
- **Created by:** @jwinkle8 and @calebbmcneill, for Duke AIPI 510: Data Sourcing, Project 2.
- **Funding:** None.

## Composition

- **Instances:** Each row is one sunflower seed kernel.
- **Size (current file):** 1608 rows, 3 columns, no missing values.

| `bag` | `state` | Rows |
|---|---|---|
| `bigs_1` | `pa` | 134 |
| `bigs_2` | `pa` | 134 |
| `bigs_3` | `pa` | 134 |
| `david_1` | `pa` | 402 |
| `bigs_4` | `fl` | 134 |
| `bigs_5` | `fl` | 134 |
| `bigs_6` | `fl` | 134 |
| `david_2` | `fl` | 402 |

- **Sample vs. population:** A sample of kernels from a small number of retail bags. It is not a random sample
  of each product's full production, so bag-to-bag and lot-to-lot variation is only partly captured.
- **Labels / targets:** `seed_length` is the outcome. `bag` (and the product derived from it) is the grouping variable.
- **Sensitive information:** None. The data contains no information about people.

### Data dictionary

| Column | Type | Description | Units / allowed values |
|---|---|---|---|
| `seed_length` | float | Length of the shelled kernel, measured with digital calipers | mm, recorded to 0.1 mm; observed range 8.1–15.9 |
| `bag` | string | The bag the kernel was sampled from: brand plus a bag id number | `bigs_1`, `bigs_2`, `bigs_3`, `bigs_4`, `bigs_5`, `bigs_6` (BIGS Dill Pickle); `david_1`, `david_2` (DAVID Original Jumbo) |
| `state` | string | US state where the bag was purchased, as a lowercase postal code | `pa` (Pennsylvania), `fl` (Florida) |

**Notes on the columns**
- The product (brand) is not its own column. Get it from the prefix of `bag` (`bigs_*` → BIGS, `david` → DAVID).
- `bag` and `state` identify the physical bag. Kernels from the same bag are not independent of one another,
  so treat bag as a potential clustering factor in the analysis.

## Collection process

- **Acquisition:** Retail bags were bought in Walmart stores. One collector bought in Pennsylvania and the other in Florida.
  - Rows 2-135: Sourced from BIGS Dill Pickle "Bag 1" purchased at Pennsylvania Walmart on October 19, 2026.
  - Rows 136-269: Sourced from BIGS Dill Pickle "Bag 2" purchased at Pennsylvania Walmart on October 19, 2026.
  - Rows 270-403: Sourced from BIGS Dill Pickle "Bag 3" purchased at Pennsylvania Walmart on October 19, 2026.
  - Rows 404-805: Sourced from DAVID Original Jumbo bag "David 1" purchased at Pennsylvania Walmart on October 19, 2026.
  - Rows 806-939: Sourced from BIGS Dill Pickle "Bag 4" purchased at Florida Walmart on October 19, 2026.
  - Rows 940-1073: Sourced from BIGS Dill Pickle "Bag 5" purchased at Florida Walmart on October 19, 2026.
  - Rows 1074-1207: Sourced from BIGS Dill Pickle "Bag 6" purchased at Florida Walmart on October 19, 2026.
  - Rows 1208-1609: Sourced from DAVID Original Jumbo bag "David 2" purchased at Florida Walmart on October 19, 2026.
- **Sampling within a bag:** Seeds were sampled by random draw without replacement. Seeds with damaged shells or kernels were discarded. Kernels that were damaged during the hulling process were discarded.
- **Measurement:** Digital calipers, read to 0.1 mm.
  - Rows 2-805: measured using a Pittsburgh 8" digital caliper; kernels were measured individually on their longer dimension from the wide base of the cotyledon to the tip of the radicle on the opposite end without zeroing the caliper; collected by @jwinkle8.
  - Rows 806-1609: measured using a ZYLTech 6" digital caliper with reported accuracy of +-0.2mm; kernels were measured individually on their longer dimension from the wide base of the cotyledon to the tip of the radicle on the opposite end without zeroing the caliper; collected by @calebbmcneill.
- **Collection period:** 10/23-10/24.
- **Ethics / IRB:** Not applicable, because no human subjects are involved.

## Preprocessing

- None. This is the raw file and must not be edited by hand after collection (see `CONTRIBUTING.md`).

## Uses

- **Intended use:** A two-group comparison of mean kernel length (BIGS vs. DAVID) for the course project.
- **Not suitable for:** General claims about either brand's entire production, or about regional differences.
  Each product–state combination has very few bags.

## Distribution and maintenance

- Stored in this repository under `data/raw/`. Maintained by the authors for the length of the course.

## Version history

| Date | Change |
|---|---|
| 2026-10-23 | Initial file: 804 Pennsylvania measurements (3 BIGS bags, 1 DAVID bag). |
| 2026-10-24 | Added Florida measurements (3 BIGS bags, 1 DAVID bag). |
| 2026-10-25 | Corrected bag numbering for Florida BIGS bags and added David 2 identifier. |
| 2026-10-25 | Corrected an entry originally recorded as 1.9 mm but was logged in handwritten entries as 11.9. |
