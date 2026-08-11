from bs4 import BeautifulSoup
from scraper.web import WebScraper
from scraper.models import ScrapedDocument

class BlockstreamScraper(WebScraper):
    start_urls = ["https://blockstream.com/blog/"]
    allow_regex = r"/blog/"
    def parse_page(self, soup: BeautifulSoup, url: str):
        article = soup.find('article') or soup.find('div', class_='post-content')
        if not article: return None
        h1 = soup.find('h1')
        title = h1.get_text().strip() if h1 else None
        if not title: return None
        body = article.get_text(separator='\n').strip()
        return ScrapedDocument(id=f"blockstream-{url.split('/')[-2] if url.endswith('/') else url.split('/')[-1]}", title=title, body=body, authors=["Blockstream"], domain=str(self.config.domain), url=url, created_at=None)
