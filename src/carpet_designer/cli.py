"""Typer CLI application per spec Section 24."""

from __future__ import annotations

import platform
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from carpet_designer import __version__
from carpet_designer.domain.enums import Status
from carpet_designer.domain.schemas import DoctorCheck, DoctorReport
from carpet_designer.logging_config import configure_logging, get_logger
from carpet_designer.settings import get_settings

app = typer.Typer(
    name="carpet-designer",
    help="Halı AI Carpet Design \u2014 Traceable Diffusion-Based Carpet Design Studio",
    no_args_is_help=True,
)
console = Console()
logger = get_logger("cli")


def _check_python() -> DoctorCheck:
    """Check Python version."""
    version = platform.python_version()
    parts = tuple(int(x) for x in version.split(".")[:2])
    ok = parts >= (3, 11)
    return DoctorCheck(
        name="Python",
        status=Status.PASS if ok else Status.FAIL,
        detail=f"Python {version}",
        value=version,
    )


def _check_os() -> DoctorCheck:
    """Check operating system."""
    os_info = f"{platform.system()} {platform.release()} {platform.machine()}"
    return DoctorCheck(name="OS", status=Status.PASS, detail=os_info, value=os_info)


def _check_gpu() -> DoctorCheck:
    """Check GPU availability via PyTorch."""
    try:
        import torch

        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            return DoctorCheck(
                name="GPU",
                status=Status.PASS,
                detail=f"{name} ({vram:.1f} GB VRAM)",
                value={"name": name, "vram_gb": round(vram, 1)},
            )
        return DoctorCheck(
            name="GPU", status=Status.HARDWARE_BLOCKED, detail="No CUDA GPU detected"
        )
    except ImportError:
        return DoctorCheck(
            name="GPU", status=Status.HARDWARE_BLOCKED, detail="PyTorch not installed"
        )


def _check_pytorch() -> DoctorCheck:
    """Check PyTorch installation."""
    try:
        import torch

        cuda_str = f", CUDA {torch.version.cuda}" if torch.cuda.is_available() else ", CPU only"
        return DoctorCheck(
            name="PyTorch",
            status=Status.PASS,
            detail=f"torch {torch.__version__}{cuda_str}",
            value=torch.__version__,
        )
    except ImportError:
        return DoctorCheck(name="PyTorch", status=Status.BLOCKED, detail="Not installed")


def _check_diffusers() -> DoctorCheck:
    """Check Diffusers installation."""
    try:
        import diffusers

        return DoctorCheck(
            name="Diffusers",
            status=Status.PASS,
            detail=f"diffusers {diffusers.__version__}",
            value=diffusers.__version__,
        )
    except ImportError:
        return DoctorCheck(name="Diffusers", status=Status.BLOCKED, detail="Not installed")


def _check_transformers() -> DoctorCheck:
    """Check Transformers installation."""
    try:
        import transformers

        return DoctorCheck(
            name="Transformers",
            status=Status.PASS,
            detail=f"transformers {transformers.__version__}",
            value=transformers.__version__,
        )
    except ImportError:
        return DoctorCheck(name="Transformers", status=Status.BLOCKED, detail="Not installed")


def _check_peft() -> DoctorCheck:
    """Check PEFT installation."""
    try:
        import peft

        return DoctorCheck(
            name="PEFT",
            status=Status.PASS,
            detail=f"peft {peft.__version__}",
            value=peft.__version__,
        )
    except ImportError:
        return DoctorCheck(name="PEFT", status=Status.BLOCKED, detail="Not installed")


def _check_disk() -> DoctorCheck:
    """Check available disk space."""
    import psutil

    settings = get_settings()
    root = settings.project_root
    usage = psutil.disk_usage(str(root))
    free_gb = usage.free / (1024**3)
    status = Status.PASS if free_gb > 10 else Status.FAIL
    return DoctorCheck(
        name="Disk",
        status=status,
        detail=f"{free_gb:.1f} GB free",
        value=round(free_gb, 1),
    )


