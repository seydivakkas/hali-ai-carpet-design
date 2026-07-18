"""LoRA registry and model-readiness page."""

from __future__ import annotations

import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import streamlit as st
import torch
import yaml

from carpet_designer.training.jobs import (
    build_training_cli_command,
    launch_training_job,
    save_training_plan,
    tail_text,
)
from carpet_designer.ui.components import (
    apply_app_style,
    get_design_service,
    render_disclaimer,
    render_sidebar_brand,
)

st.set_page_config(page_title="LoRA Kayıt Defteri", page_icon="◇", layout="wide")
apply_app_style()
render_sidebar_brand("Model & LoRA Kayıt Defteri")
service = get_design_service()
settings = service.settings

st.markdown(
    """
    <section class="hero"><div class="eyebrow">Model Governance</div>
    <h1>Model & LoRA kayıt defteri</h1><p>Temel model, adaptör yaşam döngüsü,
    veri manifesti bağı ve artifact durumu tek görünümde.</p></section>
    """,
    unsafe_allow_html=True,
)

model_config = yaml.safe_load(
    (settings.resolved_configs_dir / "models" / "sdxl_base.yaml").read_text(encoding="utf-8")
)["model"]
cards = st.columns(4)
cards[0].metric("Temel model", model_config["model_id"])
cards[1].metric("CUDA", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "Yok")
cards[2].metric("Lisans", model_config["license"])
cards[3].metric("Aktif motor", "SDXL + CPU offload" if torch.cuda.is_available() else "CPU DEMO")

st.markdown("### Kayıtlı LoRA adaptörleri")
loras = service.list_loras()
if loras:
    public_loras = [
        {
            "lora_id": item.get("lora_id", ""),
            "adapter_name": "carpet_domain_v1",
            "rank": item.get("rank", ""),
            "status": item.get("status", ""),
            "base_model_id": item.get("base_model_id", ""),
            "training_run_id": item.get("training_run_id", ""),
            "artifact_sha256": item.get("artifact_sha256", ""),
        }
        for item in loras
    ]
    st.dataframe(public_loras, use_container_width=True, hide_index=True)
else:
    st.warning(
        "Henüz tamamlanmış LoRA artifact'ı kayıtlı değil. Eğitim başladığında aday adaptör "
        "manifest ve SHA-256 bağıyla burada görünecektir."
    )

