import time
import re
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from loguru import logger
from typing import Type, List, Optional

from scraper.models import ScrapedDocument
from scraper.base import BaseScraper


class WebScraper(BaseScraper):
    """
    Base class for scraping websites.
    Provides standard methods for making HTTP requests with retries and delays.
    Also provides a default crawling loop if start_urls are provided.
    """
    
    start_urls: List[str] = []
    allow_regex: str = ".*"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.document_class: Type[ScrapedDocument] = ScrapedDocument
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

    def fetch(self, url: str, retries: int = 3, delay: float = 2.0) -> Optional[BeautifulSoup]:
        """
        Fetch a URL and return a BeautifulSoup object.
        Includes basic retry and delay logic.
        """
        for attempt in range(retries):
            try:
                logger.info(f"Fetching {url} (Attempt {attempt + 1}/{retries})")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return BeautifulSoup(response.text, 'html.parser')
            except requests.RequestException as e:
                logger.error(f"Error fetching {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(delay * (attempt + 1))
                else:
                    logger.error(f"Max retries reached for {url}")
                    return None

    async def scrape(self):
        """
        Default crawling loop. Fetches start_urls and follows links matching allow_regex.
        Subclasses can override this method if they don't need crawling.
        """
        visited = set()
        queue = self.start_urls.copy()
        allow_pattern = re.compile(self.allow_regex)
        
        while queue:
            url = queue.pop(0)
            if url in visited:
                continue
                
            visited.add(url)
            
            soup = self.fetch(url)
            if not soup:
                continue
                
            # Extract links
            for a in soup.find_all('a', href=True):
                href = a['href']
                absolute_url = urljoin(url, href)
                
                # Check domain
                parsed_url = urlparse(absolute_url)
                if parsed_url.netloc == urlparse(self.start_urls[0]).netloc:
                    clean_url = absolute_url.split('#')[0]
                    if clean_url not in visited and allow_pattern.search(clean_url):
                        queue.append(clean_url)
                        
            # Parse page
            try:
                document = self.parse_page(soup, url)
                if document:
                    await self.process_and_index_document(document)
            except Exception as e:
                logger.error(f"Error parsing {url}: {e}")

    def parse_page(self, soup: BeautifulSoup, url: str) -> Optional[ScrapedDocument]:
        """
        Parse the page and return a ScrapedDocument.
        Must be implemented if using the default scrape() loop.
        """
        raise NotImplementedError("Subclasses must implement parse_page if using default scrape()")
