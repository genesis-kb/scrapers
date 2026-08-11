import os
import configparser
import yaml
from dotenv import load_dotenv
from typing import Dict, List

from scraper.models import SourceConfig


def get_project_root():
    """
    Find the project root by searching for a specific file.

    This function traverses up the directory tree from the current file's location
    until it finds a directory containing 'cli.py', which is assumed to be
    the project root.

    Returns:
        str: The absolute path to the project root directory.

    Raises:
        Exception: If the project root cannot be found.
    """
    # The sources.yaml file is located in the parent directory (scraper/)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


class Settings:
    def __init__(self):
        # Reload environment variables from .env file
        load_dotenv(override=True)
        self.DATA_DIR = os.getenv("DATA_DIR", os.path.join(get_project_root(), "data"))
        self.DEFAULT_INDEX = os.getenv("DEFAULT_INDEX", "bitcoin_search")


    def load_sources(self) -> Dict[str, List[SourceConfig]]:
        sources_path = os.path.join(get_project_root(), "sources.yaml")
        try:
            with open(sources_path, "r") as file:
                data = yaml.safe_load(file)
        except FileNotFoundError:
            print(f"Warning: {sources_path} not found. Using empty sources.")
            return {}

        sources = {}
        for source_type, source_list in data.items():
            sources[source_type] = [SourceConfig(**source) for source in source_list]

        return sources

# Initialize the Settings class and expose an instance
settings = Settings()

__all__ = ["settings"]
