import os
import json
import time
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger

from scraper.web import WebScraper
from scraper.models import ScrapedDocument
from scraper.config import settings




class BitcoinTalkScraper(WebScraper):
    
    BOARD_URL = 'https://bitcointalk.org/index.php?board=6.'
    AUTHORS = [
        'achow101', 'kanzure', 'Sergio_Demian_Lerner', 'Nicolas Dorier', 'jl2012', 
        'Peter Todd', 'Gavin Andresen', 'adam3us', 'Pieter Wuille', 'Meni Rosenfeld', 
        'Mike Hearn', 'wumpus', 'Luke-Jr', 'Matt Corallo', 'jgarzik', 'andytoshi', 
        'satoshi', 'Cdecker', 'TimRuffing', 'gmaxwell'
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_dir = os.path.join(settings.DATA_DIR, 'bitcointalk')
        os.makedirs(self.data_dir, exist_ok=True)
        self.topics_file = os.path.join(self.data_dir, 'topics.json')

    async def scrape(self):
        topics = self.get_topics()
        logger.info(f"Found {len(topics)} topics")
        
        for i, topic in enumerate(topics):
            logger.info(f"Processing {i + 1}/{len(topics)}")
            await self.fetch_posts(topic)

    def get_topics(self) -> list:
        if os.path.exists(self.topics_file):
            with open(self.topics_file, 'r') as f:
                return json.load(f)
                
        offset = 0
        topics = []
        while True:
            logger.info(f"Downloading page {offset // 40}...")
            url = f"{self.BOARD_URL}{offset}"
            
            soup = self.fetch(url)
            if not soup:
                time.sleep(2)
                continue
                
            tops = []
            links = soup.select('tr > td > span > a')
            for link in links:
                href = link.get('href')
                if not href.startswith("https://bitcointalk.org/index.php?topic=") or 'class' in link.attrs:
                    continue
                tops.append(href)

            offset += 40
            topics.extend(tops)
            if len(tops) != 40:
                logger.info("No more data")
                break
            time.sleep(0.8)

        with open(self.topics_file, 'w') as f:
            json.dump(topics, f)
            
        return topics

    async def fetch_posts(self, url: str):
        resp = await self.get_documents_from_post(url)
        if not resp:
            return
            
        urls = resp['urls']
        for u in urls:
            logger.info(f"Downloading {u}...")
            await self.get_documents_from_post(u)
            time.sleep(1)

    async def get_documents_from_post(self, url: str) -> dict:
        soup = self.fetch(url)
        if not soup:
            time.sleep(10)
            return await self.get_documents_from_post(url)

        urls = list(set([a.get('href') for a in soup.find_all(class_='navPages')]))
        
        table = soup.select_one('#quickModForm > table:nth-child(1)')
        if not table:
            return {'urls': urls}
            
        first_tr_class = table.find('tr').get('class')
        tr_list = table.find_all('tr', class_=first_tr_class)
        logger.info(f"Found {len(tr_list)} posts in {url}")

        for tr in tr_list:
            try:
                author_elem = tr.select_one('.poster_info > b > a')
                if not author_elem:
                    continue
                author = author_elem.text
                
                if author not in self.AUTHORS:
                    continue

                logger.info(f"Post by: {author}")
                date_text = tr.select_one('.td_headerandpost .smalltext').text.strip()

                if 'Last edit:' in date_text:
                    date_text = date_text.split('Last edit:')[-1].strip()

                date_parts = date_text.split('by')[0].strip()
                if 'Today at' in date_parts:
                    date_parts = date_parts.replace('Today at', datetime.now().strftime('%B %d, %Y,'))

                date = datetime.strptime(date_parts, '%B %d, %Y, %I:%M:%S %p').isoformat()
                
                subject_elem = tr.select_one('.td_headerandpost .subject > a')
                post_url = subject_elem.get('href')
                title = subject_elem.text
                body_elem = tr.select_one('.td_headerandpost .post')
                message_number = tr.select_one('.td_headerandpost .message_number').text

                for tag in body_elem.select('.quoteheader, .quote'):
                    tag.decompose()

                body = body_elem.text.strip()
                _id = post_url[post_url.index('#msg') + 4:]

                document_data = {
                    'id': f'bitcointalk-{_id}',
                    'title': title,
                    'body': body,
                    'authors': [author],
                    'domain': str(self.config.domain),
                    'url': post_url,
                    'created_at': date,
                    'type': 'topic' if message_number == "#1" else "post"
                }
                
                document = ScrapedDocument(**document_data)
                await self.process_and_index_document(document)
                
            except Exception as e:
                logger.error(f"Error processing post: {e}")

        return {'urls': urls}
