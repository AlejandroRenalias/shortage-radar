# Shortage Radar

[Open the live site](https://alejandrorenalias.github.io/shortage-radar/) · Saatavuustutka in Finnish

Shortage Radar is a searchable view and archive of reported medicine shortages in Finland. Fimea's open file describes current shortages and those expected within two weeks, but Fimea does not provide a public history of that file. This project saves captures to make changes over time visible. Daily archive since 21 Nov 2026, with earlier captures from the Internet Archive.

![Home page](docs/home-en.png)

![Shortage list with filters](docs/shortages-en.png)

![One medicine package with its timeline](docs/medicine-en.png)

![Trends](docs/trends-en.png)

On a phone, in Finnish:

![Home page on a phone, in Finnish](docs/home-fi-phone.png) ![Medicine page on a phone, in Finnish](docs/medicine-fi-phone.png)

**This is not medical advice.** A listing does not establish whether a medicine is available at a particular pharmacy. Ask a pharmacist or doctor about your medicines.

## How it works

A scheduled job downloads and validates Fimea's shortage file and saves a dated snapshot when its contents change. The site joins package records to the current basic register by VNR and builds a static site. It can be searched by medicine, strength, substance, ATC, company or VNR; it includes veterinary products. Earlier copies from the Internet Archive extend the timeline. The download links on the site provide the current dataset.

The archive checks Fimea four times daily at 04:35, 10:05, 15:35 and 21:05 UTC to reduce the chance of a missed day. A separate Pages build runs daily at 04:55 UTC as a safety net. When a scheduled or manual workflow starts more than 30 hours after the last successful archive check, it raises a data-pipeline issue until an archive check succeeds. If GitHub starts no workflows at all, that alert will be late; the site itself shows a stale-data warning after more than three days.

The list page loads `current.json`. The other pages load small files built with it, so no page downloads the whole archive: `summary.json` (counts, longest and newest packages) for home, trends and about, `p/NN.json` (every notice of the packages whose VNR ends in NN) for the medicine page, `history.json` for the trends chart and `week.json` for the weekly facts. The downloadable `data.json` retains the complete event history. `week.json` holds the counts for the "This week" summary, and `feed.xml` (English) and `feed-fi.xml` (Finnish) are Atom feeds of the shortages that appeared or left the list in the last 14 days, with at most 200 entries.

The current dataset counts other packages in the same substitution group, strength and pharmaceutical form whose register entries say they are on the market and not in shortage, excluding packages listed in the current shortage file. This is not a pharmacy stock check, and a group does not establish that a particular package is suitable.

The CSV column `other packages on market` gives that count, or is empty when no substitution group is recorded. The CSV uses UTF-8 with a BOM and contains package, medicine, company, date and veterinary fields. The JSON records the UTC build time as `generated_at` and the most recent successful archive check date as `last_checked`, which can be empty. When that date is unavailable, the site labels the build-time fallback and does not imply that the source was checked at build time.

The history shows saved captures, not daily observations. Capture gaps can be long: the first is from 18 November 2024, followed by a gap until September 2026. The chart does not interpolate across long gaps. An event is identified by VNR, reported start, notification date and company; changes to those fields can appear as a removal and a new event.

The comparison with estimated end dates uses only events with sufficiently close captures at both ends. It describes when a record was last seen or removed from the list, not when supply actually returned. Estimates may already have changed before the first available capture, and ongoing shortages are excluded from the comparison.

## Pages and structure

The site is static and has five pages, all under `/shortage-radar/` on GitHub Pages. Text is in Finnish and English; the language follows the browser and the choice is remembered on the device.

| Page | File | What it does |
| --- | --- | --- |
| Home (Etusivu) | `index.html` | One sentence on today's situation, a search, three facts from this week and three paths. The old `?q=` address is sent to the list. |
| Shortages (Saatavuushäiriöt) | `shortages.html` | The full list with search, filters (status, medicine group, form, company) and sort. The search and filters are in the address, for example `shortages.html?q=burana&status=now`. |
| Medicine (Lääke) | `medicine.html?vnr=<VNR>` | One package: label, status, timeline, what to do, details and a link to share. Feed entries link here. |
| Trends (Tilastot) | `trends.html` | Count over time, this week, groups, companies, longest running, the delay result and a citation. |
| About (Tietoa) | `about.html` | What a shortage is, what to do, substitution groups, how the data works, limits, downloads, privacy and licence. |

The pages are built by `scripts/pages.py`, which writes the shared header and footer once into every page, and `scripts/build.py` runs it with the data. The generated pages are not committed. Browser code is in `site/`: `i18n.js` holds all text, `lib.js` the shared code (search, dates, the package card, filters, the timeline model, page set-up) and one script for each page. Form pictograms are drawn in `lib.js`. The font is Atkinson Hyperlegible Next, hosted in `site/fonts`; its digits are replaced by Public Sans digits (a 3 KB subset under the same family name) because Atkinson's zero is slashed and reads as a letter in dates and doses.

## Sources and limits

The source data is from the [Finnish Medicines Agency Fimea](https://fimea.fi/en/about_us/open-data), including its shortage file and [basic register of medicinal products](https://fimea.fi/en/databases_and_registers/basic-register-xml). Earlier captures of the shortage file and RSS feed were retrieved from the [Internet Archive](https://web.archive.org/). The project selects, joins and transforms the data; it is not endorsed by Fimea. Register names and details are current at build time and may not describe historical products as they were then. Some packages may not match the register. Fimea's file does not include all shortages, including products without VNRs.

Source times on the site are file modification times, not necessarily publication times. A missing record is an observed removal, not proof that a shortage ended or that a product is available. See [`data/snapshots/imported/manifest.json`](data/snapshots/imported/manifest.json) for the imported captures and omissions.

## Run locally

Python 3.12 is recommended; Windows needs `tzdata` for the Helsinki time zone. The register download is large and the archive commands write local data files.

```sh
python -m pip install pytest tzdata
python scripts/archive.py
python scripts/import_history.py
python scripts/fetch_register.py
python scripts/build.py
python -m pytest -q
node --test tests/test_dashboard.cjs
python -m http.server 8000 --directory site
```

Open `http://localhost:8000/` to preview the static site.

## Licence and citation

Code is licensed under the [MIT License](LICENSE). Fimea data is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Atkinson Hyperlegible Next and the Public Sans digits are locally hosted under the SIL Open Font License; the licence texts are in [`site/fonts`](site/fonts/).

Suggested citation: Alejandro Renalias, *Shortage Radar*, https://alejandrorenalias.github.io/shortage-radar/ (data dated [data date], accessed [date]); data from the Finnish Medicines Agency Fimea, CC BY 4.0, selected, joined and transformed; earlier captures from the Internet Archive.
