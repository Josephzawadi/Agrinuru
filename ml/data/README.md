# Agricultural dataset inventory

Raw files are copied without editing into `raw/`. The source files in `C:\Users\HP\Downloads` were left untouched. ZIP members listed below were extracted individually; the ZIP archives themselves are not copied into the repository.

File sizes below are the copied, uncompressed files. Record counts exclude headers; workbook sheets are counted separately. No dataset source URL or licence statement was present in the inspected files or archives. Provenance claims are therefore limited to the supplied filenames.

## Crop recommendation

| Dataset | Original source / downloaded filename | Format / size | Records and columns | Potential use |
|---|---|---|---|---|
| Crop recommendation | `archive(2).zip` → `Crop_recommendation.csv` | CSV / 150,034 bytes (0.14 MiB) | 2,200 records; `N`, `P`, `K`, `temperature`, `humidity`, `ph`, `rainfall`, `label` | Initial crop-label classification experiment. The sample is balanced across 22 labels (100 rows each), with no blank fields or exact duplicate rows detected. |

**Limitations:** The archive contains no author, source URL, collection method, location, dates, or licence. The file alone does not establish that observations represent Kenyan farms, and its label balance does not prove real-world class prevalence. Verify units, feature provenance, and geographic representativeness before using results operationally.

## Crop yield and environmental context

All five files were extracted from `archive(3).zip`.

| Dataset | Downloaded filename | Format / size | Records and columns | Potential use |
|---|---|---|---|---|
| Crop yield observations | `yield.csv` | CSV / 4,042,934 bytes (3.85 MiB) | 56,717; `Domain Code`, `Domain`, `Area Code`, `Area`, `Element Code`, `Element`, `Item Code`, `Item`, `Year Code`, `Year`, `Unit`, `Value` | Historical country/area and crop yield baseline. Years observed: 1961–2016. |
| Combined yield and context table | `yield_df.csv` | CSV / 1,565,376 bytes (1.49 MiB) | 28,242; empty-name index column, `Area`, `Item`, `Year`, `hg/ha_yield`, `average_rain_fall_mm_per_year`, `pesticides_tonnes`, `avg_temp` | A ready-made exploratory yield-feature table, subject to repeated-key checks and provenance verification. |
| Rainfall | `rainfall.csv` | CSV / 136,712 bytes (0.13 MiB) | 6,727; ` Area` (leading space in header), `Year`, `average_rain_fall_mm_per_year` | Annual rainfall context; observed years 1985–2017. |
| Temperature | `temp.csv` | CSV / 1,421,414 bytes (1.36 MiB) | 71,311; `year`, `country`, `avg_temp` | Temperature context; observed years 1743–2013. |
| Pesticide use | `pesticides.csv` | CSV / 447,677 bytes (0.43 MiB) | 4,349; `Domain`, `Area`, `Element`, `Item`, `Year`, `Unit`, `Value` | Potential country/year feature for exploratory yield analysis; observed years 1990–2016. |

**Overlap and quality:** Every distinct `(Area, Item, Year, yield)` key in `yield_df.csv` is also present in `yield.csv` (13,130 distinct shared keys), so the combined file is not independent yield evidence. `yield_df.csv` contains 28,242 rows but only 13,130 distinct target keys; 3,837 target keys repeat, adding 15,112 repeated-key rows. Review repeated observations and their differing context features before splitting or training to prevent leakage. No blank fields were detected in `yield.csv`, `yield_df.csv`, or `pesticides.csv`; `rainfall.csv` has 774 blank rainfall values and `temp.csv` has 2,547 blank temperature values. `temp.csv` also has 6,958 exact duplicate rows. These files span broad international populations and their coverage periods do not fully align, so geography, year matching, units, and any merge strategy need review. The rainfall column header has a leading space.

**Limitations:** The ZIP has no documentation, source URLs, or licence. The `yield_df.csv` index-like first column is unnamed, and the relationship between its repeated target keys and its source merges is undocumented. The data is not a substitute for Kenyan farm-level harvest outcomes and seasonal/local weather. The temperature file is UTF-8; no encoding corruption was observed.

## Kenyan market prices

| Dataset | Original source / downloaded filename | Format / size | Records and columns | Potential use |
|---|---|---|---|---|
| Monthly wholesale commodity prices | Supplied workbook `Monthly wholesale commodity prices - Ministry of Agriculture 2012-2024sep.xlsx` | XLSX / 13,288,084 bytes (12.67 MiB) | Three sheets spanning 2012–2024: `Data` has 204,739 records and `year`, `month`, `county`, `market`, `Commodity`, `unit`, `kg`, `price`; `Markets Avg` has 44,575 records and `year`, `county`, `market`, `Commodity`, `unit`, `kg`, and month columns `jan`–`dec`; `County Avg` has 21,547 records and `year`, `county`, `Commodity`, `unit`, `kg`, and month columns `jan`–`dec`. | Primary candidate for Kenyan market-price forecasting, including commodity, county, market, unit, and month-level history. |

**Overlap and quality:** The workbook has `Data` and average sheets at market/county level. The average sheets are overlapping aggregate representations, not independent datasets; the workbook contains no formula/provenance documentation to establish exactly how they were derived. No exact duplicate complete records were detected within any sheet. The `Data` sheet has 37 blank `unit` values. The `Markets Avg` and `County Avg` sheets have blank month cells in every month (approximately 23,868–32,986 and 9,039–13,809 blanks per month, respectively) and 37 and 28 blank `unit` values. `Data.price` ranges from 0.01 to 9,131,111.111; the extreme upper value should be investigated alongside commodity, unit, and quantity before modeling. Confirm currency, price units, market identity consistency, and month/date coverage. The supplied filename identifies the Ministry of Agriculture, but the inspected workbook metadata does not establish the specific publisher, download URL, licence, or currency convention.

## Excluded archive

`new dataset soen 400 project.zip` contains `train.csv` (59,598 records) and `test.csv` (14,900 records), both with employee attributes and an `Attrition` outcome. The columns include employee ID, age, job role, income, satisfaction, work conditions, and attrition status. This is an employee-attrition dataset, not agricultural data, and was not copied.

## Use by AgriNuru module

- **Crop recommendation:** `Crop_recommendation.csv` is the strongest candidate for a first exploratory classifier. It needs documented provenance, feature units and Kenyan validation data before it can inform farmers.
- **Crop yield prediction:** `yield.csv` provides the broader historical yield target; `yield_df.csv` overlaps with it and includes climate/pesticide features. `rainfall.csv`, `temp.csv`, and `pesticides.csv` may offer context, but geographic and temporal coverage must be aligned. Kenyan farm-level harvest and season data is needed for locally useful validation.
- **Market price prediction:** The Ministry-named wholesale price workbook is the most directly relevant supplied dataset. First confirm source provenance, currency/units, missingness, deduplication, and whether the monthly sheets are aggregates of `Data`.
- **Agricultural production analysis:** AgriNuru already records farmer-owned crop and production information through its application. The downloaded datasets provide no farm activity, expense, input-usage, or actual harvest history at farm level; existing production records should remain authoritative and can only support analysis as valid, sufficient, authorized records accumulate.

## Source tracking

The original source filenames and archive members are recorded above. The source archives and workbook were found in `C:\Users\HP\Downloads`; no dataset-specific source link, publisher document, or licence was supplied or embedded in the inspected metadata. Please provide source URLs/licence evidence before redistributing these files beyond this repository.
