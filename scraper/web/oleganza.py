from bs4 import BeautifulSoup
from scraper.web import WebScraper
from scraper.models import ScrapedDocument

class OleganzaScraper(WebScraper):
    start_urls = ["https://blog.oleganza.com/"]
    def parse_page(self, soup: BeautifulSoup, url: str):
        if "/post/" not in url: return None
        article = soup.find('article') or soup.find('div', class_='post')
        if not article: return None
        h1 = article.find('h1') or article.find('h2')
        title = h1.get_text().strip() if h1 else "Untitled"
        body = article.get_text(separator='\n').strip()
        return ScrapedDocument(id=f"oleganza-{url.split('/')[-1]}", title=title, body=body, authors=["Oleg Andreev"], domain=str(self.config.domain), url=url, created_at=None)
