"""Configurable importer for a rights-restricted company product catalog."""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .base import BaseAdapter

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


def _class_tokens(attributes: dict[str, str]) -> set[str]:
    return set(attributes.get("class", "").split())


def _clean_text(parts: list[str]) -> str:
    return " ".join("".join(parts).split())


class _ProductCardParser(HTMLParser):
    """Extract product cards from a collection page without JavaScript."""

    def __init__(self, collection: str) -> None:
        super().__init__(convert_charrefs=True)
        self.collection = collection
        self.products: list[dict[str, Any]] = []
        self._div_depth = 0
        self._card_depth: int | None = None
        self._size_container_depth: int | None = None
        self._current: dict[str, Any] | None = None
        self._capture_field: str | None = None
        self._capture_tag: str | None = None
        self._capture_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        classes = _class_tokens(attributes)

        if tag == "div":
            self._div_depth += 1
            if self._current is None and "product-card" in classes:
                self._current = {
                    "product_id": attributes.get("data-productid", ""),
                    "collection": self.collection,
                    "sizes": [],
                }
                self._card_depth = self._div_depth

        if self._current is None:
            return

        if tag == "a" and "product-image__body" in classes:
            self._current.setdefault("source_path", attributes.get("href", ""))
        elif tag == "img" and "product-image__img" in classes:
            image_url = attributes.get("src") or attributes.get("data-src", "")
            self._current.setdefault("image_url", image_url)
        elif tag == "a" and "product-info-detail" in classes:
            self._current["source_path"] = attributes.get(
                "href", self._current.get("source_path", "")
            )
            self._begin_capture(tag, "title")
        elif tag == "div" and "productList-categoryName" in classes:
            self._begin_capture(tag, "collection")
        elif tag == "div" and "product-card__prices" in classes:
            self._begin_capture(tag, "price_display")
        elif tag == "div" and "product-card__description" in classes:
            self._begin_capture(tag, "description")
        elif tag == "div" and "input-radio-label__list" in classes:
            self._size_container_depth = self._div_depth
        elif tag == "span" and self._size_container_depth is not None:
            self._begin_capture(tag, "size")

    def handle_data(self, data: str) -> None:
        if self._capture_field is not None:
            self._capture_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._current is not None and self._capture_tag == tag:
            value = _clean_text(self._capture_parts)
            if value:
                if self._capture_field == "size":
                    if re.fullmatch(r"\d{2,3}\s*[xX×]\s*\d{2,3}", value):
                        normalized = re.sub(r"\s*[xX×]\s*", "x", value)
                        if normalized not in self._current["sizes"]:
                            self._current["sizes"].append(normalized)
                elif self._capture_field is not None:
                    self._current[self._capture_field] = value
            self._capture_field = None
            self._capture_tag = None
            self._capture_parts = []

        if tag != "div":
            return

        if self._size_container_depth == self._div_depth:
            self._size_container_depth = None

        if self._current is not None and self._card_depth == self._div_depth:
            if (
                self._current.get("source_path")
                and self._current.get("title")
                and self._current.get("image_url")
            ):
                self.products.append(self._current)
            self._current = None
            self._card_depth = None
            self._size_container_depth = None
            self._capture_field = None
            self._capture_tag = None
            self._capture_parts = []

        self._div_depth = max(0, self._div_depth - 1)

    def _begin_capture(self, tag: str, field: str) -> None:
        self._capture_tag = tag
        self._capture_field = field
        self._capture_parts = []


