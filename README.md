# Shortage Radar

[Open the live site](https://alejandrorenalias.github.io/shortage-radar/) 

Shortage Radar is a searchable view and archive of reported medicine shortages in Finland. Fimea's open file describes current shortages and those expected within two weeks, but Fimea does not provide a public history of that file. This project saves captures to make changes over time visible. Daily archive since 21 Nov 2026, with earlier captures from the Internet Archive.

**This is not medical advice.** A listing does not establish whether a medicine is available at a particular pharmacy. Ask a pharmacist or doctor about your medicines.

## Run and test

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

## Data sources

- [Fimea open data](https://fimea.fi/en/about_us/open-data): the shortage file (`Shortages.txt`).
- [Fimea basic register of medicinal products](https://fimea.fi/en/databases_and_registers/basic-register-xml): joined to the shortage file by VNR.
- [Internet Archive](https://web.archive.org/): earlier captures of the shortage file and RSS feed.
- [EU Union list of critical medicines](https://www.ema.europa.eu/en/human-regulatory-overview/post-authorisation/medicine-shortages-and-availability-issues/union-list-critical-medicines): pinned copy in `data/critical/eu-list.csv`.

The project selects, joins and transforms the data; it is not endorsed by Fimea. Register names and details are current at build time and may not describe historical products as they were then. Some packages may not match the register. Fimea's file does not include all shortages, including products without VNRs. Source times on the site are file modification times, not necessarily publication times. A missing record is an observed removal, not proof that a shortage ended or that a product is available. Imported captures and omissions: [`data/snapshots/imported/manifest.json`](data/snapshots/imported/manifest.json).

## More detail

How the archive, impact levels, pages and EU list matching work: [`docs/internals.md`](docs/internals.md).

## Licence and citation

Code is licensed under the [MIT License](LICENSE). Fimea data is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Fonts are under the SIL Open Font License; see [`site/fonts`](site/fonts/).

Suggested citation: Alejandro Renalias, *Shortage Radar*, https://alejandrorenalias.github.io/shortage-radar/ (data dated [data date], accessed [date]); data from the Finnish Medicines Agency Fimea, CC BY 4.0, selected, joined and transformed; earlier captures from the Internet Archive.
