# Office Lunch

A single page showing **today's lunch menu** for a handful of nearby
restaurants, in the language you pick (DE / EN / FR — whichever the
restaurant publishes).

The site is a static HTML page hosted on GitHub Pages. A GitHub Action
runs each weekday morning, scrapes each restaurant's website, and
commits `data/menus.json`. The page reads that file on load.

## Restaurants covered

| # | Name              | Source                                              | Languages |
|---|-------------------|-----------------------------------------------------|-----------|
| 1 | Hortus            | https://hortus.ch/en/kitchen/                       | DE, EN    |
| 2 | Bio Bistro (Bachgraben) | https://biobistro.bsb.ch/standorte/bachgraben | DE (PDF)  |
| 3 | YAYE              | https://www.zfv.ch/de/essen-gehen/yaye              | DE, FR    |
| 4 | Belo Café Swiss TPH | https://www.zfv.ch/de/essen-gehen/belo-cafe-swiss-tph | DE, FR |
| 5 | Mister Wong (Allschwil) | https://www.misterwong.ch/standorte/allschwil/ | DE (PDF) |
| 6 | Van der Merwe     | https://vandermerwe.ch/gastronomie/                 | DE (PDF)  |

Where a restaurant only publishes in one language, the site shows that
language with a small note; no auto-translation is performed.

## Local development

Requires Python 3.11+.

```bash
cd scripts
python -m venv .venv
.venv\Scripts\activate            # PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scrape_menus.py            # writes ../data/menus.json
python scrape_menus.py --date 2026-09-21 --dry-run   # test a specific day
```

Then serve the site locally:

```bash
python -m http.server 8000        # from repo root
```

Open http://localhost:8000/. (Or `npx http-server . -p 8000` if you
prefer Node.)

## Deploying to GitHub Pages

1. Create a new GitHub repo (e.g. `office-lunch`) and push this folder:

   ```bash
   cd office-lunch
   git init && git add . && git commit -m "Initial commit"
   git branch -M main
   git remote add origin git@github.com:<you>/office-lunch.git
   git push -u origin main
   ```

2. In the repo settings → **Pages**, set **Source** = *Deploy from a
   branch*, branch = `main`, folder = `/` (root). The site will be at
   `https://<you>.github.io/office-lunch/`.
3. In **Settings** → **Actions** → **General** → **Workflow permissions**,
   pick **Read and write permissions** so the workflow can commit
   `data/menus.json` back.
4. Trigger the first scrape manually: **Actions** → **Scrape menus** →
   **Run workflow**. After that it runs on its own at 06:00 UTC on
   weekdays (≈ 07:00/08:00 Basel time depending on DST).
5. Optional: edit the `Source` link in `index.html` to point to your
   repo URL.

## Adding a restaurant

1. Add a module under `scripts/restaurants/` following the pattern of
   `hortus.py` — export `fetch(today, session) -> dict` returning the
   schema described in `scripts/scrape_menus.py`.
2. Register it in the `RESTAURANTS` list in `scripts/scrape_menus.py`.
3. Run `python scrape_menus.py` locally to test.