def _check_ram() -> DoctorCheck:
    """Check available RAM."""
    import psutil

    mem = psutil.virtual_memory()
    total_gb = mem.total / (1024**3)
    avail_gb = mem.available / (1024**3)
    return DoctorCheck(
        name="RAM",
        status=Status.PASS,
        detail=f"{avail_gb:.1f} GB available / {total_gb:.1f} GB total",
        value={"total_gb": round(total_gb, 1), "available_gb": round(avail_gb, 1)},
    )


def _check_database() -> DoctorCheck:
    """Check database connectivity."""
    settings = get_settings()
    db_path = settings.resolved_db_path
    try:
        from carpet_designer.persistence.database import get_connection

        conn = get_connection(db_path)
        conn.execute("SELECT 1")
        conn.close()
        return DoctorCheck(
            name="Database",
            status=Status.PASS,
            detail=f"SQLite at {db_path}",
        )
    except Exception as exc:
        return DoctorCheck(
            name="Database",
            status=Status.FAIL,
            detail=f"Failed: {exc}",
        )


def _check_writable_paths() -> DoctorCheck:
    """Check that artifact directories are writable."""
    settings = get_settings()
    paths_to_check = [
        settings.resolved_artifacts_dir,
        settings.resolved_data_dir,
    ]
    failed: list[str] = []
    for p in paths_to_check:
        try:
            p.mkdir(parents=True, exist_ok=True)
            test_file = p / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
        except OSError:
            failed.append(str(p))

    if failed:
        return DoctorCheck(
            name="Writable Paths",
            status=Status.FAIL,
            detail=f"Not writable: {', '.join(failed)}",
        )
    return DoctorCheck(name="Writable Paths", status=Status.PASS, detail="All paths writable")


def run_doctor() -> DoctorReport:
    """Run all system doctor checks.

    Returns:
        DoctorReport with all check results.
    """
    checks = [
        _check_python(),
        _check_os(),
        _check_gpu(),
        _check_pytorch(),
        _check_diffusers(),
        _check_transformers(),
        _check_peft(),
        _check_ram(),
        _check_disk(),
        _check_database(),
        _check_writable_paths(),
    ]

    has_fail = any(c.status == Status.FAIL for c in checks)
    has_blocked = any(c.status in (Status.BLOCKED, Status.HARDWARE_BLOCKED) for c in checks)

    if has_fail:
        overall = Status.FAIL
    elif has_blocked:
        overall = Status.PASS_WITH_RESTRICTIONS
    else:
        overall = Status.PASS

    return DoctorReport(checks=checks, overall_status=overall)


