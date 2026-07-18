"""Tests for the restricted company catalog adapter."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from carpet_designer.data.adapters.restricted_catalog import RestrictedCatalogAdapter

if TYPE_CHECKING:
    from pathlib import Path


COLLECTION_HTML = """
<div class="products-list__item">
  <div class="product-card product-card--hidden-actions" data-productid="abc-123">
    <div class="product-card__image product-image">
      <a class="product-image__body" href="/90823-070">
        <img class="product-image__img" src="https://cdn.example/90823-070_415.jpeg">
      </a>
    </div>
    <div class="input-radio-label__list"><label><input><span>80x150</span></label>
      <label><input><span>160 × 230</span></label></div>
    <div class="product-card__info">
      <div class="product-card__name"><div class="productList-categoryName"><span>Elegance</span></div>
        <a class="product-info-detail" href="/90823-070">90823 070</a></div>
      <div class="product-card__prices">₺4.639,14</div>
      <div class="product-card__description">Peşin satış fiyatıdır.</div>
    </div>
  </div>
</div>
"""


def test_parse_collection_product_metadata() -> None:
    products = RestrictedCatalogAdapter.parse_collection_page(COLLECTION_HTML, "Elegance")

    assert len(products) == 1
    assert products[0]["title"] == "90823 070"
    assert products[0]["collection"] == "Elegance"
    assert products[0]["source_path"] == "/90823-070"
    assert products[0]["sizes"] == ["80x150", "160x230"]
    assert products[0]["price_display"] == "₺4.639,14"


def test_manifest_blocks_training_without_permission(tmp_path: Path) -> None:
    class StubAdapter(RestrictedCatalogAdapter):
        def _fetch_text(self, url: str) -> str:
            return COLLECTION_HTML

    adapter = StubAdapter(
        collections=["Elegance"], metadata_only=True, request_delay_seconds=0
    )
    records = adapter.fetch_dataset(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))

    assert len(records) == 1
    assert records[0]["usage_scope"] == "internal_design_reference_only"
    assert records[0]["training_use"] == "blocked_pending_written_permission"
    assert manifest["status"] == "RESTRICTED_REFERENCE_ONLY"
    assert manifest["item_count"] == 1
    assert (tmp_path / "manifest.csv").is_file()


def test_written_permission_marks_manifest_training_approved(tmp_path: Path) -> None:
    class StubAdapter(RestrictedCatalogAdapter):
        def _fetch_text(self, url: str) -> str:
            return COLLECTION_HTML

    adapter = StubAdapter(
        collections=["Elegance"],
        metadata_only=True,
        request_delay_seconds=0,
        permission_ref="COMPANY-APPROVAL-001",
    )
    records = adapter.fetch_dataset(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))

    assert records[0]["training_use"] == "approved"
    assert records[0]["permission_ref"] == "COMPANY-APPROVAL-001"
    assert manifest["status"] == "TRAINING_APPROVED"
