from bs4 import BeautifulSoup
from scraper.web import WebScraper
from scraper.models import ScrapedDocument

class LearnMeABitcoinScraper(WebScraper):
    start_urls = ["https://learnmeabitcoin.com/"]
    def parse_page(self, soup: BeautifulSoup, url: str):
        h1 = soup.find('h1')
        title = h1.get_text().strip() if h1 else None
        if not title: return None
        content = soup.find('main') or soup.find('article')
        if not content: return None
        body = content.get_text(separator='\n').strip()
        return ScrapedDocument(id=f"learnmeabitcoin-{url.split('/')[-2] if url.endswith('/') else url.split('/')[-1]}", title=title, body=body, authors=["Greg Walker"], domain=str(self.config.domain), url=url, created_at=None)
