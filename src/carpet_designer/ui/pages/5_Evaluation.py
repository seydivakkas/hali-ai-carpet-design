"""Operational evaluation and evidence page."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from carpet_designer.ui.components import (
    apply_app_style,
    get_design_service,
    render_disclaimer,
    render_sidebar_brand,
)

st.set_page_config(page_title="Değerlendirme", page_icon="▥", layout="wide")
apply_app_style()
render_sidebar_brand("Değerlendirme")
service = get_design_service()
stats = service.dashboard_stats()

st.markdown(
    """
    <section class="hero"><div class="eyebrow">Evidence Dashboard</div>
    <h1>Değerlendirme ve kanıt merkezi</h1><p>Koşu sağlığı, geometri metrikleri ve
    dışa aktarılmış kanıt paketlerini sunum öncesinde tek ekrandan denetleyin.</p></section>
    """,
    unsafe_allow_html=True,
)

metrics_top = st.columns(2)
metrics_top[0].metric("Koşu", int(stats["total"]))
metrics_top[1].metric("Başarılı", int(stats["passed"]))
metrics_bottom = st.columns(3)
metrics_bottom[0].metric("Ort. simetri", f"{float(stats['avg_symmetry']):.1%}")
metrics_bottom[1].metric("Ort. seam", f"{float(stats['avg_seam']):.1%}")
metrics_bottom[2].metric("Ort. süre", f"{float(stats['avg_latency_ms']):.0f} ms")

recent = service.list_recent(50)
st.markdown("### Son koşular")
if recent:
    table = [
        {
            "Koşu": item["generation_id"],
            "Model": item["model_id"],
            "Seed": item["seed"],
            "Boyut": f"{item['width']}×{item['height']}",
            "Süre (ms)": round(float(item["total_latency_ms"])),
            "Durum": item["status"],
        }
        for item in recent
    ]
    st.dataframe(table, use_container_width=True, hide_index=True)
else:
    st.info("Henüz değerlendirecek koşu yok.")

reports_dir = service.settings.resolved_artifacts_dir / "reports"
reports = sorted(reports_dir.glob("*.html"), key=lambda path: path.stat().st_mtime, reverse=True)
st.markdown("### Kanıt paketleri")
if reports:
    for report in reports[:10]:
        left, right = st.columns([0.75, 0.25])
        left.write(report.stem)
        right.download_button(
            "HTML indir",
            Path(report).read_bytes(),
            file_name=report.name,
            mime="text/html",
            key=f"report_{report.stem}",
            use_container_width=True,
        )
else:
    st.caption("Raporlar ilk üretimden sonra burada görünecek.")

render_disclaimer()
