from abc import ABC, abstractmethod
from datetime import datetime
import os
import re
import time
import unicodedata
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional, Type
import requests
from bs4 import BeautifulSoup
from git import Repo
from loguru import logger

from scraper.models import RunStats, ScraperRunDocument, ScrapedDocument, SourceConfig
from scraper.outputs import AbstractOutput
from scraper.config import settings


def parse_standard_date_formats(date_str: str) -> Optional[str]:
    formats = [
        "%Y-%m-%d", "%Y/%m/%d", "%B %d, %Y", "%d %B %Y",
        "%b %d, %Y", "%d %b %Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
        "%B %d, %Y, %I:%M:%S %p", "%B %d, %Y, %I:%M %p",
        "%b %d, %Y, %I:%M:%S %p", "%b %d, %Y, %I:%M %p",
        "%d %B %Y %H:%M:%S", "%d %B %Y %H:%M",
        "%d %b %Y %H:%M:%S", "%d %b %Y %H:%M",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).isoformat()
        except ValueError:
            continue
    return None

def slugify(value: str) -> str:
    value = str(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')

def strip_emails(text: str) -> str:
    if not text:
        return text
    return re.sub(r'<[^>]+>', '', text).strip()


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers.
    """

    def __init__(self, config: SourceConfig, output: AbstractOutput):
        domain = str(config.domain).rstrip("/") + "/"
        config_dict = config.model_dump()
        config_dict["domain"] = domain
        self.config = SourceConfig(**config_dict)
        self.output = output
        self.resources_to_process = None
        self.total_documents_processed = 0
        self._error: Optional[str] = None
        self._success = True
        self._started_at: Optional[str] = None

    @abstractmethod
    async def scrape(self):
        pass

    async def process_and_index_document(self, document: ScrapedDocument):
        await self.output.index_document(document)
        self.total_documents_processed += 1
        logger.info(f"Processed document {document.id}. Total: {self.total_documents_processed}")

    async def run(self):
        self._started_at = datetime.now().isoformat()
        async with self.output:
            try:
                await self.scrape()
            except Exception as e:
                self._success = False
                self._error = str(e)
                raise
            finally:
                await self.record_run()

    async def get_last_successful_run(self) -> Optional[ScraperRunDocument]:
        return await self.output.get_last_successful_run(self.config.name)

    async def record_run(self) -> None:
        try:
            stats = RunStats(
                resources_to_process=self.resources_to_process,
                documents_indexed=self.total_documents_processed,
            )
            run_document = ScraperRunDocument(
                scraper=self.__class__.__name__,
                source=self.config.name,
                domain=str(self.config.domain),
                stats=stats,
                last_commit_hash=getattr(self, "current_commit_hash", None),
                started_at=self._started_at,
                success=self._success,
                error_message=self._error,
            )
            await self.output.record_run(run_document)
            logger.debug(f"Recorded run stats for {self.config.name}")
        except Exception as e:
            logger.error(f"Error recording run statistics: {e}")


class GithubScraper(BaseScraper):
    """
    Base class for scraping GitHub repositories.
    Provides standard methods for cloning/updating repositories and finding changed files.
    Subclasses must implement file parsing logic.
    """
    DEFAULT_EXCLUDED_FILES = {".DS_Store", "README.md", "CONTRIBUTING.md", "LICENSE.md", "LICENSE"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.repo_path = os.path.join(settings.DATA_DIR, slugify(self.config.name))
        self.excluded_files = self.DEFAULT_EXCLUDED_FILES.copy()
        self.document_class: Type[ScrapedDocument] = ScrapedDocument
        self.test_resources = self.config.test_resources

    async def scrape(self):
        """
        Main scraping method for GitHub repositories.
        Uses last successful run's commit hash to determine what files to process.
        """
        last_run = await self.get_last_successful_run()
        last_commit_hash = last_run.last_commit_hash if last_run else None

        repo = self.clone_or_pull_repo()
        
        if self.config.checkout_commit:
            try:
                repo.git.checkout(self.config.checkout_commit)
            except Exception as e:
                logger.error(f"Failed to checkout commit {self.config.checkout_commit}: {e}")
                raise

        self.current_commit_hash = repo.head.commit.hexsha

        if self.test_resources:
            logger.info(f"Running in test mode with resources: {self.test_resources}")
            files_to_process = self.test_resources
        else:
            logger.info(f"Running in full mode: {last_commit_hash} -> {self.current_commit_hash}")
            files_to_process = self.get_changed_files(repo, last_commit_hash)

        self.resources_to_process = len(files_to_process)
        await self.process_files(repo, files_to_process)

    def get_changed_files(self, repo: Repo, last_commit_hash: str) -> List[str]:
        if not last_commit_hash:
            return [item.path for item in repo.tree().traverse() if item.type == "blob"]

        current_commit = repo.head.commit
        previous_commit = repo.commit(last_commit_hash)

        diff_index = previous_commit.diff(current_commit)

        changed_files = []
        for diff_item in diff_index:
            if diff_item.a_path:
                changed_files.append(diff_item.a_path)
            if diff_item.b_path and diff_item.b_path != diff_item.a_path:
                changed_files.append(diff_item.b_path)

        return list(set(changed_files))

    def clone_or_pull_repo(self) -> Repo:
        if os.path.exists(self.repo_path):
            logger.info(f"Updating existing repo at path: {self.repo_path}")
            repo = Repo(self.repo_path)
            repo.git.reset("--hard")
            default_branch = repo.git.symbolic_ref("refs/remotes/origin/HEAD").split("/")[-1]
            repo.git.checkout(default_branch)
            origin = repo.remotes.origin
            origin.pull()
        else:
            logger.info(f"Cloning repo to path: {self.repo_path}")
            repo = Repo.clone_from(str(self.config.url), self.repo_path)
        return repo

    async def process_files(self, repo: Repo, files: List[str]) -> int:
        """Process a list of files from the repository."""
        for file_path in files:
            if self.is_relevant_file(file_path):
                logger.info(f"Processing file: {file_path}")
                try:
                    document = self.parse_file(repo, file_path)
                    if document:
                        await self.process_and_index_document(document)
                except Exception as e:
                    logger.error(f"Failed to parse file: {file_path} - {e}")

    def is_relevant_file(self, file_path: str) -> bool:
        """Filter files before parsing. Subclasses should override this."""
        file_name = os.path.basename(file_path)
        if file_name.startswith(".") or file_name in self.excluded_files:
            return False
        
        if self.config.directories:
            if not any(file_path.startswith(d) for d in self.config.directories):
                return False
                
        return file_path.endswith(".md")

    def parse_file(self, repo: Repo, file_path: str) -> Optional[ScrapedDocument]:
        """
        Parse a file and return a ScrapedDocument.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement parse_file")


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
