import os
import subprocess
import platform
import xml.etree.ElementTree as ET
from io import StringIO
from html.parser import HTMLParser
from datetime import datetime
from loguru import logger
from tqdm import tqdm

from scraper.web import WebScraper
from scraper.models import ScrapedDocument
from scraper.config import settings



class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d):
        self.text.write(d)

    def get_data(self):
        return self.text.getvalue()


def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()



class StackExchangeScraper(WebScraper):
    """
    Scraper for StackExchange dumps.
    Downloads the 7z archive, extracts it, and parses the XML files.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.download_path = os.path.join(settings.DATA_DIR, "bitcoin.stackexchange.com.7z")
        self.extract_path = os.path.join(settings.DATA_DIR, "bitcoin.stackexchange.com")
        
    async def scrape(self):
        self.download_dump()
        self.extract_dump()
        
        users_file = os.path.join(self.extract_path, "Users.xml")
        posts_file = os.path.join(self.extract_path, "Posts.xml")
        
        users = self.parse_users(users_file)
        docs = self.parse_posts(posts_file)
        
        for post in tqdm(docs):
            try:
                post_type = post.attrib.get("PostTypeId")
                if post_type not in ("1", "2"):
                    continue

                user = users.get(post.attrib.get("OwnerUserId")) or post.attrib.get("OwnerDisplayName") or "Anonymous"
                
                # prepare the document based on type: 'question' or 'answer'
                parent_id = post.attrib.get("ParentId")
                if parent_id is None:
                    tags = post.attrib.get("Tags", "")
                    if len(tags) > 2:
                        tags = tags[1:-1].split("><")
                    else:
                        tags = []
                        
                    document_data = {
                        "id": "stackexchange-" + post.attrib.get("Id"),
                        "title": post.attrib.get("Title"),
                        "body": strip_tags(post.attrib.get("Body", "")),
                        "authors": [user],
                        "tags": tags,
                        "domain": str(self.config.domain),
                        "url": f"https://bitcoin.stackexchange.com/questions/{post.attrib.get('Id')}",
                        "thread_url": f"https://bitcoin.stackexchange.com/questions/{post.attrib.get('Id')}",
                        "created_at": post.attrib.get("CreationDate"),
                        "type": "question"
                    }
                else:
                    question = docs.find(f"./row[@Id='{parent_id}']")
                    title = question.attrib.get("Title") + " (Answer)" if question is not None else "Answer"
                    
                    document_data = {
                        "id": "stackexchange-" + post.attrib.get("Id"),
                        "title": title,
                        "body": strip_tags(post.attrib.get("Body", "")),
                        "authors": [user],
                        "domain": str(self.config.domain),
                        "url": f"https://bitcoin.stackexchange.com/questions/{parent_id}#{post.attrib.get('Id')}",
                        "thread_url": f"https://bitcoin.stackexchange.com/questions/{parent_id}#{post.attrib.get('Id')}",
                        "created_at": post.attrib.get("CreationDate"),
                        "type": "answer"
                    }

                document = ScrapedDocument(**document_data)
                await self.process_and_index_document(document)

            except Exception as ex:
                logger.error(f"Error occurred: {ex}")

    def parse_users(self, file_path) -> dict:
        users = {}
        tree = ET.parse(file_path)
        root = tree.getroot()
        for user in root:
            users[user.attrib.get("Id")] = user.attrib.get("DisplayName")
        logger.info(f"Number of users found: {len(users.keys())}")
        return users

    def parse_posts(self, file_path):
        tree = ET.parse(file_path)
        return tree.getroot()

    def download_dump(self):
        if os.path.exists(self.download_path):
            logger.info(f'File already exists at path: {self.download_path}')
            return

        os.makedirs(os.path.dirname(self.download_path), exist_ok=True)
        logger.info('Downloading the data from archive...')
        archive_url = "https://archive.org/download/stackexchange/bitcoin.stackexchange.com.7z"
        try:
            r = self.session.get(archive_url, stream=True)
            if r.status_code == 200:
                with open(self.download_path, "wb") as f:
                    for chunk in tqdm(r.iter_content(chunk_size=1024)):
                        if chunk:
                            f.write(chunk)
                logger.info(f"Successfully downloaded data to: {self.download_path}")
            else:
                logger.error(f"Request returned an error: {r.status_code}")
        except Exception as e:
            logger.error(f"An error occurred while downloading: {e}")

    def extract_dump(self):
        if os.path.exists(self.extract_path) and os.listdir(self.extract_path):
            logger.info(f'Data already extracted at: {self.extract_path}')
            return
            
        try:
            logger.info('Extracting the data...')
            os.makedirs(self.extract_path, exist_ok=True)

            try:
                import py7zr
                logger.info("Extracting archive using py7zr...")
                with py7zr.SevenZipFile(self.download_path, mode='r') as z:
                    z.extractall(path=self.extract_path)
                return
            except ImportError:
                logger.debug("py7zr not installed, attempting system 7z binaries")

            executable = None
            if platform.system() == 'Windows':
                default_win_path = r"C:\Program Files\7-Zip\7z.exe"
                if os.path.exists(default_win_path):
                    executable = default_win_path

            if not executable:
                import shutil
                for cmd in ["7z", "7za", "7zz", "p7zip"]:
                    found = shutil.which(cmd)
                    if found:
                        executable = found
                        break

            if executable:
                logger.info(f"Extracting archive using CLI tool: {executable}")
                subprocess.check_call([executable, "x", "-o" + self.extract_path, "-y", self.download_path])
            else:
                raise RuntimeError("No 7z extraction tool found.")
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            raise
