# Shortage Radar

A daily archive and static dashboard of reported medicine shortages in Finland. Fimea's open shortage file contains current shortages and those expected within two weeks; it is not a public historical archive. This project captures changes so that the list can be studied over time.

![Dashboard showing 751 reported shortage records on 21 November 2026](docs/dashboard.png)

**Not medical advice. Ask a pharmacist or doctor about your medicines.** A listing does not establish availability at a particular pharmacy or recommend a substitute.

## Dashboard and data

The dashboard searches names, substances, ATC codes, companies and package VNRs. It counts records by ATC group and company and charts captures. History begins on **18 November 2024**, but only with a few captures: there is one capture from 2024, then nothing until **15 September 2026**. No trend should be inferred for the gap. The delays section compares estimates to removal from the list, not a confirmed return to supply; see [Imported history](#imported-history).

The project's snapshot from 21 November 2026 has 751 rows, 743 matched product names and 8 unmatched VNRs: `422093`, `433660`, `522103`, `531797`, `541749`, `572154`, `583857`, `584836`. Names are joined to the current register and may not describe historical products as they were at the time. The basic register was chosen because Fimea publishes a direct, nightly updated XML download with package, product and substance references; no account or catalogue lookup is needed. It is large (about 200 MB), but is streamed during processing and not committed.

The dataset includes `substitution_group` from the current basic register, joined to packages through their product reference. These product-level groups are not recommendations: Fimea states that the group alone does not establish package-size interchangeability. Groups may be missing when a VNR is absent from the register, and the current register may not describe historical products as they were at the time. The dashboard does not suggest alternatives.

## Imported history

Fimea does not publish past versions of the shortage file. Earlier copies were taken from the [Internet Archive](https://web.archive.org/), which holds captures of Fimea's Finnish-named copy of the file (`Saatavuushairiot.txt`, same data as `Shortages.txt`). `python scripts/import_history.py` lists the captures with HTTP status 200, downloads each one sequentially with a delay and retries, and writes it to `data/snapshots/imported/<date>.txt`.

- The date is the capture time converted to Helsinki time. Dates already covered by a snapshot saved by this project, or by an earlier capture, are skipped, so this project's own snapshots are never replaced.
- The Finnish header (`VNR`, `Voimassa`, `SaatavuushairioAlkupaiva`, ...) is replaced by the current header (`NordicArticleNumber`, `Valid`, `UnavailableFrom`, ...). Rows are kept byte for byte.
- A capture must match the archive's content digest and pass the checks used for daily snapshots: valid header and rows, at least 100 rows, and no drop to less than half the previous row count. Failed captures are skipped and logged.
- [`data/snapshots/imported/manifest.json`](data/snapshots/imported/manifest.json) records every capture considered: archive timestamp and URL, content digest, date, row count and SHA-256, or the reason it was skipped. Re-running the script downloads nothing that is already stored.

Result: 23 captures imported (2024-11-18, then 2026-09-15 to 2026-11-17, every few days) and 3 skipped: the 2025 captures of `Shortages.txt` and `Restnoteringar.txt` return HTTP 404 from the archive, and the capture of 2026-11-20 23:44 UTC falls on 2026-11-21 in Helsinki, which this project's own snapshot covers.

**What the timeline can show.** Captures are days apart, so a start or an end is a window, never a date. For each event the data keeps `first_seen_after` and `first_seen` (it began in between) and `last_seen` and `removed_on` (it left the list in between). Records present in the first capture are marked "already listed at first capture": their real start is earlier. Records first seen on 2026-09-15 began somewhere in the 666-day gap. The history chart does not draw a line across gaps longer than 14 days and does not interpolate days.

**Delay finding.** The dashboard compares each event's first estimated end with the window in which it left the list. Only events whose first sighting is within 14 days of the previous capture and whose removal window is within 14 days are used; events listed at the first capture, events first seen after a long gap and events whose package is still listed under a changed record (for example a revised start date) are excluded. An event lasted past the estimate if it was still listed after the estimated end date, was gone by it if it was removed on or before that date, and is undetermined if the end date falls inside the removal window. The share that lasted past is therefore given as a range, and the median overrun for events that lasted past it as a lower and an upper bound. Shares and medians are shown only for samples of at least 30 events; smaller samples show the sample size only. Limits: estimates may already have been revised before the first capture that lists them, the window of about two weeks is wide next to typical delays, and removal from the list is not a confirmed end of the shortage. Counts for the current build are shown on the dashboard.

**RSS feed.** Archived copies of Fimea's [shortage RSS feed](https://fimea.fi/c/laakehaut_ja_luettelot/saatavuushairio-uusi/rss) (4 usable captures: 2021-01-27, 2022-03-02, 2022-07-09, 2026-08-08; 2 skipped for a digest mismatch) list items with name, ATC, pack size, start and end dates, but no VNR. They can only show how many items were listed on those dates (summaries in [`rss-counts.json`](data/snapshots/imported/rss-counts.json)). They cannot be linked to packages, give no removal dates and are not comparable to package counts, so they are kept out of the timeline and delay calculations.

## How it works

The scheduled GitHub Action downloads and validates the Fimea file, saving a dated file only if its bytes changed. It rejects files with fewer than 100 rows or less than half the previous snapshot's row count. A run fails on an invalid file, network failure, or conflicting capture on the same date. Changed snapshots trigger the Pages workflow, which downloads the current basic register and builds `site/data.json` as a deployment artifact; the generated data is not committed. A daily Pages build refreshes the register even when the shortage file has not changed, and pushes to main also build and deploy Pages. Enable GitHub Pages with **GitHub Actions** as the source after the repository becomes public. GitHub Actions must have permission to write repository contents, and scheduled workflows and Pages depend on repository settings and plan.

An event is identified by VNR, reported start date, notification date and company. Changes to these identifying fields can appear as a removal and a new event. The output records first and last seen dates, initial estimated end, changes in that estimate, and the first saved snapshot without the record. A missing record is an **observed removal**, not a medically confirmed real end. Since identical downloads are not saved, last seen is the last *saved* snapshot, not necessarily the last successful daily check; a removal may have occurred anywhere after that snapshot and on or before the next saved one. Gaps and failed runs widen the uncertainty. The chart shows saved snapshots rather than interpolating missing days. Fimea's feed excludes products without VNRs and some other shortages; consult Fimea for the full limitations.

## Run locally

Python 3.12 is recommended. On Windows, install `tzdata` for the Helsinki time zone. `pytest` is needed for tests; the processing code otherwise uses the standard library.

```sh
python -m pip install pytest tzdata
python scripts/archive.py
python scripts/import_history.py
python scripts/fetch_register.py
python scripts/build.py
python -m pytest -q
python -m http.server 8000 --directory site
```

Open `http://localhost:8000/`. The local HTTP server is only for preview: the site itself is static. The archive command downloads current public Fimea data and writes this repository's data files.

## Attribution and licence

Data is provided by the **Finnish Medicines Agency Fimea**, under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Earlier captures of the shortage file and RSS feed were retrieved from the [Internet Archive](https://web.archive.org/). Fimea's [open data page](https://fimea.fi/en/about_us/open-data) describes the datasets and licence. This project transforms and joins the source data, derives events and counts, and displays a subset; it is not endorsed by Fimea. Source modification timestamps below are the HTTP `Last-Modified` timestamps, not necessarily the publisher's release time. Latest observed timestamps for the first build:

| Dataset | Source | Source last modified (UTC) | Changes |
| --- | --- | --- | --- |
| Supply shortages | [Shortages.txt](https://data.pilvi.fimea.fi/avoin-data/Shortages.txt) | 2026-11-20 23:20:01 | Archived, parsed, joined and aggregated |
| Basic register of medicinal products | [XML and documentation](https://fimea.fi/en/databases_and_registers/basic-register-xml) | 2026-11-21 00:30:41 | Selected package, product, substitution group and substance fields joined by VNR |

The most recent snapshot's shortage timestamp is in [`data/source/metadata.json`](data/source/metadata.json); the basic-register timestamp is captured during each build. The dashboard displays both timestamps. Source release times beyond these HTTP timestamps were not available from the files.
