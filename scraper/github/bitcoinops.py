import os
from datetime import datetime
import yaml
from loguru import logger
from typing import Optional

from scraper.github import GithubScraper
from scraper.models import ScrapedDocument



class BitcoinOpsScraper(GithubScraper):
    """
    Scraper for BitcoinOps GitHub repository.
    Parses Jekyll markdown files from _posts/en and _topics/en.
    """
    
    def is_relevant_file(self, file_path: str) -> bool:
        if not file_path.endswith(".md"):
            return False
            
        # Only process files in specific directories
        if "bitcoinops.github.io-master/_posts/en" in file_path or "bitcoinops.github.io-master/_topics/en" in file_path:
            return True
        if "_posts/en" in file_path or "_topics/en" in file_path:
            return True
            
        return False

    def parse_markdown(self, content: str):
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                return parts[1], parts[2]
        return "", content

    def parse_file(self, repo, file_path: str) -> Optional[ScrapedDocument]:
        try:
            full_path = os.path.join(repo.working_dir, file_path)
            with open(full_path, "r", encoding="utf-8") as file:
                content = file.read()
                
            front_matter, body = self.parse_markdown(content)
            
            try:
                metadata = yaml.safe_load(front_matter) or {}
            except yaml.YAMLError as e:
                logger.warning(f"YAML parsing error in {file_path}: {e}")
                metadata = {}

            is_topic = "_topics" in file_path
            
            custom_id = (
                os.path.basename(file_path).replace(".md", "")
                if is_topic
                else metadata.get("slug", os.path.basename(file_path).replace(".md", ""))
            )
            
            date_val = metadata.get("date")
            if isinstance(date_val, datetime):
                created_at = date_val.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            elif date_val:
                created_at = str(date_val)
            else:
                created_at = None

            document_data = {
                "id": f"bitcoinops-{custom_id}",
                "title": metadata.get("title", custom_id),
                "body": body,
                "created_at": created_at,
                "domain": str(self.config.domain),
                "url": (
                    f"https://bitcoinops.org/en/topics/{custom_id}"
                    if is_topic
                    else f"https://bitcoinops.org{metadata.get('permalink', '')}"
                ),
                "type": "topic" if is_topic else metadata.get("type", "newsletter"),
                "language": metadata.get("lang", "en"),
                "authors": ["Bitcoin Optech"],
            }
            
            return ScrapedDocument(**document_data)
            
        except Exception as e:
            logger.warning(f"Issue while parsing the file, {file_path}: {e}")
            return None
