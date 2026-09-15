# Stefan Henkler research website

Static research website for GitHub Pages.

## Publication workflow

`data/henkler_all.bib` is the single bibliographic source. `scripts/build_publications.py` generates `publications/index.html` and stable anchors of the form `#pub-BIBTEX_KEY`. The Research page links only to these internal anchors.

On GitHub, `.github/workflows/pages.yml` runs the generator and deploys the resulting static site. No client-side JavaScript or bibliography service is required. To update publications, edit or replace `data/henkler_all.bib` and push to `main`.

For local preview:

```sh
python scripts/build_publications.py
python -m http.server 8000
```
