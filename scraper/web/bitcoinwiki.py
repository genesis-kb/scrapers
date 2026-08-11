from bs4 import BeautifulSoup
from scraper.web import WebScraper
from scraper.models import ScrapedDocument

class BitcoinWikiScraper(WebScraper):
    start_urls = ["https://en.bitcoin.it/wiki/Main_Page"]
    allow_regex = r"/wiki/"
    
    def parse_page(self, soup: BeautifulSoup, url: str):
        if ":" in url.split("/wiki/")[-1]: return None
        h1 = soup.find('h1', id='firstHeading')
        title = h1.get_text().strip() if h1 else None
        if not title: return None
        content = soup.find('div', id='mw-content-text')
        if not content: return None
        body = content.get_text(separator='\n').strip()
        return ScrapedDocument(id=f"bitcoinwiki-{url.split('/')[-1]}", title=title, body=body, authors=["Bitcoin Wiki Contributors"], domain=str(self.config.domain), url=url, created_at=None)
