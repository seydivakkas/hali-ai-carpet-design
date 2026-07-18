"""Reference-aware controlled variant generation page."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from carpet_designer.data.reference_image import (
    build_reference_guidance,
    fit_generation_size,
    store_reference_image,
)
from carpet_designer.domain.schemas import PromptRecipe
from carpet_designer.ui.components import (
    apply_app_style,
    get_design_service,
    render_disclaimer,
    render_palette_swatches,
    render_sidebar_brand,
)

st.set_page_config(page_title="Varyant Laboratuvarı", page_icon="▦", layout="wide")
apply_app_style()
render_sidebar_brand("Varyant Laboratuvarı")
service = get_design_service()
catalog = service.catalog()
taxonomy = catalog["taxonomy"]
palettes = catalog["palettes"]

available_loras = [
    item
    for item in service.list_loras()
    if item.get("status") in {"CANDIDATE", "VALIDATED", "ACTIVE_COMPANY_PILOT"}
    and Path(str(item.get("artifact_path", ""))).is_file()
]

st.markdown(
    """
    <section class="hero"><div class="eyebrow">Reference Variation</div>
    <h1>Varyant Laboratuvarı</h1><p>Bir halı görselini referans alın; değişmesine izin verdiğiniz
    stil, kompozisyon, palet, motif, bordür ve simetri alanlarını seçerek kontrollü alternatifler
    üretin.</p></section>
    """,
    unsafe_allow_html=True,
)

source_mode = st.radio(
    "Varyant kaynağı",
    ["Halı görseli yükle", "Sıfırdan reçete"],
    horizontal=True,
)
uploaded_reference = None
if source_mode == "Halı görseli yükle":
    upload_col, info_col = st.columns([0.62, 0.38], gap="large")
    uploaded_reference = upload_col.file_uploader(
        "Referans halı görseli",
        type=["png", "jpg", "jpeg", "webp"],
        help="PNG, JPEG veya WEBP · en az 64×64 px · en fazla 25 MB",
    )
    if uploaded_reference is not None:
        info_col.image(uploaded_reference, caption="Yüklenen referans", width=260)
    else:
        info_col.info("Ayarlar korunacak/değişecek alanları tanımlar; üretim için görsel yükleyin.")

has_reference = uploaded_reference is not None
style_entries = taxonomy.get("style_families", [])
style_labels = {entry["id"]: entry["label"] for entry in style_entries}

with st.form("variant_lab_form", border=True):
    st.markdown("#### Değişmesine izin verilen özellikler")
    target_columns = st.columns(7)
    change_style = target_columns[0].checkbox("Stil", value=True)
    change_composition = target_columns[1].checkbox("Kompozisyon", value=True)
    change_palette = target_columns[2].checkbox("Palet", value=True)
    change_motifs = target_columns[3].checkbox("Motifler", value=True)
    change_border = target_columns[4].checkbox("Bordür", value=True)
    change_symmetry = target_columns[5].checkbox("Simetri", value=True)
    change_resolution = target_columns[6].checkbox("Çözünürlük", value=False)

    left, right = st.columns(2, gap="large")
    with left:
        style = st.selectbox(
            "Stil ailesi",
            list(style_labels),
            format_func=lambda value: style_labels[value],
            disabled=has_reference and not change_style,
        )
        composition = st.selectbox(
            "Kompozisyon",
            taxonomy.get("compositions", []),
            disabled=has_reference and not change_composition,
        )
        motifs = st.multiselect(
            "Motifler",
            taxonomy.get("motif_families", []),
            default=["diamond", "rosette", "hook"],
            max_selections=5,
            disabled=has_reference and not change_motifs,
        )
        border = st.selectbox(
            "Bordür yapısı",
            taxonomy.get("border_structures", []),
            disabled=has_reference and not change_border,
        )
    with right:
        palette_id = st.selectbox(
            "Renk paleti",
            list(palettes),
            disabled=has_reference and not change_palette,
        )
        render_palette_swatches(palettes[palette_id]["colors"])
        symmetry = st.selectbox(
            "Simetri niyeti",
            taxonomy.get("symmetry_types", []),
            index=1,
            disabled=has_reference and not change_symmetry,
        )
        resolution = st.select_slider(
            "Hedef uzun kenar",
            options=[512, 640, 768, 1024],
            value=768,
            disabled=has_reference and not change_resolution,
        )
        preserve_aspect_ratio = st.checkbox(
            "Kaynak en-boy oranını koru",
            value=True,
            disabled=not has_reference,
        )

    control_left, control_mid, control_right = st.columns(3)
    count = control_left.slider("Varyant sayısı", 2, 6, 4)
    seed = control_mid.number_input("Başlangıç seed", min_value=0, value=120)
    variation_strength = control_right.slider(
        "Değişim gücü",
        0.05,
        0.95,
        0.45,
        0.05,
        disabled=not has_reference,
        help="Düşük değer kaynağı daha sıkı korur; yüksek değer seçili ayarları güçlendirir.",
    )

    engine_options = ["CPU Demo", "SDXL"]
    if available_loras:
        engine_options.append("SDXL + Carpet LoRA")
    engine = st.radio("Üretim motoru", engine_options, horizontal=True)
    selected_lora = available_loras[0] if available_loras else None
    lora_scale = 0.8
    if engine == "SDXL + Carpet LoRA" and available_loras:
        lora_col, scale_col = st.columns([0.7, 0.3])
        selected_lora = lora_col.selectbox(
            "LoRA adaptörü",
            available_loras,
            format_func=lambda item: (
                f"Carpet LoRA · rank {item['rank']} · {item['status']} · "
                f"{str(item['lora_id'])[:12]}"
            ),
        )
        lora_scale = scale_col.slider("LoRA etkisi", 0.1, 1.5, 0.8, 0.05)

    design_note = st.text_area(
        "Ek tasarım notu",
        placeholder="Örn. merkez alanı ferah tut, bordürü daha ince yorumla...",
    )
    submitted = st.form_submit_button(
        "Kontrollü varyant setini üret",
        type="primary",
        use_container_width=True,
    )

if submitted:
    if source_mode == "Halı görseli yükle" and uploaded_reference is None:
        st.error("Referans varyantları için önce bir halı görseli yükleyin.")
    else:
        variation_targets = [
            target
            for target, enabled in (
                ("style", change_style),
                ("composition", change_composition),
                ("palette", change_palette),
                ("motifs", change_motifs),
                ("border", change_border),
                ("symmetry", change_symmetry),
                ("resolution", change_resolution),
            )
            if enabled
        ]
        try:
            stored_reference = None
            if uploaded_reference is not None:
                stored_reference = store_reference_image(
                    uploaded_reference.getvalue(),
                    service.settings.resolved_artifacts_dir / "reference_uploads",
                )

            if stored_reference is not None:
                target_edge = int(resolution) if change_resolution else min(
                    1024, max(stored_reference.width, stored_reference.height)
                )
                width, height = fit_generation_size(
                    stored_reference.width,
                    stored_reference.height,
                    target_edge,
                    preserve_aspect_ratio=preserve_aspect_ratio,
                )
                guidance = build_reference_guidance(variation_targets)
                free_text = f"{guidance}. {design_note}" if design_note else guidance
                reference_palette = stored_reference.palette if not change_palette else []
            else:
                width = height = int(resolution)
                free_text = design_note
                reference_palette = []

            use_lora = engine == "SDXL + Carpet LoRA" and selected_lora is not None
            selected_lora_id = (
                str(selected_lora["lora_id"])
                if use_lora and selected_lora is not None
                else ""
            )
            if use_lora:
                free_text = f"mrcpt, {free_text}" if free_text else "mrcpt"
            recipe = PromptRecipe(
                style_family=style if change_style or stored_reference is None else "",
                motifs=motifs if change_motifs or stored_reference is None else [],
                composition=(
                    composition if change_composition or stored_reference is None else ""
                ),
                border=border if change_border or stored_reference is None else "",
                symmetry=symmetry if change_symmetry or stored_reference is None else "",
                palette_id=palette_id if change_palette or stored_reference is None else "",
                free_text=free_text,
                seed=int(seed),
                width=width,
                height=height,
                model_id="demo-procedural-v1" if engine == "CPU Demo" else "sdxl_base_v1",
                lora_ids=[selected_lora_id] if selected_lora_id else [],
                lora_scales=[float(lora_scale)] if use_lora else [],
                reference_image_path=(
                    str(stored_reference.path) if stored_reference is not None else ""
                ),
                reference_image_sha256=(
                    stored_reference.sha256 if stored_reference is not None else ""
                ),
                reference_palette=reference_palette,
                variation_strength=float(variation_strength) if stored_reference is not None else 0.45,
                variation_targets=variation_targets,
            )
            with st.spinner(f"{count} kontrollü varyant uçtan uca işleniyor..."):
                st.session_state["batch_runs"] = service.generate_batch(recipe, count)
                st.session_state["batch_reference"] = (
                    {
                        "path": str(stored_reference.path),
                        "sha256": stored_reference.sha256,
                        "palette": stored_reference.palette,
                        "targets": variation_targets,
                    }
                    if stored_reference is not None
                    else None
                )
        except Exception as exc:
            st.error(f"Varyant üretimi tamamlanamadı: {exc}")

runs = st.session_state.get("batch_runs", [])
reference_state = st.session_state.get("batch_reference")
if runs:
    st.markdown("### Karşılaştırma panosu")
    if isinstance(reference_state, dict) and reference_state.get("path"):
        reference_col, summary_col = st.columns([0.34, 0.66], gap="large")
        reference_col.image(reference_state["path"], caption="Referans halı", width=320)
        summary_col.markdown("#### Uygulanan değişim sözleşmesi")
        summary_col.write(
            ", ".join(reference_state.get("targets", [])) or "Yalnızca seed yüzey ayrıntıları"
        )
        summary_col.caption(f"Referans SHA-256: {reference_state.get('sha256', '')}")
        render_palette_swatches(reference_state.get("palette", []))

    columns = st.columns(2)
    for index, run in enumerate(runs):
        with columns[index % 2]:
            st.image(run.generation.image_path)
            st.markdown(f"**Seed {run.generation.seed}** · {run.generation.generation_id}")
            st.caption(
                f"{run.recipe.width}×{run.recipe.height} · "
                f"değişim gücü {run.recipe.variation_strength:.2f}"
            )
            metrics = st.columns(3)
            metrics[0].metric(
                "Simetri", f"{run.analysis.symmetry.central_alignment_score:.0%}"
            )
            metrics[1].metric("Seam", f"{run.analysis.seam.overall_score:.0%}")
            metrics[2].metric(
                "Tekrar", f"{run.analysis.repeatability.periodicity_score:.0%}"
            )

render_disclaimer()