dataset_manifest = settings.resolved_data_dir / "processed" / "carpet_lora_v1" / "manifest.json"
with st.expander("Eğitim Laboratuvarı · deney ve checkpoint kontrolleri", expanded=False):
    st.caption(
        "Mevcut arayüzün içinde tekrarlanabilir bir eğitim planı oluşturur. Plan; veri hash'i, "
        "hiperparametreler ve çıktı klasörüyle GPU sürecinden önce kaydedilir."
    )
    with st.form("training_lab", border=False):
        profile_col, core_col, experiment_col = st.columns(3, gap="large")
        with profile_col:
            profile_label = st.selectbox(
                "Eğitim profili",
                ["Görsel başına caption", "Tek prompt · düşük VRAM"],
                help=(
                    "Caption profili metadata.jsonl içindeki her görselin açıklamasını kullanır; "
                    "8 GB VRAM'de daha ağırdır."
                ),
            )
            resolution = st.selectbox("Eğitim çözünürlüğü", [512, 768, 1024], index=0)
            rank = st.selectbox("LoRA rank", [4, 8, 16], index=0)
            seed = st.number_input("Eğitim + validasyon seed", 0, 2_147_483_647, 42)
        with core_col:
            max_train_steps = st.select_slider(
                "Optimizer adımı", options=[100, 250, 500, 750, 1000], value=250
            )
            learning_rate = st.selectbox(
                "Learning rate", [5e-5, 1e-4, 2e-4], index=1, format_func=str
            )
            gradient_accumulation_steps = st.selectbox(
                "Gradient accumulation", [2, 4, 8], index=1
            )
            random_flip = st.checkbox(
                "Yatay random flip",
                value=False,
                help="Yön anlamı taşıyan motifler için kapalı tutulması önerilir.",
            )
        with experiment_col:
            enable_snr = st.checkbox("Min-SNR deneyi", value=False)
            snr_gamma = st.number_input(
                "SNR gamma", 1.0, 10.0, 5.0, 0.5, disabled=not enable_snr
            )
            checkpointing_steps = st.selectbox(
                "Checkpoint sıklığı", [25, 50, 100], index=0
            )
            checkpoints_total_limit = st.number_input(
                "Saklanacak checkpoint", 1, 10, 3
            )
            resume_latest = st.checkbox("Son checkpoint'ten devam et", value=False)

        validation_prompt = st.text_area(
            "Sabit validasyon promptu",
            value=(
                "mrcpt carpet design, geometric central medallion, multi-band border, "
                "burgundy navy cream palette, flat full rug view"
            ),
            height=80,
        )
        validation_left, validation_right = st.columns(2)
        num_validation_images = validation_left.number_input(
            "Validasyon görseli", 1, 8, 2
        )
        validation_epochs = validation_right.number_input(
            "Validasyon aralığı (epoch)", 1, 10, 1
        )
        run_name = st.text_input(
            "Koşu adı",
            value=f"lora_{datetime.now(tz=UTC).strftime('%Y%m%d_%H%M')}",
            help="Yalnızca harf, rakam, tire ve alt çizgi kullanın.",
        )
        confirm_launch = st.checkbox(
            "Bu planla arka planda GPU eğitimini başlatmaya hazırım",
            value=False,
        )
        save_clicked = st.form_submit_button("Deney planını kaydet")
        launch_clicked = st.form_submit_button("GPU eğitimini başlat", type="primary")

    training_mode = (
        "caption_aware" if profile_label == "Görsel başına caption" else "single_prompt"
    )
    training_config = {
        "training_mode": training_mode,
        "max_train_steps": int(max_train_steps),
        "resolution": int(resolution),
        "rank": int(rank),
        "learning_rate": float(learning_rate),
        "gradient_accumulation_steps": int(gradient_accumulation_steps),
        "snr_gamma": float(snr_gamma) if enable_snr else None,
        "validation_prompt": validation_prompt.strip(),
        "num_validation_images": int(num_validation_images),
        "validation_epochs": int(validation_epochs),
        "checkpointing_steps": int(checkpointing_steps),
        "checkpoints_total_limit": int(checkpoints_total_limit),
        "resume_from_checkpoint": "latest" if resume_latest else None,
        "lr_scheduler": "constant",
        "lr_warmup_steps": 0,
        "seed": int(seed),
        "random_flip": bool(random_flip),
    }
    safe_run_name = run_name if re.fullmatch(r"[A-Za-z0-9_-]+", run_name) else ""
    output_dir = settings.resolved_artifacts_dir / "models" / "lora_runs" / safe_run_name
    preview_command = build_training_cli_command(
        dataset_manifest, output_dir, training_config
    )
    with st.popover("CLI komutunu göster"):
        st.code(subprocess.list2cmdline(preview_command), language="powershell")

    plans_dir = settings.resolved_artifacts_dir / "training" / "plans"
    if save_clicked or launch_clicked:
        if not safe_run_name:
            st.error("Koşu adı yalnızca harf, rakam, tire ve alt çizgi içerebilir.")
        elif not dataset_manifest.is_file():
            st.error(f"Eğitim veri manifesti bulunamadı: {dataset_manifest}")
        elif launch_clicked and not confirm_launch:
            st.error("GPU eğitimini başlatmak için onay kutusunu işaretleyin.")
        elif launch_clicked and not torch.cuda.is_available():
            st.error("CUDA GPU görünmüyor; planı kaydedebilir ancak eğitimi başlatamazsınız.")
        elif launch_clicked:
            job = launch_training_job(
                settings.project_root,
                plans_dir,
                dataset_manifest,
                output_dir,
                training_config,
            )
            st.session_state["active_training_job"] = job
            st.success(f"Eğitim arka planda başlatıldı · PID {job['pid']}")
        else:
            plan_path = save_training_plan(
                plans_dir, dataset_manifest, output_dir, training_config
            )
            st.success(f"Deney planı kaydedildi: {plan_path.name}")

    active_job = st.session_state.get("active_training_job")
    if isinstance(active_job, dict):
        st.markdown("#### Aktif/son başlatılan koşu")
        active_config = active_job.get("config", {})
        if not isinstance(active_config, dict):
            active_config = {}
        status_columns = st.columns(3)
        status_columns[0].metric("PID", active_job.get("pid", "—"))
        status_columns[1].metric("Profil", active_config.get("training_mode", "—"))
        status_columns[2].metric("Checkpoint", active_config.get("checkpointing_steps", "—"))
        log_path = Path(str(active_job.get("log_path", "")))
        with st.popover("Son log satırlarını göster"):
            st.code(tail_text(log_path), language="text")

st.markdown("### Aktivasyon kapıları")
artifact_ready = any(Path(str(item.get("artifact_path", ""))).is_file() for item in loras)
gates = [
    ("Veri kökeni", "Dataset manifest SHA-256 kayıtlı", dataset_manifest.is_file()),
    (
        "Lisans",
        "Training permission_ref kayıtlı",
        bool(settings.restricted_catalog_permission_ref),
    ),
    ("Teknik", "Safetensors artifact üretildi", artifact_ready),
    (
        "Kalite",
        "Benchmark ve insan değerlendirmesi kabul eşiği",
        any(item.get("status") in {"VALIDATED", "ACTIVE_COMPANY_PILOT"} for item in loras),
    ),
]
for title, body, passed in gates:
    st.checkbox(f"{title} · {body}", value=passed, disabled=True)

artifact_dir = settings.resolved_artifacts_dir / "models"
st.caption(f"Artifact deposu: {Path(artifact_dir)}")
render_disclaimer()
