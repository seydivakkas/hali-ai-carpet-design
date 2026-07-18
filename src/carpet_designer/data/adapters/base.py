from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseAdapter(ABC):
    """Abstract base class for dataset ingestion adapters."""

    @abstractmethod
    def fetch_dataset(self, output_dir: Path, limit: int = 100) -> list[dict[str, Any]]:
        """
        Fetch a dataset and download its contents to output_dir.

        Args:
            output_dir (Path): The directory to save images and manifest.
            limit (int): The maximum number of items to fetch.

        Returns:
            List[Dict[str, Any]]: A list of manifest entries.
        """
        pass
