#!/usr/bin/env python3
"""
Simple entrypoint to run scrapers.
Usage: python run_scraper.py [source_name]
"""
import sys
import asyncio
import importlib
import inspect
from loguru import logger
import os

log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "logs"))
os.makedirs(log_dir, exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO")
logger.add(os.path.join(log_dir, "scraper.log"), level="DEBUG", rotation="10 MB", retention="7 days")



def get_scraper_class(src_type: str, src):
    # Determine the script name to load
    script_name = src.script if getattr(src, 'script', None) else src.name.lower()
    module_name = f"scraper.{src_type}.{script_name}"
    
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        logger.error(f"Could not load module {module_name}: {e}")
        return None
        
    from scraper.base import BaseScraper
    
    # Find the class that subclasses BaseScraper (ignoring the base classes themselves)
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, BaseScraper) and obj.__name__ not in ("BaseScraper", "GithubScraper", "WebScraper"):
            if obj.__module__ == module_name or "default_github" in obj.__module__:
                return obj
                
    return None

async def main():
    from scraper.config import settings
    from scraper.outputs.text_output import TextOutput

    source_name = sys.argv[1] if len(sys.argv) > 1 else None
    sources = settings.load_sources()
    
    # Load targets as tuples of (source_type, source_config)
    targets = []
    for src_type, src_list in sources.items():
        for src in src_list:
            if not source_name or src.name.lower() == source_name.lower():
                targets.append((src_type, src))

    if source_name and not targets:
        logger.error(f"Source '{source_name}' not found in sources.yaml")
        sys.exit(1)

    for src_type, src in targets:
        logger.info(f"Starting scrape: {src.name} ({src_type})")
        scraper_class = get_scraper_class(src_type, src)
        
        if not scraper_class:
            logger.error(f"No scraper implementation found for {src.name} in scraper/{src_type}/")
            continue
            
        output = TextOutput(
            source_name=src.name,
            index_name=settings.DEFAULT_INDEX if hasattr(settings, "DEFAULT_INDEX") else None,
            batch_size=settings.config.getint("batch_size", 100) if hasattr(settings, "config") else 100,
        )
        
        scraper = scraper_class(src, output)
        await scraper.run()
        logger.info(f"Finished scrape: {src.name}")

if __name__ == "__main__":
    asyncio.run(main())
