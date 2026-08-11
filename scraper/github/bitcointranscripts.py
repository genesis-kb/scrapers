import os
from datetime import datetime
import re
import yaml
from loguru import logger
from typing import Optional

from scraper.github import GithubScraper
from scraper.models import BitcoinTranscriptDocument



class BitcoinTranscriptsScraper(GithubScraper):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.document_class = BitcoinTranscriptDocument

    def is_relevant_file(self, file_path: str) -> bool:
        file_name = os.path.basename(file_path)
        if not file_name.endswith('.md'):
            return False
            
        translated_transcript_pattern = r'\.([a-z][a-z])\.md$'
        is_translated = re.search(translated_transcript_pattern, file_name)
        is_index = file_name.startswith('_')
        
        if is_index or is_translated:
            return False
            
        return True

    def parse_markdown(self, content: str):
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                return parts[1], parts[2]
        return "", content

    def parse_file(self, repo, file_path: str) -> Optional[BitcoinTranscriptDocument]:
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

            url_path = os.path.normpath(file_path.replace('.md', ''))
            transcript_by = metadata.get('transcript_by', "")
            
            date_val = metadata.get('date')
            if isinstance(date_val, datetime):
                created_at = date_val.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            elif date_val:
                try:
                    created_at = datetime.strptime(str(date_val), '%Y-%m-%d').strftime('%Y-%m-%dT%H:%M:%S.000Z')
                except ValueError:
                    created_at = str(date_val)
            else:
                created_at = None

            document_data = {
                "id": "bitcointranscripts+" + url_path.replace(os.sep, "+"),
                "title": metadata.get("title", "Unknown Title"),
                "body": body,
                "created_at": created_at,
                "domain": str(self.config.domain),
                "url": f"https://btctranscripts.com/{url_path.replace(os.sep, '/')}",
                "authors": metadata.get('speakers', []),
                "tags": metadata.get('tags', []),
                "media": metadata.get('media', ""),
                "transcript_by": transcript_by,
                "needs_review": "--needs-review" in transcript_by,
                "transcript_source": url_path.split(os.sep)[0] if len(url_path.split(os.sep)) > 0 else "Unknown"
            }
            
            return BitcoinTranscriptDocument(**document_data)
            
        except Exception as e:
            logger.warning(f"Issue while parsing the file, {file_path}: {e}")
            return None
