import os
from datetime import datetime
import yaml
from loguru import logger
from typing import Optional

from scraper.github import GithubScraper
from scraper.models import ScrapedDocument

from scraper.base import strip_emails, parse_standard_date_formats

class DefaultGithubScraper(GithubScraper):
    """
    Default GitHub scraper that clones the repo and parses Markdown files.
    Reads YAML/BIP-style front matter for metadata.
    """
    
    def parse_markdown(self, content: str):
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                return parts[1], parts[2]
        return "", content
        
    def _parse_bip_style_content(self, content: str) -> dict:
        metadata = {}
        current_key = None
        for line in content.split("\n"):
            line = line.strip()
            if ":" in line:
                key, value = line.split(":", 1)
                current_key = key.strip()
                metadata[current_key] = [value.strip()]
            elif current_key:
                metadata[current_key].append(line)
        
        for key in metadata:
            if len(metadata[key]) == 1 and key != "Author":
                metadata[key] = metadata[key][0]
        return metadata

    def parse_file(self, repo, file_path: str) -> Optional[ScrapedDocument]:
        try:
            full_path = os.path.join(repo.working_dir, file_path)
            with open(full_path, "r", encoding="utf-8") as file:
                content = file.read()
                
            front_matter, body = self.parse_markdown(content)
            
            try:
                metadata = yaml.safe_load(front_matter)
                if not isinstance(metadata, dict):
                    metadata = self._parse_bip_style_content(front_matter)
            except Exception:
                metadata = self._parse_bip_style_content(front_matter)
            
            title = metadata.get("title") or metadata.get("Title") or os.path.basename(file_path).replace(".md", "")
            
            # Author
            authors = metadata.get("authors") or metadata.get("Author")
            if not authors:
                authors = []
            elif isinstance(authors, str):
                authors = [authors]
            authors = [strip_emails(author) for author in authors]

            # Date
            created_at = None
            date_fields = ["date", "created", "created_at", "published", "Date", "Created"]
            for field in date_fields:
                value = metadata.get(field)
                if value:
                    if isinstance(value, datetime):
                        created_at = value.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                    else:
                        parsed = parse_standard_date_formats(str(value))
                        created_at = parsed if parsed else str(value)
                    break
                    
            # ID
            file_name = os.path.basename(file_path)
            name_without_extension = os.path.splitext(file_name)[0]
            doc_id = f"{self.config.name.lower()}-{name_without_extension}"
            
            # URL
            github_path = f"blob/master/{file_path}"
            url = f"{str(self.config.domain).rstrip('/')}/{github_path}"

            document_data = {
                "id": doc_id,
                "title": title,
                "body": body,
                "created_at": created_at,
                "domain": str(self.config.domain),
                "url": url,
                "authors": authors,
                "tags": metadata.get("tags")
            }
            
            return ScrapedDocument(**document_data)
            
        except Exception as e:
            logger.warning(f"Issue while parsing the file, {file_path}: {e}")
            return None

# Register the default scraper for various simple GitHub repositories
