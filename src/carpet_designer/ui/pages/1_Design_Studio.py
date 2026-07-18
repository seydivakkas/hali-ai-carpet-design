"""Interactive controlled design generation page."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from carpet_designer.domain.schemas import PromptRecipe
from carpet_designer.ui.components import (
    apply_app_style,
    get_design_service,
    render_design_run,
    render_disclaimer,
    render_palette_swatches,
    render_sidebar_brand,
)
from carpet_designer.ui.state import init_state

st.set_page_config(page_title="Tasarım Stüdyosu", page_icon="🎨", layout="wide")
apply_app_style()
render_sidebar_brand("Tasarım Stüdyosu")
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
status_priority = {"ACTIVE_COMPANY_PILOT": 0, "VALIDATED": 1, "CANDIDATE": 2}
available_loras.sort(
    key=lambda item: (
        status_priority.get(str(item.get("status")), 9),
        str(item.get("training_run_id", "")),
    )
)
available_lora_by_id = {str(item["lora_id"]): item for item in available_loras}

st.markdown(
    """
    <section class="hero"><div class="eyebrow">Controlled Generation</div>
    <h1>Tasarım Stüdyosu</h1>
    <p>Halı tasarım niyetini yapılandırılmış bir reçeteye dönüştürün; aynı seed ile
    tekrar üretilebilen, ölçülmüş ve raporlanmış bir tasarım alın.</p></section>
    """,
    unsafe_allow_html=True,
)

style_entries = taxonomy.get("style_families", [])
style_labels = {entry["id"]: entry["label"] for entry in style_entries}
motifs = taxonomy.get("motif_families", [])
compositions = taxonomy.get("compositions", [])
borders = taxonomy.get("border_structures", [])
symmetries = taxonomy.get("symmetry_types", [])

engine_options = ["CPU Demo", "SDXL"]
if available_loras:
    engine_options.append("SDXL + Carpet LoRA")
engine = st.radio(
    "Üretim motoru",
    engine_options,
    horizontal=True,
    help="SDXL modları RTX 4070 üzerinde model CPU offload ile çalışır.",
)
selected_lora_ids: list[str] = []
lora_scales_by_id: dict[str, float] = {}

with st.form("design_recipe", border=True):
    left, right = st.columns(2, gap="large")
    with left:
        style = st.selectbox(
            "Stil ailesi",
            list(style_labels),
            format_func=lambda value: style_labels[value],
        )
        selected_motifs = st.multiselect(
            "Motifler",
            motifs,
            default=["diamond", "star", "ram_horn"],
            max_selections=5,
        )
        composition = st.selectbox("Kompozisyon", compositions, index=0)
    with right:
        palette_id = st.selectbox("Renk paleti", list(palettes))
        render_palette_swatches(palettes[palette_id]["colors"])
        border = st.selectbox("Bordür", borders, index=0)
        symmetry = st.selectbox("Simetri niyeti", symmetries, index=1)
        if engine == "SDXL + Carpet LoRA" and available_loras:
            selected_lora_ids = st.multiselect(
                "Hibrit LoRA bileşenleri",
                options=list(available_lora_by_id),
                default=[str(available_loras[0]["lora_id"])],
                max_selections=3,
                format_func=lambda lora_id: (
                    f"Carpet LoRA · rank {available_lora_by_id[lora_id]['rank']} · "
                    f"{available_lora_by_id[lora_id]['status']} · {lora_id[:12]}"
                ),
                help="En fazla üç adaptörü ayrı etkilerle aynı üretimde hibritleyebilirsiniz.",
            )
            for index, lora_id in enumerate(selected_lora_ids):
                lora = available_lora_by_id[lora_id]
                lora_scales_by_id[lora_id] = st.slider(
                    f"{index + 1}. bileşen etkisi · {lora_id[:12]}",
                    0.0,
                    1.5,
                    0.8 if index == 0 else 0.4,
                    0.05,
                    key=f"lora_scale_{lora_id}",
                    help=f"Eğitim koşusu: {lora.get('training_run_id', '—')}",
                )
            total_scale = sum(lora_scales_by_id.values())
            if selected_lora_ids:
                mix_rows = []
                for index, lora_id in enumerate(selected_lora_ids):
                    lora = available_lora_by_id[lora_id]
                    scale = lora_scales_by_id[lora_id]
                    mix_rows.append(
                        {
                            "Bileşen": f"Carpet LoRA {index + 1}",
                            "LoRA ID": lora_id,
                            "Eğitim koşusu": lora.get("training_run_id", ""),
                            "Etki": scale,
                            "Hibrit payı": (
                                f"{scale / total_scale:.0%}" if total_scale > 0 else "0%"
                            ),
                        }
                    )
                st.dataframe(mix_rows, use_container_width=True, hide_index=True)
                st.caption(
                    "Üretimde **Etki** değerleri kullanılır; hibrit payı oranların okunabilir "
                    "normalize edilmiş karşılığıdır."
                )
        seed = st.number_input("Deterministik seed", 0, 2_147_483_647, 42)
        resolution = st.select_slider("Çözünürlük", options=[512, 640, 768, 1024], value=768)
    free_text = st.text_area(
        "Tasarım notu",
        placeholder="Örn. daha ferah negatif alan, güçlü lacivert merkez...",
    )
    submitted = st.form_submit_button("Tasarımı üret ve analiz et", use_container_width=True)

if submitted:
    use_lora = engine == "SDXL + Carpet LoRA" and bool(selected_lora_ids)
    selected_scales = [lora_scales_by_id[lora_id] for lora_id in selected_lora_ids]
    lora_free_text = f"mrcpt, {free_text}" if free_text else "mrcpt"
    if use_lora and sum(selected_scales) <= 0:
        st.error("Hibrit LoRA bileşenlerinden en az birinin etkisi sıfırdan büyük olmalı.")
    else:
        recipe = PromptRecipe(
            style_family=style,
            motifs=selected_motifs,
            composition=composition,
            border=border,
            symmetry=symmetry,
            palette_id=palette_id,
            free_text=lora_free_text if use_lora else free_text,
            seed=int(seed),
            width=resolution,
            height=resolution,
            model_id="demo-procedural-v1" if engine == "CPU Demo" else "sdxl_base_v1",
            lora_ids=selected_lora_ids if use_lora else [],
            lora_scales=[float(scale) for scale in selected_scales] if use_lora else [],
        )
        try:
            with st.spinner("Tasarım üretiliyor, analiz ediliyor ve raporlanıyor..."):
                st.session_state["latest_design_run"] = service.generate_design(recipe)
        except Exception as exc:
            st.error(f"Üretim tamamlanamadı: {exc}")

latest = init_state("latest_design_run", None)
if latest is not None:
    st.markdown("### Üretim sonucu")
    render_design_run(latest)

render_disclaimer()
