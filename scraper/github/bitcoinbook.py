import os
import re
from loguru import logger
from datetime import datetime

from scraper.web import WebScraper
from scraper.models import ScrapedDocument



class BitcoinBookScraper(WebScraper):
    """
    Scraper for BitcoinBook.
    Fetches rendered HTML directly from GitHub.
    """
    
    DEFAULT_CHAPTERS = [
        "ch01_intro.adoc", "ch02_overview.adoc", "ch03_bitcoin-core.adoc",
        "ch04_keys.adoc", "ch05_wallets.adoc", "ch06_transactions.adoc",
        "ch07_authorization-authentication.adoc", "ch08_signatures.adoc",
        "ch09_fees.adoc", "ch10_network.adoc", "ch11_blockchain.adoc",
        "ch12_mining.adoc", "ch13_security.adoc", "ch14_applications.adoc"
    ]

    def get_chapter_links(self):
        api_url = 'https://api.github.com/repos/bitcoinbook/bitcoinbook/contents?ref=develop'
        try:
            resp = self.session.get(api_url, timeout=10)
            if resp.status_code == 200:
                links = []
                for item in resp.json():
                    name = item.get('name', '')
                    if name.startswith('ch') and (name.endswith('.adoc') or name.endswith('.asciidoc')):
                        links.append(item['html_url'])
                if links:
                    links.sort()
                    return links
        except Exception as e:
            logger.warning(f"Could not fetch chapter list from GitHub API: {e}")

        site = 'https://github.com/bitcoinbook/bitcoinbook/blob/develop'
        return [f"{site}/{ch}" for ch in self.DEFAULT_CHAPTERS]

    async def scrape(self):
        chapter_links = self.get_chapter_links()
        
        for url in chapter_links:
            try:
                soup = self.fetch(url)
                if not soup:
                    continue

                article = soup.find('article') or soup.find(class_='markdown-body') or soup.find(id='readme') or soup.find('main')
                if not article:
                    logger.error(f"Could not locate content container for {url}")
                    continue

                header = article.find(['h1', 'h2', 'h3'])
                title = header.get_text().strip() if header else os.path.basename(url)
                body = article.get_text().strip()
                
                chapter_number = ''.join(re.findall(r'\d+', url.split('/')[-1].split('_')[0]))
                doc_id = f"bitcoinbook-chapter-{chapter_number}"

                document_data = {
                    "id": doc_id,
                    "title": title,
                    "body": body,
                    "authors": ["Andreas Antonopoulos"],
                    "domain": str(self.config.domain),
                    "url": url,
                    "created_at": "2022-11-15", # date of most recent commit
                }
                
                document = ScrapedDocument(**document_data)
                await self.process_and_index_document(document)
                
            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
