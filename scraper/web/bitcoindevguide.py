from bs4 import BeautifulSoup
from scraper.web import WebScraper
from scraper.models import ScrapedDocument

class BitcoinDevGuideScraper(WebScraper):
    start_urls = ["https://developer.bitcoin.org/devguide/", "https://developer.bitcoin.org/reference/", "https://developer.bitcoin.org/examples/"]
    allow_regex = r"(/devguide/|/reference/|/examples/)"
    
    def parse_page(self, soup: BeautifulSoup, url: str):
        h1 = soup.find('h1')
        if not h1:
            section = soup.find('div', class_='section')
            if section:
                h1 = section.find('h1')
        title = h1.get_text().strip() if h1 else None
        if not title:
            return None
        content = soup.find('div', class_='content-left') or soup.find('div', role='main') or soup.find('main')
        if not content:
            return None
        paragraphs = content.find_all('p')
        body = "\n".join([p.get_text() for p in paragraphs])
        if len(body.strip()) < 80:
            return None
        return ScrapedDocument(id=f"bitcoindevguide-{url.split('/')[-2] if url.endswith('/') else url.split('/')[-1]}", title=title, body=body, authors=["Bitcoin.org Developers"], domain=str(self.config.domain), url=url, created_at=None)
