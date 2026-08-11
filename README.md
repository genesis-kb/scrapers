# Bitcoin Search Scraper

A modular scraper framework that collects Bitcoin and Lightning Network educational content from GitHub repositories and websites, and outputs structured documents in JSON and Markdown format.

## Architecture

```
scraper/
├── run_scraper.py          # Entry point
├── sources.yaml            # All sources defined here
│
└── scraper/
    ├── base.py             # BaseScraper: abstract interface + shared utilities
    ├── github.py           # GithubScraper: git clone + file parsing base
    ├── web.py              # WebScraper: HTTP fetch + crawling base
    ├── models.py           # Pydantic data models (ScrapedDocument, SourceConfig etc.)
    ├── config.py           # Settings & sources.yaml loader
    │
    ├── github/             # One file per GitHub source
    │   ├── bitcoinops.py
    │   ├── bitcointranscripts.py
    │   ├── bitcoinbook.py
    │   └── default_github.py   # Reused by BIPs, BOLTs, BLIPs, etc.
    │
    ├── web/                # One file per website source
    │   ├── bitcointalk.py
    │   ├── stackexchange.py
    │   ├── bitcoindevguide.py
    │   ├── bitcoinwiki.py
    │   ├── bitmex.py
    │   ├── blockstream.py
    │   ├── learnmeabitcoin.py
    │   ├── oleganza.py
    │   ├── river.py
    │   └── rusty.py
    │
    └── outputs/
        └── text_output.py  # Saves scraped docs as JSON + Markdown files
```

## How it works

1. `sources.yaml` lists all sources under `github:` or `web:` with a `name`, `url`, and optional `script` field.
2. `run_scraper.py` reads `sources.yaml` and dynamically loads the matching script from `scraper/github/<name>.py` or `scraper/web/<name>.py`.
3. Each script contains a single class that inherits from `GithubScraper` or `WebScraper` and implements `scrape()` or `parse_page()`.
4. Scraped documents are saved to `outputs/<source_name>/<doc_id>/` as `data.json` and `content.md`.

## Adding a New Source

1. **Create the scraping script:**
   - For a website: create `scraper/web/mynewsite.py` with a class extending `WebScraper`
   - For a GitHub repo: create `scraper/github/myrepo.py` with a class extending `GithubScraper`

2. **Add it to `sources.yaml`:**
   ```yaml
   web:
     - name: MyNewSite
       domain: https://mynewsite.com
       url: https://mynewsite.com
   ```
   If multiple sources share the same parsing logic, use the `script` field:
   ```yaml
   github:
     - name: MyRepo
       script: default_github
       domain: https://github.com/user/repo
       url: https://github.com/user/repo.git
   ```

That's it! No registration, no imports to update anywhere.

## Setup

```bash
# Install dependencies
pip install -r requirements.txt
```

## Running

```bash
# Run a single scraper
python run_scraper.py BitcoinOps

# Run all scrapers sequentially
python run_scraper.py
```

Output is written to `outputs/<SourceName>/`.
Logs are written to `logs/scraper.log`.

## Sources

### GitHub
| Name | Repository |
|---|---|
| BIPs | https://github.com/bitcoin/bips |
| BOLTs | https://github.com/lightning/bolts |
| BLIPs | https://github.com/lightning/blips |
| BitcoinOps | https://github.com/bitcoinops/bitcoinops.github.io |
| BitcoinTranscripts | https://github.com/bitcointranscripts/bitcointranscripts |
| BitcoinBook | https://github.com/bitcoinbook/bitcoinbook |
| PR-Review-Club | https://github.com/bitcoin-core-review-club/website |
| BtcPhilosophy | https://github.com/bitcoin-dev-philosophy/btcphilosophy |
| GrokkingBtc | https://github.com/kallerosenbaum/grokkingbitcoin |
| LnDocs | https://github.com/t-bast/lightning-docs |
| ProgrammingBtc | https://github.com/jimmysong/programmingbitcoin |

### Web
| Name | URL |
|---|---|
| BitcoinTalk | https://bitcointalk.org |
| StackExchange | https://bitcoin.stackexchange.com |
| BitcoinDevGuide | https://developer.bitcoin.org |
| BitcoinWiki | https://en.bitcoin.it |
| Bitmex | https://blog.bitmex.com |
| Blockstream | https://blog.blockstream.com |
| LearnMeABitcoin | https://learnmeabitcoin.com |
| Oleganza | https://blog.oleganza.com |
| River | https://river.com |
| Rusty | https://rusty.ozlabs.org |