class RestrictedCatalogAdapter(BaseAdapter):
    """Download catalog records strictly for internal design-reference workflows.

    The source catalog is assumed to reserve all rights. Every generated manifest
    therefore blocks training and commercial use until the rights holder records a
    written permission reference.
    """

    USER_AGENT = "HaliAICarpetDesign/1.0 (+internal-reference-import)"
    USAGE_SCOPE = "internal_design_reference_only"

    def __init__(
        self,
        collections: Sequence[str],
        *,
        base_url: str = "https://catalog.example",
        limit_per_collection: int | None = None,
        metadata_only: bool = False,
        request_delay_seconds: float = 0.25,
        permission_ref: str = "",
    ) -> None:
        requested = [name.strip() for name in collections if name.strip()]
        if not requested:
            raise ValueError("At least one catalog collection is required.")
        parsed_base_url = urllib.parse.urlparse(base_url)
        if parsed_base_url.scheme not in {"http", "https"} or not parsed_base_url.netloc:
            raise ValueError("base_url must be an absolute HTTP(S) URL.")
        self.base_url = base_url.rstrip("/")
        self.collections = requested
        self.limit_per_collection = limit_per_collection
        self.metadata_only = metadata_only
        self.request_delay_seconds = max(0.0, request_delay_seconds)
        self.permission_ref = permission_ref.strip()

    @property
    def training_use(self) -> str:
        """Return the manifest training policy implied by recorded permission."""
        return "approved" if self.permission_ref else "blocked_pending_written_permission"

    @property
    def commercial_use(self) -> str:
        """Keep approval scoped to the rights-holder-approved internal model."""
        if self.permission_ref:
            return "approved_for_company_internal_model"
        return "blocked_pending_legal_review"

    @property
    def dataset_status(self) -> str:
        """Return a machine-enforceable governance status."""
        return "TRAINING_APPROVED" if self.permission_ref else "RESTRICTED_REFERENCE_ONLY"

    @staticmethod
    def parse_collection_page(html: str, collection: str) -> list[dict[str, Any]]:
        """Parse normalized product records from collection-page HTML."""
        parser = _ProductCardParser(collection)
        parser.feed(html)
        return parser.products

    def _request(self, url: str) -> urllib.request.Request:
        return urllib.request.Request(
            url,
            headers={
                "User-Agent": self.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,image/*;q=0.9,*/*;q=0.8",
                "Accept-Encoding": "identity",
            },
        )

    def _fetch_text(self, url: str) -> str:
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                with urllib.request.urlopen(self._request(url), timeout=30) as response:
                    charset = response.headers.get_content_charset() or "utf-8"
                    return bytes(response.read()).decode(charset, errors="replace")
            except (OSError, urllib.error.URLError) as error:
                last_error = error
                logger.warning("catalog_request_retry | url=%s | attempt=%d", url, attempt)
                time.sleep(self.request_delay_seconds * attempt)
        raise RuntimeError(f"Catalog request failed for {url}: {last_error}")

    def _download_image(self, image_url: str, destination: Path) -> str:
        if destination.exists() and destination.stat().st_size > 0:
            return hashlib.sha256(destination.read_bytes()).hexdigest()

        with urllib.request.urlopen(self._request(image_url), timeout=45) as response:
            content_type = response.headers.get_content_type()
            payload = response.read()
        if not content_type.startswith("image/") or not payload:
            raise RuntimeError(f"Unexpected image response from {image_url}: {content_type}")

        temporary = destination.with_suffix(f"{destination.suffix}.part")
        temporary.write_bytes(payload)
        temporary.replace(destination)
        return hashlib.sha256(payload).hexdigest()

    def fetch_dataset(self, output_dir: Path, limit: int = 0) -> list[dict[str, Any]]:
        """Fetch catalog cards and optionally their display-resolution images.

        A non-positive ``limit`` imports every product found in the requested
        collections. ``limit_per_collection`` can independently cap each page.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        image_dir = output_dir / "images"
        image_dir.mkdir(exist_ok=True)
        retrieved_at = datetime.now(tz=UTC).isoformat()
        entries: list[dict[str, Any]] = []
        seen_source_ids: set[str] = set()

        for collection in self.collections:
            if limit > 0 and len(entries) >= limit:
                break
            collection_url = urllib.parse.urljoin(self.base_url, f"/{collection}")
            logger.info("fetching_restricted_collection | collection=%s", collection)
            html = self._fetch_text(collection_url)
            products = self.parse_collection_page(html, collection)
            if self.limit_per_collection and self.limit_per_collection > 0:
                products = products[: self.limit_per_collection]

            for product in products:
                if limit > 0 and len(entries) >= limit:
                    break
                source_path = str(product["source_path"])
                source_id = source_path.strip("/") or re.sub(
                    r"\s+", "-", str(product["title"])
                )
                if source_id in seen_source_ids:
                    continue
                seen_source_ids.add(source_id)

                image_url = urllib.parse.urljoin(self.base_url, str(product["image_url"]))
                suffix = Path(urllib.parse.urlparse(image_url).path).suffix.lower()
                if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
                    suffix = ".jpg"
                safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", source_id).strip("-").lower()
                image_file = f"catalog_{safe_id}{suffix}"
                image_sha256 = ""
                download_status = "metadata_only"

                if not self.metadata_only:
                    try:
                        image_sha256 = self._download_image(image_url, image_dir / image_file)
                        download_status = "downloaded"
                    except (OSError, RuntimeError, urllib.error.URLError) as error:
                        logger.error("restricted_image_failed | sku=%s | error=%s", source_id, error)
                        download_status = "failed"
                        image_file = ""

                entry = {
                    "image_file": image_file,
                    "image_sha256": image_sha256,
                    "download_status": download_status,
                    "source_id": source_id,
                    "source_url": urllib.parse.urljoin(self.base_url, source_path),
                    "image_url": image_url,
                    "title": str(product["title"]),
                    "collection": str(product.get("collection") or collection),
                    "sizes_cm": list(product.get("sizes", [])),
                    "price_display": str(product.get("price_display", "")),
                    "description": str(product.get("description", "")),
                    "source_owner": "rights_holder",
                    "retrieved_at": retrieved_at,
                    "license": "all_rights_reserved",
                    "usage_scope": self.USAGE_SCOPE,
                    "training_use": self.training_use,
                    "commercial_use": self.commercial_use,
                    "permission_ref": self.permission_ref,
                    "status": self.dataset_status,
                    "caption": f"Company catalog {product.get('collection') or collection} {product['title']}",
                }
                entries.append(entry)
                logger.info(
                    "restricted_product_recorded | sku=%s | progress=%d", source_id, len(entries)
                )
                time.sleep(self.request_delay_seconds)
            time.sleep(self.request_delay_seconds)

        self._save_manifest(output_dir, entries, retrieved_at)
        return entries

    def _save_manifest(
        self, output_dir: Path, entries: list[dict[str, Any]], retrieved_at: str
    ) -> None:
        manifest = {
            "schema_version": 1,
            "dataset_id": "restricted_company_catalog_reference",
            "source_name": "Rights-restricted company product catalog",
            "source_url": self.base_url,
            "source_owner": "rights_holder",
            "retrieved_at": retrieved_at,
            "license": "all_rights_reserved",
            "usage_scope": self.USAGE_SCOPE,
            "training_use": self.training_use,
            "commercial_use": self.commercial_use,
            "permission_ref": self.permission_ref,
            "status": self.dataset_status,
            "item_count": len(entries),
            "collections": self.collections,
            "entries": entries,
        }
        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        csv_path = output_dir / "manifest.csv"
        columns = [
            "source_id",
            "title",
            "collection",
            "sizes_cm",
            "price_display",
            "source_url",
            "image_url",
            "image_file",
            "image_sha256",
            "download_status",
            "license",
            "usage_scope",
            "training_use",
            "commercial_use",
            "permission_ref",
            "status",
            "retrieved_at",
        ]
        with csv_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for entry in entries:
                row = dict(entry)
                row["sizes_cm"] = "|".join(entry["sizes_cm"])
                writer.writerow(row)

        logger.info("restricted_catalog_saved | items=%d | manifest=%s", len(entries), manifest_path)
