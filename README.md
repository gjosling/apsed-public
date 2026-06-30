# APSED Headcount Dataset

A Python pipeline that downloads APSC APS Employment Data (APSED) Excel releases, parses headcount tables across two output formats, and produces clean longitudinal datasets of APS headcount by agency, job family, and snapshot date.

The dataset covers twice-yearly snapshots from June 2020 to December 2025. It is designed to pair with the [APS Gazette vacancies dataset](https://github.com/gjosling/aps-gazette-public), using the APSC 2025 Job Family Framework as the common taxonomy.

## Dataset

All output files are available for download:

**Agency × job family** (`apsed_agency_jf`): [Parquet](https://data.foiforest.org/apsed/apsed_agency_jf.parquet) · [CSV](https://data.foiforest.org/apsed/apsed_agency_jf.csv)

**Agency headcount** (`apsed_agency_headcount`): [Parquet](https://data.foiforest.org/apsed/apsed_agency_headcount.parquet) · [CSV](https://data.foiforest.org/apsed/apsed_agency_headcount.csv)

**APS-wide totals** (`apsed_totals_jf`): [Parquet](https://data.foiforest.org/apsed/apsed_totals_jf.parquet) · [CSV](https://data.foiforest.org/apsed/apsed_totals_jf.csv)

This dataset is updated manually when new APSED releases are published by the APSC (typically every six months).

**`data/apsed_agency_jf.csv`:** headcount by agency × job family (Jun 2024 onwards)

The APSC first published an agency-level breakdown by job family in the June 2024 release. Each row is one agency × job family combination for a single snapshot date.

| Column | Description |
|--------|-------------|
| `snapshot_date` | Employment count date (30 June or 31 December) |
| `taxonomy_regime` | Taxonomy version in force at that date (see below) |
| `agency` | Agency name as it appears in the source APSED table |
| `agency_canonical` | Canonical agency name for joining against the APS Gazette vacancies dataset `agency_canonical` column |
| `is_sub_agency` | `True` if the row is a sub-agency; `False` for portfolio departments |
| `parent_agency` | Portfolio department name for sub-agencies; null for portfolio department rows |
| `job_family` | Job family label as it appears in the source table (may vary by regime) |
| `job_family_key` | SCREAMING_SNAKE_CASE key for joining against the gazette `job_family` column; null where no gazette equivalent exists (see data dictionary) |
| `headcount` | Employee count; null where the source cell contains `"."` (most likely zero employees or not applicable) |

**`data/apsed_agency_headcount.csv`:** total headcount by agency (Jun 2020 onwards)

Each row is one agency or sub-agency for a single snapshot date, with headcount split into ongoing and non-ongoing employment categories. Covers all 12 releases from Jun 2020 to Dec 2025. Unlike the job family files, this file counts all employees at every date, including those whose job family is unclassified. Before Jun 2024, those employees do not appear in the job family tables; they are present here throughout.

| Column | Description |
|--------|-------------|
| `snapshot_date` | Employment count date (30 June or 31 December) |
| `agency` | Agency name as it appears in the source APSED table |
| `agency_canonical` | Canonical agency name for joining against the APS Gazette vacancies dataset `agency_canonical` column |
| `is_sub_agency` | `True` if the row is a sub-agency; `False` for portfolio departments |
| `parent_agency` | Portfolio department name for sub-agencies; null for portfolio department rows |
| `headcount_ongoing` | Ongoing employee count; null where the source cell contains `"."` (most likely zero) |
| `headcount_non_ongoing` | Non-ongoing employee count; null where the source cell contains `"."` (most likely zero non-ongoing staff) |
| `headcount_total` | Total employee count; null where the source cell contains `"."` |

**`data/apsed_totals_jf.csv`:** APS-wide headcount by job family (Jun 2020 onwards)

Each row is one job family for a single snapshot date, representing the APS-wide total across all agencies.

| Column | Description |
|--------|-------------|
| `snapshot_date` | Employment count date (30 June or 31 December) |
| `taxonomy_regime` | Taxonomy version in force at that date |
| `job_family` | Job family label as it appears in the source table |
| `headcount` | APS-wide employee count for that family |

**`data/crosswalk.csv`:** taxonomy crosswalk (committed reference file)

Maps every job family label in each taxonomy regime to its Regime 3 (APSC 2025 Job Family Framework) equivalent. Columns: `regime`, `family_label`, `regime3_family`, `mapping_type` (same/rename/merge/split/discontinued), `notes`.

See [`docs/data_dictionary.md`](docs/data_dictionary.md) for full column documentation.

## Pipeline

Scripts are numbered in execution order:

| Script | What it does |
|--------|-------------|
| `01_download.py` | Download all APSED Excel files from the APSC using `data/releases.csv` as the manifest. Skips files already present. |
| `02_parse.py` | Parse the agency × job family cross-tabulation table (Table 88) from all eligible releases. Outputs `data/apsed_agency_jf.csv`. |
| `03_parse_totals.py` | Parse APS-wide job family headcount totals from all releases. Outputs `data/apsed_totals_jf.csv`. |
| `04_parse_agency_headcount.py` | Parse agency-level total headcount from Table 2 in all releases. Outputs `data/apsed_agency_headcount.csv`. |
| `validate.py` | Sanity-check all outputs against each other and the crosswalk. Run after regenerating outputs. |
| `r2_sync.py` | Publish output files to Cloudflare R2 public bucket. Used by CI. |

To run locally:

```bash
uv sync

uv run python pipeline/01_download.py      # downloads Excel files to data/xlsx/
uv run python pipeline/02_parse.py
uv run python pipeline/03_parse_totals.py
uv run python pipeline/04_parse_agency_headcount.py
uv run python pipeline/validate.py         # optional: verify outputs
```

## Repository structure

| Path | Contents |
|------|----------|
| `pipeline/` | Numbered pipeline scripts and utilities (`validate.py`, `r2_sync.py`) |
| `data/` | Reference files (`releases.csv`, `crosswalk.csv`) and generated outputs (gitignored) |
| `data/xlsx/` | Downloaded APSED Excel files (gitignored) |
| `docs/` | Data dictionary |

## Taxonomy regimes

The APSC's job family taxonomy changed across releases. The dataset preserves job family labels exactly as they appear in each release, with a `taxonomy_regime` column identifying which version applies. A crosswalk in `data/crosswalk.csv` documents the label-by-label mappings to the Regime 3 canonical names.

| Regime | Releases | Families | Key changes |
|--------|----------|----------|-------------|
| 1 | Jun 2020, Dec 2020 | 20 (22 labels) | Original taxonomy. Science and Health are separate families. "Organisation Leadership" and "Strategic Policy" in use. |
| 2a | Jun 2021–Jun 2023 | 19 | "Science" and "Health" merged into a single "Science and Health" family. "Senior Executive" introduced (renamed from "Organisation Leadership"). "Data and Research" introduced (renamed from "Research"). "Policy" and "Portfolio, Program and Project Management" replace earlier labels. "Development Programme" declining. |
| 2b | Dec 2023 | 18 | Development Programme dropped (headcount had dwindled to near zero). |
| 2b+ | Jun 2024–Jun 2025 | 19 | Agency × job family cross-tabulation first appears. "No data" unclassified column added (tens of thousands of staff, roughly 10–15% of the APS per snapshot). |
| 3 | Dec 2025 | 17 | 2025 Job Family Framework: Science and Health split back into separate families. "Administration" → "Business and Organisational Management". Several renames and merges. 16 substantive families + "No data". |

*Regime 1 label count: Dec 2020 uses "Program" (American spelling) where Jun 2020 uses "Programme" for two family names, giving 22 distinct labels across the two releases for 20 conceptual families. See the [data dictionary](docs/data_dictionary.md) for details.*

## Key caveats

**Families with no gazette join key.** Four `job_family` values in `apsed_agency_jf.csv` have a null `job_family_key` and cannot be joined to the APS Gazette vacancies dataset:

- `Science and Health` (Regimes 2a/2b/2b+): roughly 6,400–7,000 staff per snapshot
- `Monitoring and Audit` (Regime 2b+): roughly 2,400–2,900 staff per snapshot
- `Senior Executive` (Regime 2b+ in agency_jf)
- `No data` (Regime 2b+)

For longitudinal Science or Health analysis: Science and Health are merged across Regimes 2a/2b/2b+ (Jun 2021–Jun 2025) and cannot be separated for those periods; they are split back into separate families in Regime 3 (Dec 2025).

**"No data" (Jun 2024 onwards).** Employees whose job family is unclassified are counted in a "No data" column starting from the June 2024 release. (tens of thousands of staff, roughly 10–15% of the APS per snapshot; see the taxonomy table above). Prior releases excluded these employees from the job family tables entirely. This was verified by comparing the sum of all job family headcounts against the headline APS employment figure in the source Excel files: a gap of 22,000–27,000 employees exists in every pre-2024 release, and the "No data" count in June 2024 exactly closes it. The apparent headcount jump between December 2023 and June 2024 partly reflects visibility of this previously uncounted population, not purely real growth.

**Machinery-of-government splits.** The July 2022 MoG changes split several agencies: DAWE → DAFF + DCCEEW; DESE → Department of Education + DEWR. APSED assigns staff to successor agencies from July 2022 onwards; predecessor agency data is not redistributed. Agency-level headcount cannot be tracked continuously across the split date. See the [gazette README](https://github.com/gjosling/aps-gazette-public#interpreting-longitudinal-trends) for a broader discussion of MoG discontinuities including function transfers and portfolio reshuffles.

**Portfolio department rows are direct-employee-only.** In `apsed_agency_jf.csv` and `apsed_agency_headcount.csv`, portfolio department rows (`is_sub_agency=False`) record only the core department's own employees. Sub-agencies within the same portfolio are listed as separate rows. Summing portfolio department rows alone does not give the APS total; all rows (portfolio departments and sub-agencies alike) must be summed.

**Dot cells stored as null.** Some agency × job family cells in the source table contain "." rather than a number. These are stored as `null` in the output rather than zero to preserve the source distinction. "." most likely represents zero employees or a not-applicable combination, but the source files provide no documentation of what it means (the only footnote on the sheet is "Source: APSED"). The presence of null values means row sums across job families may not exactly match an agency's total headcount.

**Dec 2020 spelling variant.** December 2020 uses "Program" (American spelling) for two family names where June 2020 uses "Programme". Both spellings appear in Regime 1 output and are documented in the crosswalk.

## Linking to APS Gazette

This dataset is designed to pair with the [APS Gazette vacancies dataset](https://github.com/gjosling/aps-gazette-public). The gazette `agency_canonical` column joins directly to `agency_canonical` in `apsed_agency_jf.csv`; gazette `job_family` joins to `job_family_key` in APSED. The reliable join window starts from June 2024, when the APSED agency × job family table begins. The `agency_canonical` column in `apsed_agency_headcount.csv` uses the same lookup and joins the same way, which is useful for comparing gazette vacancy volumes against total agency headcount across the full time series from June 2020.

See the [gazette README](https://github.com/gjosling/aps-gazette-public#linking-to-apsed) for a practical join guide including a code example and caveats.

## Source data

The APSC publishes twice-yearly APSED releases at:
[https://www.apsc.gov.au/initiatives-and-programs/workforce-information/workforce-data/aps-employment-data-release](https://www.apsc.gov.au/initiatives-and-programs/workforce-information/workforce-data/aps-employment-data-release)

`data/releases.csv` catalogues all available releases with their snapshot dates, formats, and download URLs.

## Licence

Code: [MIT](LICENSE)

The underlying APSED data is published by the Australian Public Service Commission under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## Development

The code in this repository was written with the assistance of a large language model, working from my specifications. The pipeline design, parsing strategy, normalisation rules, and data quality decisions are my own. All code was reviewed, tested, and iterated by me.

## Contact

Gabrielle Josling — [mindyourowndata.org](https://mindyourowndata.org)
