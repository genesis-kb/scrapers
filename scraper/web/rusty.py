import re
from bs4 import BeautifulSoup
from scraper.web import WebScraper
from scraper.models import ScrapedDocument

class RustyScraper(WebScraper):
    start_urls = ["https://rusty.ozlabs.org"]
    
    def parse_page(self, soup: BeautifulSoup, url: str):
        keywords = ["bitcoin", "lightning", "bip", "payment", "block", "transaction"]
        entry = soup.find('div', class_='entry-content')
        if not entry:
            return None
        body = entry.get_text(separator='\n').strip()
        h1 = soup.find('h1')
        title = h1.get_text().strip() if h1 else ""
        pattern = re.compile("|".join(keywords), re.IGNORECASE)
        if not title or not re.search(pattern, title):
            return None
        author_tag = soup.find('span', class_='author vcard')
        author = author_tag.get_text().strip() if author_tag else "Rusty"
        time_tag = soup.find('time', class_='entry-date published')
        date = time_tag.get('datetime') if time_tag else None
        return ScrapedDocument(id=f"rusty-{url.split('/')[-2] if url.endswith('/') else url.split('/')[-1]}", title=title, body=body, authors=[author], domain=str(self.config.domain), url=url, created_at=date)
