"""Streamlit entry point for the Halı AI Carpet Design demo."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from carpet_designer.ui.components import (
    apply_app_style,
    get_design_service,
    render_disclaimer,
    render_sidebar_brand,
)

st.set_page_config(
    page_title="Halı AI Carpet Design",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    """Render the executive dashboard and recent design gallery."""
    apply_app_style()
    render_sidebar_brand("Yönetim Özeti")
    service = get_design_service()
    stats = service.dashboard_stats()

    st.markdown(
        """
        <section class="hero">
          <div class="eyebrow">Design Intelligence · Local First</div>
          <h1>Fikirden izlenebilir halı tasarımına.</h1>
          <p>Kontrollü tasarım reçetesi, deterministik üretim, dijital geometri analizi,
          koleksiyon araması ve kanıt raporu — tek bir yerel mühendislik akışında.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="status-strip">● Sistem çevrimiçi &nbsp;·&nbsp; '
        "SQLite kalıcılığı aktif &nbsp;·&nbsp; JSON / HTML kanıt raporu hazır</div>",
        unsafe_allow_html=True,
    )

    metrics_top = st.columns(2)
    metrics_top[0].metric("Toplam tasarım", int(stats["total"]))
    metrics_top[1].metric("Başarılı koşu", int(stats["passed"]))
    metrics_bottom = st.columns(2)
    metrics_bottom[0].metric("Ort. simetri", f"{float(stats['avg_symmetry']):.0%}")
    metrics_bottom[1].metric("Ort. seam", f"{float(stats['avg_seam']):.0%}")

    st.markdown("### Ürün akışı")
    flow = st.columns(2)
    flow_items = (
        ("01", "Reçete", "Stil, motif, palet, kompozisyon ve seed kontrolü"),
        ("02", "Üretim", "CPU demo motoru veya opsiyonel SDXL + LoRA"),
        ("03", "Analiz", "Renk, simetri, seam ve tekrar ölçümü"),
        ("04", "Kanıt", "SQLite kaydı ile PNG, JSON ve HTML raporu"),
    )
    for index, (number, title, body) in enumerate(flow_items):
        column = flow[index % 2]
        with column:
            st.caption(number)
            st.subheader(title)
            st.write(body)

    action, note = st.columns([0.4, 0.6], gap="large")
    with action:
        st.page_link("pages/1_Design_Studio.py", label="Tasarım Stüdyosunu Aç", icon="🎨")
        st.page_link("pages/2_Variant_Batch.py", label="Varyant Üret", icon="🧩")
    with note:
        st.info(
            "Mühendislik demosu model ağırlığı olmadan tamamen çalışır. "
            "Onaylı SDXL ağırlığı eklendiğinde aynı backend sözleşmesi gerçek diffusion motoruna geçer."
        )

    recent = [item for item in service.list_recent(6) if Path(str(item["image_path"])).exists()]
    if recent:
        st.markdown("### Son tasarımlar")
        gallery = st.columns(3)
        for index, item in enumerate(recent):
            with gallery[index % 3]:
                st.image(str(item["image_path"]))
                st.caption(f"{item['generation_id']} · seed {item['seed']}")
    else:
        st.markdown("### İlk tasarımı üretmeye hazır")
        st.write(
            "Stüdyo sayfasındaki örnek reçete ile birkaç saniye içinde ilk koşuyu oluşturabilirsiniz."
        )

    render_disclaimer()


if __name__ == "__main__":
    main()
