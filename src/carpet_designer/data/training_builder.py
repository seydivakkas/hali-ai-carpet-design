"""Build a governed, deduplicated image set for carpet-domain LoRA training."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from PIL import Image, ImageOps

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class TrainingCandidate:
    """A source image plus its governed training metadata."""

    path: Path
    source: str
    source_id: str
    source_url: str
    license: str
    permission_ref: str
    caption: str
    style_labels: tuple[str, ...] = ()


class TrainingDatasetBuilder:
    """Merge an approved company catalog with open and public-domain sources."""

    CARPET_KEYWORDS = re.compile(r"carpet|rug|kilim|textile|tapestry", re.IGNORECASE)
    KAGGLE_SOURCE_URL = (
        "https://www.kaggle.com/datasets/mahdisarbazi/"
        "safavid-dynasty-iranian-carpet-dataset"
    )

    def __init__(
        self,
        *,
        restricted_catalog_dir: Path,
        kaggle_dir: Path,
        met_dir: Path,
        canvas_size: int = 768,
    ) -> None:
        self.restricted_catalog_dir = restricted_catalog_dir
        self.kaggle_dir = kaggle_dir
        self.met_dir = met_dir
        self.canvas_size = canvas_size

    def build(self, output_dir: Path) -> dict[str, Any]:
        """Create normalized JPEGs, captions and an auditable manifest."""
        image_dir = output_dir / "images"
        image_dir.mkdir(parents=True, exist_ok=True)
        candidates = [
            *self._collect_restricted_catalog(),
            *self._collect_kaggle(),
            *self._collect_met(),
        ]

        files: list[dict[str, Any]] = []
        metadata_lines: list[str] = []
        seen_hashes: set[str] = set()
        source_counts: dict[str, int] = {}
        excluded_duplicates = 0
        excluded_invalid = 0
        generated_file_names: set[str] = set()

        for candidate in candidates:
            try:
                payload_hash = hashlib.sha256(candidate.path.read_bytes()).hexdigest()
                if payload_hash in seen_hashes:
                    excluded_duplicates += 1
                    continue
                seen_hashes.add(payload_hash)
                with Image.open(candidate.path) as source_image:
                    image = ImageOps.exif_transpose(source_image).convert("RGB")
                    normalized = ImageOps.pad(
                        image,
                        (self.canvas_size, self.canvas_size),
                        method=Image.Resampling.LANCZOS,
                        color=(238, 235, 228),
                        centering=(0.5, 0.5),
                    )
            except (OSError, ValueError):
                excluded_invalid += 1
                continue

            safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", candidate.source_id).strip("-")
            file_name = f"{candidate.source}_{safe_id}.jpg".lower()
            destination = image_dir / file_name
            normalized.save(destination, format="JPEG", quality=92, optimize=True)
            generated_file_names.add(file_name)
            output_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
            source_counts[candidate.source] = source_counts.get(candidate.source, 0) + 1
            metadata_lines.append(
                json.dumps(
                    {"file_name": f"images/{file_name}", "text": candidate.caption},
                    ensure_ascii=False,
                )
            )
            files.append(
                {
                    "relative_path": f"images/{file_name}",
                    "sha256": output_hash,
                    "source_object_id": candidate.source_id,
                    "source_url": candidate.source_url,
                    "license": candidate.license,
                    "width": self.canvas_size,
                    "height": self.canvas_size,
                    "caption_path": "metadata.jsonl",
                    "style_labels": list(candidate.style_labels),
                    "palette_labels": [],
                    "split": "train",
                    "source": candidate.source,
                    "permission_ref": candidate.permission_ref,
                    "caption": candidate.caption,
                }
            )

        stale_images = [
            path for path in image_dir.glob("*.jpg") if path.name not in generated_file_names
        ]
        for stale_image in stale_images:
            stale_image.unlink()

        (output_dir / "metadata.jsonl").write_text(
            "\n".join(metadata_lines) + "\n", encoding="utf-8"
        )
        manifest = {
            "schema_version": "1.0.0",
            "dataset_id": "carpet_lora_v1",
            "created_at": datetime.now(tz=UTC).isoformat(),
            "training_use": "approved",
            "permission_ref": "MULTI_SOURCE_LICENSE_REGISTER_2026-07-18",
            "status": "TRAINING_APPROVED",
            "source": {
                "restricted_catalog": "rights-holder-approved catalog snapshot",
                "kaggle_safavid": "MIT-licensed Kaggle dataset; original images only",
                "met": "Metropolitan Museum of Art Open Access public-domain records",
            },
            "counts": {
                "total": len(files),
                "train": len(files),
                "excluded_duplicates": excluded_duplicates,
                "excluded_invalid": excluded_invalid,
                "stale_images_removed": len(stale_images),
                **source_counts,
            },
            "files": files,
            "manifest_sha256": "",
        }
        entry_hash = hashlib.sha256(
            json.dumps(files, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        manifest["manifest_sha256"] = entry_hash
        (output_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (output_dir / "ATTRIBUTION.md").write_text(
            "# Training dataset attribution\n\n"
            "- Restricted company catalog: rights-holder training permission recorded as "
            "`USER_ATTESTED_WRITTEN_PERMISSION_2026-07-18`.\n"
            f"- Safavid carpet dataset: MIT license, {self.KAGGLE_SOURCE_URL}\n"
            "- The Metropolitan Museum of Art: Open Access, public domain.\n",
            encoding="utf-8",
        )
        return manifest

    def _collect_restricted_catalog(self) -> list[TrainingCandidate]:
        manifest_path = self.restricted_catalog_dir / "manifest.json"
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if payload.get("training_use") != "approved" or not payload.get("permission_ref"):
            raise PermissionError("Company catalog training permission is not recorded.")
        permission_ref = str(payload["permission_ref"])
        candidates: list[TrainingCandidate] = []
        for item in payload.get("entries", []):
            image_file = str(item.get("image_file", ""))
            path = self.restricted_catalog_dir / "images" / image_file
            if not image_file or not path.is_file():
                continue
            collection = str(item.get("collection", "Company catalog"))
            title = str(item.get("title", item.get("source_id", "carpet")))
            candidates.append(
                TrainingCandidate(
                    path=path,
                    source="restricted_catalog",
                    source_id=str(item.get("source_id", path.stem)),
                    source_url=str(item.get("source_url", "")),
                    license="company_training_permission",
                    permission_ref=permission_ref,
                    caption=(
                        f"a mrcpt company carpet design, {collection} collection, product {title}, "
                        "full rug view, detailed textile pattern"
                    ),
                    style_labels=("company_catalog", collection),
                )
            )
        return candidates

    def _collect_kaggle(self) -> list[TrainingCandidate]:
        candidates: list[TrainingCandidate] = []
        image_paths = sorted(
            path
            for path in self.kaggle_dir.rglob("*")
            if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        )
        for path in image_paths:
            stem = path.stem.strip()
            if not re.fullmatch(r"\d+", stem):
                continue  # Exclude gray/Laplacian/Gabor augmented variants.
            candidates.append(
                TrainingCandidate(
                    path=path,
                    source="kaggle_safavid",
                    source_id=stem,
                    source_url=self.KAGGLE_SOURCE_URL,
                    license="MIT",
                    permission_ref="KAGGLE_DATASET_LICENSE_MIT",
                    caption=(
                        "a mrcpt historic Safavid Persian carpet, full rug view, ornate symmetric "
                        "textile pattern, museum collection"
                    ),
                    style_labels=("safavid", "persian", "historic"),
                )
            )
        if not candidates:
            raise FileNotFoundError(f"No original Safavid images found under {self.kaggle_dir}")
        return candidates

    def _collect_met(self) -> list[TrainingCandidate]:
        manifest_path = self.met_dir / "manifest.json"
        entries = json.loads(manifest_path.read_text(encoding="utf-8"))
        candidates: list[TrainingCandidate] = []
        for item in entries:
            searchable = " ".join(
                str(item.get(key, "")) for key in ("title", "caption", "medium")
            )
            if not self.CARPET_KEYWORDS.search(searchable):
                continue
            image_file = str(item.get("image_file", ""))
            path = self.met_dir / "images" / image_file
            if not image_file or not path.is_file():
                continue
            title = str(item.get("title") or "historic carpet")
            culture = str(item.get("culture") or "museum")
            candidates.append(
                TrainingCandidate(
                    path=path,
                    source="met",
                    source_id=str(item.get("source_id", path.stem)),
                    source_url=str(item.get("source_url", "")),
                    license="public_domain",
                    permission_ref="MET_OPEN_ACCESS_PUBLIC_DOMAIN",
                    caption=(
                        f"a mrcpt historic carpet or textile, {title}, {culture}, full pattern view"
                    ),
                    style_labels=("museum", "historic"),
                )
            )
        return candidates
