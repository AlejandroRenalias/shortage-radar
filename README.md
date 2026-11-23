# Shortage Radar

[Open the live site](https://alejandrorenalias.github.io/shortage-radar/) · Saatavuustutka in Finnish

Shortage Radar is a searchable view and archive of reported medicine shortages in Finland. Fimea's open file describes current shortages and those expected within two weeks, but Fimea does not provide a public history of that file. This project saves captures to make changes over time visible. Daily archive since 21 Nov 2026, with earlier captures from the Internet Archive.

![Home page](docs/home-en.png)

**This is not medical advice.** A listing does not establish whether a medicine is available at a particular pharmacy. Ask a pharmacist or doctor about your medicines.

## How it works

A scheduled job downloads and validates Fimea's shortage file and saves a dated snapshot when its contents change. The site joins package records to the current basic register by VNR and builds a static site. It can be searched by medicine, strength, substance, ATC, company or VNR; it includes veterinary products. Earlier copies from the Internet Archive extend the timeline. The download links on the site provide the current dataset.

The archive checks Fimea four times daily at 04:35, 10:05, 15:35 and 21:05 UTC to reduce the chance of a missed day. A separate Pages build runs daily at 04:55 UTC as a safety net. When a scheduled or manual workflow starts more than 30 hours after the last successful archive check, it raises a data-pipeline issue until an archive check succeeds. If GitHub starts no workflows at all, that alert will be late; the site itself shows a stale-data warning after more than three days.

The list page loads `current.json`. The other pages load small files built with it, so no page downloads the whole archive: `summary.json` (counts, impact counts, longest and newest packages) for home, trends and about, `p/NN.json` (every notice of the packages whose VNR ends in NN, and the other packages in the substitution groups of its current packages) for the medicine page, `history.json` for the trends page and `week.json` for the weekly facts. The downloadable `data.json` retains the complete event history. `week.json` holds the counts for the "This week" summary, and `feed.xml` (English) and `feed-fi.xml` (Finnish) are Atom feeds of the shortages that appeared or left the list in the last 14 days and of the substitution groups that newly have no interchangeable product on the market, with at most 200 entries.

### Impact: can the pharmacy give a substitute?

For each current shortage, the build counts the other packages in the same substitution group (vaihtokelpoisuusryhmä) whose register entries say they are on the market and not in shortage, excluding packages listed in the current shortage file. Only Fimea's group code is compared. The register writes the strength and form of one group in different ways ("20 mg/ml" and "20 mg/g", film-coated tablets and capsules), and an earlier version that also compared that text found no alternative for 30 packages that had one. This is not a pharmacy stock check, and a group does not establish that a particular package is suitable.

Each current shortage gets one impact level (`impact` in `current.json`, `data.json` and the CSV; counts in `summary.json` under `impact`), set in `scripts/triage.py`:

| Level | Meaning |
| --- | --- |
| `substitute` | Substitute usually available: the group has at least one other package on the market and not short. |
| `critical` | No interchangeable product on the market: the package has a group, but no such other package. |
| `nogroup` | No substitution group: the pharmacy cannot change the medicine on its own. |
| `vet` | Veterinary medicine (ATC starting with Q). Substitution groups are for human medicines, so these are counted apart from the human headline. |

On 22 Nov 2026 the split was 531 / 60 / 119 human packages and 39 veterinary packages, 749 in all. The home page shows the three human levels, each linking to the list filtered by it (`shortages.html?impact=critical`). With `impact=critical` the list shows one row per active substance and form, which opens to its packages. The medicine page names the other packages of the group with strength, pack and company, so the label can be checked.

The CSV column `other packages on market` gives the count, or is empty when no substitution group is recorded; `substitution group` gives Fimea's group code and `impact` the level. The CSV uses UTF-8 with a BOM and contains package, medicine, company, date and veterinary fields.

"Newly critical" is the capture in which a substitution group lost its last available alternative. The register describes only today, so the history is rebuilt from the saved captures with today's group membership and the market entry and exit dates the register gives for each package. A group changes state only when the new state holds in two captures in a row, each at most 14 days apart, and no change is dated across a longer gap. On the archive up to 22 Nov 2026 this finds 20 events since 15 Sep 2026; each one is explained by its last alternative appearing on the shortage list or, once, leaving the market. Group changes and packages withdrawn from the register cannot be seen, so older events are less certain. To keep a record that does not depend on a later register, the archive job also downloads the register and saves the day's impact counts in `data/triage-counts.json` (`scripts/record_triage.py`); a failure there does not stop the archive. The JSON records the UTC build time as `generated_at` and the most recent successful archive check date as `last_checked`, which can be empty. When that date is unavailable, the site labels the build-time fallback and does not imply that the source was checked at build time.

The history shows saved captures, not daily observations. Capture gaps can be long: the first is from 18 November 2024, followed by a gap until September 2026. The chart does not interpolate across long gaps. An event is identified by VNR, reported start, notification date and company; changes to those fields can appear as a removal and a new event.

The comparison with estimated end dates uses only events with sufficiently close captures at both ends. It describes when a record was last seen or removed from the list, not when supply actually returned. Estimates may already have changed before the first available capture, and ongoing shortages are excluded from the comparison.

## Pages and structure

The site is static and has five pages, all under `/shortage-radar/` on GitHub Pages. Text is in Finnish and English; the language follows the browser and the choice is remembered on the device.

| Page | File | What it does |
| --- | --- | --- |
| Home (Etusivu) | `index.html` | One sentence on today's situation, the impact triage (substitute usually available, no interchangeable product on the market, no substitution group), a search, the newest packages, three facts from this week and three paths. The old `?q=` address is sent to the list. |
| Shortages (Saatavuushäiriöt) | `shortages.html` | The full list with search, filters (impact, status, medicine group, form, company) and sort. The search and filters are in the address, for example `shortages.html?q=burana&status=now` or `shortages.html?impact=critical`, which groups the packages by medicine. |
| Medicine (Lääke) | `medicine.html?vnr=<VNR>` | One package: label, whether the pharmacy can give a substitute and the other packages of its group, status, timeline, what to do, details and a link to share. Feed entries link here. |
| Trends (Tilastot) | `trends.html` | Count over time, this week, groups, companies, longest running, groups newly without an interchangeable product, the recorded impact counts, the delay result and a citation. |
| About (Tietoa) | `about.html` | What a shortage is, what to do, substitution groups, what the impact label means and its limits, how the data works, limits, downloads, privacy and licence. |

The pages are built by `scripts/pages.py`, which writes the shared header and footer once into every page, and `scripts/build.py` runs it with the data. The generated pages are not committed. Browser code is in `site/`: `i18n.js` holds all text, `lib.js` the shared code (search, dates, the package card, filters, the timeline model, page set-up) and one script for each page. Form pictograms are drawn in `lib.js`. The font is Atkinson Hyperlegible Next, hosted in `site/fonts`; its digits are replaced by Public Sans digits (a 3 KB subset under the same family name) because Atkinson's zero is slashed and reads as a letter in dates and doses.

## Critical medicines in Finland

`critical.html` (nav label "EU list") shows which packages on Fimea's shortage list are on the EU [Union list of critical medicines](https://www.ema.europa.eu/en/human-regulatory-overview/post-authorisation/medicine-shortages-and-availability-issues/union-list-critical-medicines), pinned at version 2.1 (EMA/229885/2026, 4 Nov 2026) in `data/critical/eu-list.csv` with the source row of each entry. A package is an `exact` match when its ATC level 5 code is on the list and one of its routes (Fimea `Antoreitti`) fits a list route, `route-mismatch` when the code matches but the route does not (or Fimea gives no route: "route unclear"), and `unmatched` when the VNR is not in the register. Fimea's `EUKriittinenValmiste` flag is only a cross-check, shown in the note. The route table is `data/critical/routes.json`; there are no keyword rules. Facts only: no advice, score, forecast or alternatives.

`scripts/build.py` writes the match page, `critical-methods.html` (sources, licences, the rule, four hand-checked rows, limits), one page per code (`critical-<ATC>.html`: list row, Fimea notices, what the archive shows, with "last seen" for notices that left), the downloads `critical.csv` and `critical.json`, and the alert feeds `critical-feed.xml` (RSS) and `critical-feed.json` of new exact-match shortages of the last 30 days. The daily Pages build, which also runs after each archive check, produces the feeds. The register is now read from `Perusrekisteri2026.xml`, which carries the route and flag fields; the existing fields are unchanged. To update the list, run `python scripts/fetch_critical.py list` (it refuses a version other than the pinned one unless `--version` is given; it sends a User-Agent, pauses and caches); `python scripts/fetch_critical.py forms` refreshes the dosage form names. The EMA licence is its copyright notice (reuse with EMA acknowledged), not CC BY; Fimea data is CC BY 4.0.

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
