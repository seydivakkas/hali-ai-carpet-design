"""Retrieval index manager using FAISS per spec Section 18."""

from __future__ import annotations

import json

import numpy as np
from PIL import Image

try:
    import faiss

    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from typing import TYPE_CHECKING

from carpet_designer.logging_config import get_logger

if TYPE_CHECKING:
    from pathlib import Path

    from carpet_designer.domain.schemas import DatasetManifest

logger = get_logger("retrieval.index")

# Assume 512-dim embedding for CLIP
EMBEDDING_DIM = 512


def _get_dummy_embedding(image: Image.Image) -> np.ndarray:
    """Generate a dummy deterministic embedding based on image hash."""
    import hashlib

    img_data = image.tobytes()
    hash_obj = hashlib.md5(img_data)
    seed = int(hash_obj.hexdigest()[:8], 16)

    rng = np.random.default_rng(seed)
    emb = rng.standard_normal(EMBEDDING_DIM, dtype=np.float32)
    # Normalize
    norm = np.linalg.norm(emb)
    return emb / norm


class IndexManager:
    """Manages FAISS index for design retrieval."""

    def __init__(self, index_dir: Path) -> None:
        """Initialize IndexManager.

        Args:
            index_dir: Directory to save/load index artifacts.
        """
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.index_dir / "collection.index"
        self.metadata_path = self.index_dir / "metadata.json"

        self.index: faiss.Index | None = None
        self.metadata: list[str] = []

    def load(self) -> None:
        """Load index and metadata from disk."""
        if not FAISS_AVAILABLE:
            raise RuntimeError("faiss-cpu is not installed")

        if self.index_path.exists() and self.metadata_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            self.metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            logger.info("Loaded index with %d entries", self.index.ntotal)
        else:
            self.index = faiss.IndexFlatIP(EMBEDDING_DIM)
            self.metadata = []
            logger.info("Initialized empty FAISS index (Inner Product)")

    def build_from_manifest(self, manifest: DatasetManifest, image_dir: Path) -> None:
        """Build FAISS index from a DatasetManifest.

        Args:
            manifest: The manifest containing files to index.
            image_dir: Base directory for the images.
        """
        if self.index is None:
            self.load()

        index = self.index
        if index is None:
            raise RuntimeError("FAISS index failed to initialize")

        embeddings = []
        paths = []

        for file in manifest.files:
            img_path = image_dir / file.relative_path
            if not img_path.exists():
                logger.warning("Image not found: %s", img_path)
                continue

            try:
                img = Image.open(img_path).convert("RGB")
                emb = _get_dummy_embedding(img)
                embeddings.append(emb)
                paths.append(file.relative_path)
            except Exception as e:
                logger.error("Failed to embed %s: %s", img_path, e)

        if embeddings:
            emb_matrix = np.vstack(embeddings)
            index.add(emb_matrix)
            self.metadata.extend(paths)

            # Save
            faiss.write_index(index, str(self.index_path))
            self.metadata_path.write_text(json.dumps(self.metadata, indent=2), encoding="utf-8")
            logger.info("Added %d items to index and saved to %s", len(embeddings), self.index_path)

    def search(self, query_image: Image.Image, top_k: int = 5) -> list[dict[str, str | float]]:
        """Search the index.

        Args:
            query_image: Query PIL Image.
            top_k: Number of results.

        Returns:
            List of dicts containing 'path' and 'score'.
        """
        if self.index is None:
            self.load()

        index = self.index
        if index is None:
            raise RuntimeError("FAISS index failed to initialize")

        if index.ntotal == 0:
            logger.warning("Index is empty")
            return []

        q_emb = _get_dummy_embedding(query_image)
        q_matrix = np.expand_dims(q_emb, axis=0)

        distances, indices = index.search(q_matrix, min(top_k, index.ntotal))

        results = []
        for dist, idx in zip(distances[0], indices[0], strict=False):
            if idx != -1:
                results.append({"path": self.metadata[idx], "score": float(dist)})

        return results
