from bs4 import BeautifulSoup
from scraper.web import WebScraper
from scraper.models import ScrapedDocument

class BitmexScraper(WebScraper):
    start_urls = ["https://blog.bitmex.com/"]
    def parse_page(self, soup: BeautifulSoup, url: str):
        article = soup.find('article') or soup.find('div', class_='post-content')
        if not article: return None
        h1 = soup.find('h1')
        title = h1.get_text().strip() if h1 else None
        if not title: return None
        body = article.get_text(separator='\n').strip()
        return ScrapedDocument(id=f"bitmex-{url.split('/')[-2] if url.endswith('/') else url.split('/')[-1]}", title=title, body=body, authors=["BitMEX Research"], domain=str(self.config.domain), url=url, created_at=None)
