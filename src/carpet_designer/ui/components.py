"""Shared UI components for Streamlit pages."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import streamlit as st

from carpet_designer.domain.enums import Status
from carpet_designer.services.design_service import DesignService

if TYPE_CHECKING:
    from carpet_designer.domain.schemas import DesignRunResult


@st.cache_resource(show_spinner=False)
def get_design_service() -> DesignService:
    """Return the shared backend facade for the current Streamlit process."""
    return DesignService()


def apply_app_style() -> None:
    """Apply the presentation theme shared by all application pages."""
    st.markdown(
        """
        <style>
        :root { --brand-red:#8f1d2c; --brand-gold:#c3a15b; --ink:#17221c; }
        .stApp { background:
            radial-gradient(circle at 85% 0%, rgba(195,161,91,.10), transparent 28rem),
            linear-gradient(180deg, #f8f6f1 0%, #f2efe8 100%); }
        [data-testid="stMainBlockContainer"] { width:100%; max-width:100%; padding-left:2rem; padding-right:2rem; }
        [data-testid="stAppViewContainer"] { color:var(--ink); }
        [data-testid="stSidebar"] { background:#152019; border-right:1px solid #2e3b32; }
        [data-testid="stSidebar"] * { color:#f6f1e7; }
        h1,h2,h3 { letter-spacing:-.02em; color:var(--ink); }
        .hero { padding:1.8rem 2rem; border-radius:24px; color:white;
            background:linear-gradient(120deg,#731724,#9e2938 58%,#3d211d); margin-bottom:1.5rem;
            box-shadow:0 18px 50px rgba(69,23,29,.18); }
        .hero h1 { color:white; margin:0 0 .45rem; font-size:2.45rem; }
        .hero p { color:#f3ddd9; margin:0; max-width:780px; font-size:1.02rem; }
        .eyebrow { text-transform:uppercase; letter-spacing:.16em; font-size:.7rem;
            color:#e2c483; font-weight:800; margin-bottom:.5rem; }
        .status-strip { padding:.75rem 1rem; border:1px solid #ddd7ca; background:#fffdf8;
            border-radius:13px; color:#526056; font-size:.86rem; margin-bottom:1rem; }
        div[data-testid="stMetric"] { background:#fffdf9; border:1px solid #e1dbcf;
            padding:1rem 1.1rem; border-radius:16px; box-shadow:0 5px 18px rgba(37,48,40,.05); }
        [data-testid="stMetricValue"] { color:#7f1d2b; }
        [data-testid="stMetricLabel"] { color:#4f5b53; }
        div[data-testid="stForm"] { background:#fffdf9; border:1px solid #e1dbcf;
            padding:1rem; border-radius:18px; }
        .swatch-row { display:flex; gap:.6rem; flex-wrap:wrap; margin:.5rem 0 1rem; }
        .swatch { width:76px; font-size:.7rem; color:#566159; }
        .swatch i { display:block; height:38px; border-radius:8px; border:1px solid #0001; }
        .disclaimer { border-left:4px solid #c3a15b; background:#fff9eb; padding:.8rem 1rem;
            border-radius:0 10px 10px 0; color:#61563c; font-size:.82rem; }
        .stButton>button, .stDownloadButton>button { border-radius:10px; font-weight:700; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand(active: str) -> None:
    """Render product identity and execution mode in the sidebar."""
    with st.sidebar:
        st.markdown("## HALI · AI")
        st.caption("Carpet Design Studio")
        st.markdown(f"**{active}**")
        st.markdown("---")
        st.markdown("🟢 Backend servisi hazır")
        st.caption("Varsayılan: CPU uyumlu prosedürel demo motoru")


def render_palette_swatches(colors: list[str]) -> None:
    """Render color chips without requiring a charting dependency."""
    swatches = "".join(
        f'<span class="swatch"><i style="background:{color}"></i>{color.upper()}</span>'
        for color in colors
    )
    st.markdown(f'<div class="swatch-row">{swatches}</div>', unsafe_allow_html=True)


def render_design_run(run: DesignRunResult) -> None:
    """Render a complete generated-design result with metrics and downloads."""
    generation = run.generation
    analysis = run.analysis
    left, right = st.columns([1.25, 0.75], gap="large")
    with left:
        st.image(generation.image_path, caption=f"Koşu · {generation.generation_id}")
    with right:
        st.subheader("Dijital tasarım analizi")
        col1, col2 = st.columns(2)
        col1.metric("Simetri", f"{analysis.symmetry.central_alignment_score:.0%}")
        col2.metric("Seam", f"{analysis.seam.overall_score:.0%}")
        col1.metric("Tekrar", f"{analysis.repeatability.periodicity_score:.0%}")
        col2.metric("Palet kapsamı", f"{analysis.color.coverage_ratio:.0%}")
        render_palette_swatches([item.hex for item in analysis.color.dominant_colors])
        st.caption(
            f"Motor: {run.engine_mode} · Seed: {generation.seed} · "
            f"Süre: {generation.timing.total_ms:.0f} ms"
        )
        if generation.warnings:
            st.warning("\n".join(generation.warnings))

    with st.expander("Prompt reçetesi ve izlenebilirlik"):
        st.code(run.positive_prompt, language=None)
        st.caption(f"Image SHA-256: {generation.image_sha256}")

    downloads = st.columns(3)
    downloads[0].download_button(
        "PNG indir",
        data=Path(generation.image_path).read_bytes(),
        file_name=Path(generation.image_path).name,
        mime="image/png",
        use_container_width=True,
    )
    downloads[1].download_button(
        "JSON raporu",
        data=Path(run.json_report_path).read_bytes(),
        file_name=Path(run.json_report_path).name,
        mime="application/json",
        use_container_width=True,
    )
    downloads[2].download_button(
        "HTML raporu",
        data=Path(run.html_report_path).read_bytes(),
        file_name=Path(run.html_report_path).name,
        mime="text/html",
        use_container_width=True,
    )


def render_status_badge(status: Status) -> str:
    """Render a colored status badge.

    Args:
        status: The status to render.

    Returns:
        Emoji + status text string.
    """
    badges = {
        Status.PASS: "✅ PASS",
        Status.FAIL: "❌ FAIL",
        Status.BLOCKED: "⚠️ BLOCKED",
        Status.HARDWARE_BLOCKED: "⚠️ HW_BLOCKED",
        Status.NOT_RUN: "⏸️ NOT_RUN",
        Status.PASS_WITH_RESTRICTIONS: "🔹 RESTRICTED",
        Status.DEMO_ONLY: "🔸 DEMO_ONLY",
        Status.LICENSE_BLOCKED: "🚫 LICENSE_BLOCKED",
    }
    return badges.get(status, str(status))


def render_disclaimer() -> None:
    """Render the standard disclaimer footer."""
    st.markdown("---")
    st.caption(
        "⚠️ Generated designs are not production-approved. "
        "Retrieval does not establish legal originality. "
        "This system does not claim manufacturability, "
        "originality or copyright safety without external evidence."
    )


def render_model_status(model_available: bool, lora_available: bool) -> None:
    """Render model availability status in sidebar.

    Args:
        model_available: Whether base model is loaded.
        lora_available: Whether LoRA adapter is loaded.
    """
    with st.sidebar:
        st.markdown("### Model Status")
        if model_available:
            st.success("Base model loaded")
        else:
            st.warning("No base model — generation disabled")
        if lora_available:
            st.info("LoRA adapter active")
        else:
            st.caption("No LoRA adapter (BASE_MODEL_DEMO)")
