import re
from bs4 import BeautifulSoup
from scraper.web import WebScraper
from scraper.models import ScrapedDocument

class RiverScraper(WebScraper):
    start_urls = ["https://river.com"]
    allow_regex = r"terms"
    
    def parse_page(self, soup: BeautifulSoup, url: str):
        keywords = ["taproot", "script", "wallet", "watchtower", "sign", "chain", "contract", "proof", "fork", "vByte", "bitcoin", "lightning", "bip", "payment", "block", "transaction"]
        clearn = soup.find('div', class_='c-learn__content')
        if not clearn:
            return None
        paragraphs = clearn.find('div', class_='c-article').find_all('p')
        body = "".join([p.get_text() for p in paragraphs])
        h1 = clearn.find('h1')
        title = h1.get_text().strip() if h1 else ""
        pattern = re.compile("|".join(keywords), re.IGNORECASE)
        if not title or not re.search(pattern, title):
            return None
        return ScrapedDocument(id=f"river-{url.split('/')[-2]}", title=title, body=body, authors=["river"], domain=str(self.config.domain), url=url, created_at=None)
