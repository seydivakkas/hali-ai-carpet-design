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


class VnaAdapter(BaseAdapter):
    """Adapter for The Victoria & Albert Museum API v2."""

    SEARCH_URL = "https://api.vam.ac.uk/v2/objects/search"

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
        logger.info(f"fetching_vna_dataset | query={self.query} | limit={limit}")

        output_dir.mkdir(parents=True, exist_ok=True)
        img_dir = output_dir / "images"
        img_dir.mkdir(exist_ok=True)

        manifest_entries = []
        downloaded = 0

        # Pagination handling
        page_size = 50 if limit > 50 else limit
        cluster_url: str | None = (
            f"{self.SEARCH_URL}?q={urllib.parse.quote(self.query)}&page_size={page_size}"
        )

        while downloaded < limit and cluster_url:
            search_results = self._fetch_json(cluster_url)
            records = search_results.get("records", [])

            if not records:
                logger.warning(f"no_more_records | downloaded={downloaded}")
                break

            for obj in records:
                if downloaded >= limit:
                    break

                obj_id = obj.get("systemNumber")
                # Need an image to download
                images = obj.get("_primaryImageId")

                if not images:
                    continue

                # Image URL formation (IIIF server for V&A)
                # Format: https://framemark.vam.ac.uk/collections/{imageId}/full/{size}/0/default.jpg
                image_id = images
                size_param = "full" if self.use_high_res else "!512,512"
                image_url = f"https://framemark.vam.ac.uk/collections/{image_id}/full/{size_param}/0/default.jpg"

                file_name = f"vna_{obj_id}.jpg"
                dest_path = img_dir / file_name

                time.sleep(0.1)  # Rate limiting respect

                if self._download_image(image_url, dest_path):
                    # Build metadata entry
                    title = obj.get("_primaryTitle", "")
                    date_text = obj.get("_primaryDate", "")
                    place = obj.get("_primaryPlace", "")

                    entry = {
                        "image_file": file_name,
                        "source_id": str(obj_id),
                        "source_url": f"https://collections.vam.ac.uk/item/{obj_id}",
                        "title": title,
                        "culture": place,
                        "period": "",
                        "date": date_text,
                        "medium": "",
                        "license": "public_domain_or_fair_use",  # V&A uses specific terms
                        "caption": f"{title}, {place}, {date_text}",
                    }
                    manifest_entries.append(entry)
                    downloaded += 1
                    logger.info(
                        f"downloaded_object | obj_id={obj_id} | progress={downloaded}/{limit}"
                    )

            # Next page
            meta = search_results.get("meta", {})
            next_url = meta.get("next")
            cluster_url = next_url if isinstance(next_url, str) and next_url else None

        # Save manifest
        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_entries, f, indent=2, ensure_ascii=False)

        logger.info(f"fetch_complete | downloaded={downloaded} | manifest={manifest_path}")
        return manifest_entries
