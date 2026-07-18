"""Collection similarity search page."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
from PIL import Image

from carpet_designer.ui.components import (
    apply_app_style,
    get_design_service,
    render_disclaimer,
    render_sidebar_brand,
)

st.set_page_config(page_title="Koleksiyon Arama", page_icon="⌕", layout="wide")
apply_app_style()
render_sidebar_brand("Koleksiyon Arama")
service = get_design_service()

st.markdown(
    """
    <section class="hero"><div class="eyebrow">Visual Retrieval</div>
    <h1>Koleksiyonda yakın tasarım ara</h1><p>Bir görsel yükleyin veya geçmiş bir koşuyu seçin.
    Backend, tasarım geçmişi ile kısıtlı şirket katalog referanslarını normalize renk
    dağılımlarına göre birlikte sıralar.</p></section>
    """,
    unsafe_allow_html=True,
)

recent = [item for item in service.list_recent(50) if Path(str(item["image_path"])).exists()]
source = st.radio("Sorgu kaynağı", ["Geçmiş tasarım", "Görsel yükle"], horizontal=True)
query_image: Image.Image | None = None
if source == "Geçmiş tasarım":
    if recent:
        selected = st.selectbox(
            "Koşu",
            recent,
            format_func=lambda item: f"{item['generation_id']} · seed {item['seed']}",
        )
        query_image = Image.open(str(selected["image_path"])).convert("RGB")
    else:
        st.info("Arama yapabilmek için önce Tasarım Stüdyosu'nda bir tasarım üretin.")
else:
    upload = st.file_uploader("PNG veya JPG", type=["png", "jpg", "jpeg", "webp"])
    if upload is not None:
        query_image = Image.open(upload).convert("RGB")

if query_image is not None:
    preview, controls = st.columns([0.35, 0.65], gap="large")
    with preview:
        st.image(query_image, caption="Sorgu görseli")
    with controls:
        top_k = st.slider("Sonuç sayısı", 1, 12, 5)
        run_search = st.button("Benzer tasarımları bul", use_container_width=True)
    if run_search:
        st.session_state["search_matches"] = service.search_collection(query_image, top_k)

matches = st.session_state.get("search_matches", [])
if matches:
    st.markdown("### En yakın sonuçlar")
    columns = st.columns(3)
    for index, match in enumerate(matches):
        with columns[index % 3]:
            st.image(str(match["image_path"]))
            st.progress(float(match["score"]), text=f"Benzerlik · {float(match['score']):.1%}")
            if match.get("source_type") == "restricted_catalog_reference":
                collection = str(match.get("collection", "Katalog"))
                st.caption(f"{collection} · {match['generation_id']}")
                if match.get("training_use") == "approved":
                    st.caption("Şirket katalog verisi · eğitim izni kayıtlı")
                else:
                    st.caption("Kısıtlı katalog referansı · eğitim için kullanılamaz")
                if match.get("source_url"):
                    st.link_button("Ürün kaynağını aç", str(match["source_url"]))
            else:
                st.caption(f"Üretilen tasarım · {match['generation_id']}")

st.info(
    "Bu sıralama tasarım keşfi içindir; hukuki özgünlük veya telif güvenliği sonucu değildir.",
    icon="ℹ️",
)
render_disclaimer()
