"""Detailed system diagnostics page."""

from __future__ import annotations

import streamlit as st

from carpet_designer.services.health_service import HealthService
from carpet_designer.ui.components import (
    apply_app_style,
    render_disclaimer,
    render_sidebar_brand,
    render_status_badge,
)

st.set_page_config(page_title="Sistem Sağlığı", page_icon="＋", layout="wide")
apply_app_style()
render_sidebar_brand("Sistem Sağlığı")

st.markdown(
    """
    <section class="hero"><div class="eyebrow">Operational Readiness</div>
    <h1>Sistem sağlığı</h1><p>Donanım, model kütüphaneleri, depolama ve SQLite
    bağlantısının canlı ön kontrolü.</p></section>
    """,
    unsafe_allow_html=True,
)

with st.spinner("Sistem kontrolleri çalışıyor..."):
    report = HealthService().check()

summary_top = st.columns(2)
summary_top[0].metric("Genel durum", report.overall_status.value)
summary_top[1].metric("PASS", sum(check.status.value == "PASS" for check in report.checks))
summary_bottom = st.columns(2)
summary_bottom[0].metric(
    "Kısıtlı",
    sum(check.status.value in {"BLOCKED", "HARDWARE_BLOCKED"} for check in report.checks),
)
summary_bottom[1].metric("FAIL", sum(check.status.value == "FAIL" for check in report.checks))

st.markdown("### Kontrol matrisi")
for check in report.checks:
    with st.expander(f"{render_status_badge(check.status)} · {check.name}"):
        st.write(check.detail)
        if check.value is not None:
            st.json(check.value)

st.success(
    "GPU veya SDXL ağırlığı bulunmasa bile CPU demo motoru, analiz, kalıcılık ve raporlama akışı çalışır."
)
render_disclaimer()