@app.command()
def doctor(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Run system environment doctor checks."""
    configure_logging("INFO")
    report = run_doctor()

    if json_output:
        console.print(report.model_dump_json(indent=2))
        return

    table = Table(title="Carpet Designer \u2014 System Doctor")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Detail")

    status_styles = {
        Status.PASS: "[green]PASS[/green]",
        Status.FAIL: "[red]FAIL[/red]",
        Status.BLOCKED: "[yellow]BLOCKED[/yellow]",
        Status.HARDWARE_BLOCKED: "[yellow]HW_BLOCKED[/yellow]",
        Status.PASS_WITH_RESTRICTIONS: "[blue]RESTRICTED[/blue]",
        Status.NOT_RUN: "[dim]NOT_RUN[/dim]",
    }

    for check in report.checks:
        table.add_row(
            check.name,
            status_styles.get(check.status, str(check.status)),
            check.detail,
        )

    console.print(table)
    console.print(
        f"\n[bold]Overall: {status_styles.get(report.overall_status, str(report.overall_status))}[/bold]"
    )

    # Save report
    settings = get_settings()
    reports_dir = settings.resolved_artifacts_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "system_doctor.json"
    report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    console.print(f"\nReport saved: {report_path}")


@app.command()
def version() -> None:
    """Show application version."""
    console.print(f"Halı AI Carpet Design v{__version__}")


@app.command()
def serve(
    port: int = typer.Option(8501, help="Streamlit port"),
) -> None:
    """Launch Streamlit UI."""
    import subprocess

    settings = get_settings()
    app_path = Path(__file__).parent / "ui" / "app.py"

    if not app_path.exists():
        console.print("[red]UI app not found.[/red]")
        raise typer.Exit(code=1)

    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path), "--server.port", str(port)],
        cwd=str(settings.project_root),
        check=False,
    )


# --- Dataset commands ---

dataset_app = typer.Typer(help="Dataset management commands")
app.add_typer(dataset_app, name="dataset")


@dataset_app.command()
def audit(
    manifest: Path = typer.Option(..., help="Path to dataset manifest JSON"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Audit a dataset manifest for completeness and license compliance."""
    configure_logging("INFO")
    if not manifest.exists():
        console.print(f"[red]Manifest not found: {manifest}[/red]")
        raise typer.Exit(code=1)

    try:
        from carpet_designer.data.manifest import ManifestBuilder

        loaded = ManifestBuilder.load(manifest)
        console.print(f"[green]Manifest loaded successfully: {loaded.dataset_id}[/green]")
        console.print(f"Total files: {loaded.counts.get('total', 0)}")

        # Check licenses
        licenses = {f.license for f in loaded.files}
        console.print(f"Licenses found: {', '.join(licenses)}")
        if any(lic.lower() not in {"cc0", "public_domain", "open"} for lic in licenses):
            console.print("[yellow]Status: RESTRICTED (Commercial use may be prohibited)[/yellow]")
        else:
            console.print("[green]Status: VERIFIED (Open licenses)[/green]")

        if json_output:
            console.print(loaded.model_dump_json(indent=2))

    except Exception as e:
        console.print(f"[red]Audit failed: {e}[/red]")
        raise typer.Exit(code=1) from e


@dataset_app.command()
def prepare(
    source_dir: Path = typer.Option(..., help="Path to raw dataset directory"),
    dataset_id: str = typer.Option(..., help="Unique ID for this dataset"),
    license_type: str = typer.Option("custom", help="License type (e.g. cc0, restricted)"),
) -> None:
    """Prepare dataset for training based on configuration."""
    configure_logging("INFO")
    if not source_dir.exists() or not source_dir.is_dir():
        console.print(f"[red]Source directory not found: {source_dir}[/red]")
        raise typer.Exit(code=1)

    try:
        from carpet_designer.services.dataset_service import DatasetService

        settings = get_settings()

        service = DatasetService(
            data_dir=settings.resolved_data_dir,
            manifests_dir=settings.project_root / "data" / "manifests",
        )

        manifest_path = service.prepare_dataset(
            source_dir=source_dir, dataset_id=dataset_id, license_type=license_type
        )
        console.print(
            f"[green]Dataset prepared successfully. Manifest saved to: {manifest_path}[/green]"
        )

    except Exception as e:
        console.print(f"[red]Preparation failed: {e}[/red]")
        raise typer.Exit(code=1) from e


# --- Generate commands ---


@app.command()
def generate(
    recipe: Path = typer.Option(..., help="Path to prompt recipe JSON"),
) -> None:
    """Generate a single carpet design from a recipe."""
    configure_logging("INFO")
    if not recipe.exists():
        console.print(f"[red]Recipe not found: {recipe}[/red]")
        raise typer.Exit(code=1)

    try:
        from carpet_designer.domain.schemas import PromptRecipe
        from carpet_designer.services.design_service import DesignService

        recipe_data = PromptRecipe.model_validate_json(recipe.read_text(encoding="utf-8"))
        console.print(f"[green]Loaded recipe: {recipe_data.recipe_id}[/green]")

        service = DesignService()
        console.print(f"[yellow]Starting generation on {service.pipeline.device}...[/yellow]")
        run = service.generate_design(recipe_data)
        console.print(f"[green]Generation success! Saved to {run.generation.image_path}[/green]")
        console.print(f"Hash: {run.generation.image_sha256}")
        console.print(f"JSON report: {run.json_report_path}")
        console.print(f"HTML report: {run.html_report_path}")

    except Exception as e:
        console.print(f"[red]Generation process failed: {e}[/red]")
        raise typer.Exit(code=1) from e


@app.command(name="batch-generate")
def batch_generate(
    recipes: Path = typer.Option(..., help="Path to recipes JSONL"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Batch generate carpet designs from multiple recipes."""
    configure_logging("INFO")
    if not recipes.exists():
        console.print(f"[red]Recipes file not found: {recipes}[/red]")
        raise typer.Exit(code=1)
    try:
        from carpet_designer.domain.schemas import PromptRecipe
        from carpet_designer.services.design_service import DesignService

        service = DesignService()
        runs = []
        for line_number, line in enumerate(recipes.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            recipe_data = PromptRecipe.model_validate_json(line)
            run = service.generate_design(recipe_data)
            runs.append(run)
            console.print(
                f"[green]#{line_number}[/green] {run.generation.generation_id} "
                f"→ {run.generation.image_path}"
            )
        if json_output:
            console.print_json(data=[run.model_dump(mode="json") for run in runs])
        console.print(f"[bold green]{len(runs)} design(s) completed.[/bold green]")
    except Exception as e:
        console.print(f"[red]Batch generation failed: {e}[/red]")
        raise typer.Exit(code=1) from e


# --- Training commands ---

training_app = typer.Typer(help="Training commands")
app.add_typer(training_app, name="training")


@training_app.command()
def train(
    dataset_manifest: Path = typer.Option(..., help="Path to dataset manifest JSON"),
    output_dir: Path | None = typer.Option(
        None, "--output-dir", help="Directory for checkpoints and final LoRA weights"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Validate and record the plan without producing model weights",
    ),
    max_train_steps: int = typer.Option(100, min=1, help="LoRA optimizer update steps"),
    resolution: int = typer.Option(512, min=256, max=1024, help="Training image resolution"),
    rank: int = typer.Option(4, min=1, max=64, help="LoRA rank"),
    training_mode: str = typer.Option(
        "caption_aware",
        help="caption_aware uses metadata.jsonl; single_prompt is the lower-VRAM profile",
    ),
    learning_rate: float = typer.Option(1e-4, min=1e-7, max=1e-2),
    gradient_accumulation_steps: int = typer.Option(4, min=1, max=64),
    snr_gamma: float | None = typer.Option(
        None, help="Optional Min-SNR gamma; use 5.0 for the comparison run"
    ),
    validation_prompt: str = typer.Option(
        (
            "mrcpt carpet design, geometric central medallion, multi-band border, "
            "burgundy navy cream palette, flat full rug view"
        ),
        help="Fixed prompt used for checkpoint validation",
    ),
    num_validation_images: int = typer.Option(2, min=1, max=8),
    validation_epochs: int = typer.Option(1, min=1),
    checkpointing_steps: int = typer.Option(25, min=1),
    checkpoints_total_limit: int = typer.Option(3, min=1, max=20),
    resume_from_checkpoint: str | None = typer.Option(
        None, help="Checkpoint path or 'latest'"
    ),
    lr_scheduler: str = typer.Option("constant"),
    lr_warmup_steps: int = typer.Option(0, min=0),
    seed: int = typer.Option(42, min=0, max=2_147_483_647),
    random_flip: bool = typer.Option(
        False,
        "--random-flip/--no-random-flip",
        help="Keep disabled for directional carpet motifs",
    ),
) -> None:
    """Run LoRA adapter training."""
    configure_logging("INFO")
    if not dataset_manifest.exists():
        console.print(f"[red]Dataset manifest not found: {dataset_manifest}[/red]")
        raise typer.Exit(code=1)

    try:
        from carpet_designer.training.trainer import Trainer

        settings = get_settings()

        resolved_output_dir = output_dir or (
            settings.resolved_artifacts_dir / "models" / "lora_candidate"
        )
        if not resolved_output_dir.is_absolute():
            resolved_output_dir = settings.resolve_path(resolved_output_dir)
        trainer = Trainer(
            dataset_path=dataset_manifest,
            output_dir=resolved_output_dir,
            dry_run=dry_run,
        )

        console.print("[yellow]Starting training process...[/yellow]")
        manifest = trainer.train(
            {
                "max_train_steps": max_train_steps,
                "resolution": resolution,
                "rank": rank,
                "training_mode": training_mode,
                "learning_rate": learning_rate,
                "gradient_accumulation_steps": gradient_accumulation_steps,
                "snr_gamma": snr_gamma,
                "validation_prompt": validation_prompt,
                "num_validation_images": num_validation_images,
                "validation_epochs": validation_epochs,
                "checkpointing_steps": checkpointing_steps,
                "checkpoints_total_limit": checkpoints_total_limit,
                "resume_from_checkpoint": resume_from_checkpoint,
                "lr_scheduler": lr_scheduler,
                "lr_warmup_steps": lr_warmup_steps,
                "seed": seed,
                "random_flip": random_flip,
            }
        )
        if not dry_run:
            from carpet_designer.services.design_service import DesignService

            DesignService(settings=settings).register_lora(manifest)

        console.print("[green]Training completed successfully![/green]")
        console.print(f"Metrics saved to: {manifest.metrics_path}")
        console.print(f"Adapter saved to: {manifest.artifact_path}")

    except Exception as e:
        console.print(f"[red]Training failed: {e}[/red]")
        raise typer.Exit(code=1) from e


# --- Evaluation commands ---

analysis_app = typer.Typer(help="Analysis commands")
app.add_typer(analysis_app, name="analysis")


@analysis_app.command()
def analyze(
    image: Path = typer.Option(..., help="Path to image for analysis"),
    generation_id: str = typer.Option(
        "manual_import", help="Generation ID to attach this analysis to"
    ),
) -> None:
    """Analyze a carpet design for color and symmetry."""
    configure_logging("INFO")
    if not image.exists():
        console.print(f"[red]Image not found: {image}[/red]")
        raise typer.Exit(code=1)

    try:
        import uuid

        from PIL import Image

        from carpet_designer.analysis.color import extract_dominant_colors
        from carpet_designer.analysis.geometry import analyze_seam_continuity, analyze_symmetry
        from carpet_designer.persistence.database import get_connection
        from carpet_designer.persistence.repositories import AnalysisRepository

        console.print(f"[yellow]Analyzing image: {image.name}[/yellow]")
        img = Image.open(image)

        # Color Analysis
        color_res = extract_dominant_colors(img)
        console.print("[bold cyan]Color Extraction:[/bold cyan]")
        for c in color_res.dominant_colors:
            console.print(f"  - {c.hex}: {c.proportion:.1%}")

        # Symmetry Analysis
        sym_res = analyze_symmetry(img)
        console.print("[bold cyan]Symmetry Score:[/bold cyan]")
        console.print(f"  - Horizontal: {sym_res.horizontal_score:.2f}")
        console.print(f"  - Vertical:   {sym_res.vertical_score:.2f}")

        # Seam Analysis
        seam_res = analyze_seam_continuity(img)
        console.print("[bold cyan]Seam Continuity:[/bold cyan]")
        console.print(f"  - Overall Score: {seam_res.overall_score:.2f}")

        # Save to DB
        analysis_id = f"ana_{uuid.uuid4().hex[:12]}"
        settings = get_settings()
        db = get_connection(settings.resolved_data_dir / "carpet_design.db")
        repo = AnalysisRepository(db)
        repo.save(
            analysis_id=analysis_id,
            generation_id=generation_id,
            mean_delta_e=0.0,
            symmetry_score=sym_res.central_alignment_score,
            seam_score=seam_res.overall_score,
            result_json_path=str(image.with_suffix(".analysis.json")),
        )
        console.print(f"[green]Analysis complete. ID: {analysis_id}[/green]")
        console.print("[dim]Analysis logged to database.[/dim]")

    except Exception as e:
        console.print(f"[red]Analysis failed: {e}[/red]")
        raise typer.Exit(code=1) from e


@app.command()
def evaluate(
    config: Path = typer.Option(..., help="Path to evaluation config YAML"),
) -> None:
    """Run evaluation benchmark."""
    configure_logging("INFO")
    if not config.exists():
        console.print(f"[red]Config not found: {config}[/red]")
        raise typer.Exit(code=1)

    try:
        from carpet_designer.evaluation.benchmark import BenchmarkOrchestrator

        settings = get_settings()
        reports_dir = settings.resolved_artifacts_dir / "reports" / "evaluation"
        orchestrator = BenchmarkOrchestrator(output_dir=reports_dir)

        console.print(f"[yellow]Running evaluation benchmark from {config.name}...[/yellow]")
        result = orchestrator.run(config)

        color = "green" if result.status == "PASS" else "yellow"
        console.print(f"[{color}]Evaluation status: {result.status}[/{color}]")
        console.print("[bold cyan]Metrics:[/bold cyan]")
        for k, v in result.metrics.items():
            value = "NOT_RUN" if v is None else f"{v:.4f}"
            console.print(f"  - {k}: {value}")

    except Exception as e:
        console.print(f"[red]Evaluation failed: {e}[/red]")
        raise typer.Exit(code=1) from e


# --- Index commands ---

index_app = typer.Typer(help="Retrieval index management")
app.add_typer(index_app, name="index")


@index_app.command()
def build(
    collection_manifest: Path = typer.Option(
        ..., "--collection-manifest", help="Collection manifest"
    ),
) -> None:
    """Build retrieval index from collection."""
    configure_logging("INFO")
    if not collection_manifest.exists():
        console.print(f"[red]Manifest not found: {collection_manifest}[/red]")
        raise typer.Exit(code=1)

    try:
        from carpet_designer.data.manifest import ManifestBuilder
        from carpet_designer.retrieval.index import IndexManager

        settings = get_settings()
        manifest_data = ManifestBuilder.load(collection_manifest)

        index_dir = settings.resolved_artifacts_dir / "index"
        manager = IndexManager(index_dir=index_dir)

        console.print(f"[yellow]Building index from {len(manifest_data.files)} files...[/yellow]")
        manager.build_from_manifest(manifest_data, settings.resolved_data_dir)

        console.print("[green]Index build complete.[/green]")
        console.print(f"Index saved to: {manager.index_path}")

    except Exception as e:
        console.print(f"[red]Build failed: {e}[/red]")
        raise typer.Exit(code=1) from e


@index_app.command()
def search(
    image: Path = typer.Option(..., help="Query image path"),
    top_k: int = typer.Option(5, help="Number of results"),
) -> None:
    """Search for similar designs."""
    configure_logging("INFO")
    if not image.exists():
        console.print(f"[red]Image not found: {image}[/red]")
        raise typer.Exit(code=1)

    try:
        from PIL import Image

        from carpet_designer.retrieval.index import IndexManager

        settings = get_settings()
        index_dir = settings.resolved_artifacts_dir / "index"
        manager = IndexManager(index_dir=index_dir)
        manager.load()

        console.print("[yellow]Searching index for similar designs...[/yellow]")
        img = Image.open(image)
        results = manager.search(img, top_k=top_k)

        if not results:
            console.print("[yellow]No results found (index might be empty).[/yellow]")
            return

        console.print("[bold cyan]Top matches:[/bold cyan]")
        for i, res in enumerate(results, 1):
            console.print(f"  {i}. {res['path']} (score: {res['score']:.4f})")

    except Exception as e:
        console.print(f"[red]Search failed: {e}[/red]")
        raise typer.Exit(code=1) from e


# --- Model/LoRA commands ---

model_app = typer.Typer(help="Model management")
app.add_typer(model_app, name="model")


@model_app.command(name="list")
def model_list() -> None:
    """List registered base models."""
    configure_logging("INFO")
    console.print("[dim]No models registered yet[/dim]")


lora_app = typer.Typer(help="LoRA adapter management")
app.add_typer(lora_app, name="lora")


@lora_app.command(name="list")
def lora_list() -> None:
    """List registered LoRA adapters."""
    configure_logging("INFO")
    from carpet_designer.services.design_service import DesignService

    adapters = DesignService().list_loras()
    if not adapters:
        console.print("[dim]No LoRA adapters registered yet[/dim]")
        return
    console.print_json(data=adapters)


@lora_app.command()
def promote(
    lora_id: str = typer.Option(..., help="LoRA adapter ID to promote"),
) -> None:
    """Promote a LoRA adapter status."""
    configure_logging("INFO")
    console.print(f"[yellow]Promote LoRA: {lora_id}[/yellow]")
    console.print("[dim]Implementation in M4 milestone[/dim]")
