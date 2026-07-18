import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .base import BaseAdapter

logger = logging.getLogger(__name__)


class MetOpenAccessAdapter(BaseAdapter):
    """Adapter for The Metropolitan Museum of Art Open Access API."""

    SEARCH_URL = "https://collectionapi.metmuseum.org/public/collection/v1/search"
    OBJECT_URL = "https://collectionapi.metmuseum.org/public/collection/v1/objects"

    def __init__(self, query: str = "carpet", use_high_res: bool = False):
        self.query = query
        self.use_high_res = use_high_res

    def _fetch_json(self, url: str) -> dict[str, Any]:
        req = urllib.request.Request(url, headers={"User-Agent": "HaliAICarpetDesign/1.0"})
        try:
            with urllib.request.urlopen(req) as response:
                payload = json.loads(response.read().decode("utf-8"))
                return payload if isinstance(payload, dict) else {}
        except urllib.error.URLError as e:
            logger.error(f"api_request_failed | url={url} | error={e}")
            return {}

    def _download_image(self, image_url: str, dest_path: Path) -> bool:
        req = urllib.request.Request(image_url, headers={"User-Agent": "HaliAICarpetDesign/1.0"})
        try:
            with urllib.request.urlopen(req) as response, open(dest_path, "wb") as out_file:
                data = response.read()
                out_file.write(data)
            return True
        except urllib.error.URLError as e:
            logger.error(f"image_download_failed | url={image_url} | error={e}")
            return False

    def fetch_dataset(self, output_dir: Path, limit: int = 100) -> list[dict[str, Any]]:
        logger.info(f"fetching_met_dataset | query={self.query} | limit={limit}")

        output_dir.mkdir(parents=True, exist_ok=True)
        img_dir = output_dir / "images"
        img_dir.mkdir(exist_ok=True)

        # 1. Search for objects
        search_url = f"{self.SEARCH_URL}?q={urllib.parse.quote(self.query)}&isHighlight=false"
        search_results = self._fetch_json(search_url)
        object_ids = search_results.get("objectIDs", [])

        if not object_ids:
            logger.warning(f"no_objects_found | query={self.query}")
            return []

        logger.info(f"objects_found | count={len(object_ids)}")

        manifest_entries = []
        downloaded = 0

        # 2. Fetch details and download
        for obj_id in object_ids:
            if downloaded >= limit:
                break

            time.sleep(
                0.015
            )  # Rate limiting (80 requests per second allowed, this ensures ~60/s max)

            obj_url = f"{self.OBJECT_URL}/{obj_id}"
            obj_data = self._fetch_json(obj_url)

            if not obj_data:
                continue

            # Must be public domain
            if not obj_data.get("isPublicDomain"):
                continue

            # Pick image URL
            image_url = (
                obj_data.get("primaryImage")
                if self.use_high_res
                else obj_data.get("primaryImageSmall")
            )
            if not image_url:
                continue

            # Download image
            file_name = f"met_{obj_id}.jpg"
            dest_path = img_dir / file_name

            if self._download_image(image_url, dest_path):
                # Build metadata entry
                entry = {
                    "image_file": file_name,
                    "source_id": str(obj_id),
                    "source_url": obj_data.get("objectURL", ""),
                    "title": obj_data.get("title", ""),
                    "culture": obj_data.get("culture", ""),
                    "period": obj_data.get("period", ""),
                    "date": obj_data.get("objectDate", ""),
                    "medium": obj_data.get("medium", ""),
                    "license": "public_domain",
                    "caption": f"{obj_data.get('title', '')}, {obj_data.get('culture', '')}, {obj_data.get('medium', '')}",
                }
                manifest_entries.append(entry)
                downloaded += 1
                logger.info(f"downloaded_object | obj_id={obj_id} | progress={downloaded}/{limit}")

        # 3. Save manifest
        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_entries, f, indent=2, ensure_ascii=False)

        logger.info(f"fetch_complete | downloaded={downloaded} | manifest={manifest_path}")
        return manifest_entries
