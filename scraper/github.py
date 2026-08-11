import os
from git import Repo
from loguru import logger
from typing import List, Optional, Type

from scraper.models import ScrapedDocument
from scraper.config import settings
from scraper.base import slugify
from scraper.base import BaseScraper


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
