lines = open('src/carpet_designer/cli.py').read().splitlines()
idx = lines.index("        if result.status == \"PASS\":")
good_lines = lines[:idx]
append = """        if result.status == "PASS":
            console.print(f"[green]Generation success! Saved to {result.image_path}[/green]")
            console.print(f"Hash: {result.image_sha256}")
            
            # Save to DB
            settings = get_settings()
            db = get_connection(settings.resolved_data_dir / "carpet_design.db")
            RecipeRepository(db).save(recipe_data)
            GenerationRepository(db).save(result)
            console.print("[dim]Result logged to database.[/dim]")
        else:
            console.print(f"[red]Generation failed: {result.warnings}[/red]")
            raise typer.Exit(code=1)
            
    except Exception as e:
        console.print(f"[red]Generation process failed: {e}[/red]")
        raise typer.Exit(code=1)


@app.command(name="batch-generate")
def batch_generate(
    recipes: Path = typer.Option(..., help="Path to recipes JSONL"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    \"\"\"Batch generate carpet designs from multiple recipes.\"\"\"
    configure_logging("INFO")
    if not recipes.exists():
        console.print(f"[red]Recipes file not found: {recipes}[/red]")
        raise typer.Exit(code=1)
    console.print(f"[yellow]Batch generate from: {recipes}[/yellow]")
    console.print("[dim]Implementation in M3 milestone[/dim]")


# --- Training commands ---

training_app = typer.Typer(help="Training commands")
app.add_typer(training_app, name="training")

@training_app.command()
def train(
    dataset_manifest: Path = typer.Option(..., help="Path to dataset manifest JSON"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate training run"),
) -> None:
    \"\"\"Run LoRA adapter training.\"\"\"
    configure_logging("INFO")
    if not dataset_manifest.exists():
        console.print(f"[red]Dataset manifest not found: {dataset_manifest}[/red]")
        raise typer.Exit(code=1)
        
    try:
        from carpet_designer.training.trainer import Trainer
        settings = get_settings()
        
        output_dir = settings.resolved_artifacts_dir / "models" / "lora_candidate"
        trainer = Trainer(dataset_path=dataset_manifest, output_dir=output_dir, dry_run=dry_run)
        
        console.print("[yellow]Starting training process...[/yellow]")
        manifest = trainer.train()
        
        console.print(f"[green]Training completed successfully![/green]")
        console.print(f"Metrics saved to: {manifest.metrics_path}")
        console.print(f"Adapter saved to: {manifest.artifact_path}")
        
    except Exception as e:
        console.print(f"[red]Training failed: {e}[/red]")
        raise typer.Exit(code=1)


# --- Evaluation commands ---

analysis_app = typer.Typer(help="Analysis commands")
app.add_typer(analysis_app, name="analysis")

@analysis_app.command()
def analyze(
    image: Path = typer.Option(..., help="Path to image for analysis"),
    generation_id: str = typer.Option("manual_import", help="Generation ID to attach this analysis to"),
) -> None:
    \"\"\"Analyze a carpet design for color and symmetry.\"\"\"
    configure_logging("INFO")
    if not image.exists():
        console.print(f"[red]Image not found: {image}[/red]")
        raise typer.Exit(code=1)
        
    try:
        from PIL import Image
        from carpet_designer.analysis.color import extract_dominant_colors
        from carpet_designer.analysis.geometry import analyze_seam_continuity, analyze_symmetry
        from carpet_designer.persistence.database import get_connection
        from carpet_designer.persistence.repositories import AnalysisRepository
        import uuid
        import json
        
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
            result_json_path=str(image.with_suffix('.analysis.json'))
        )
        console.print(f"[green]Analysis complete. ID: {analysis_id}[/green]")
        console.print("[dim]Analysis logged to database.[/dim]")
        
    except Exception as e:
        console.print(f"[red]Analysis failed: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def evaluate(
    config: Path = typer.Option(..., help="Path to evaluation config YAML"),
) -> None:
    \"\"\"Run evaluation benchmark.\"\"\"
    configure_logging("INFO")
    if not config.exists():
        console.print(f"[red]Config not found: {config}[/red]")
        raise typer.Exit(code=1)
    console.print(f"[yellow]Evaluation with: {config}[/yellow]")
    console.print("[dim]Implementation in M7 milestone[/dim]")


# --- Index commands ---

index_app = typer.Typer(help="Retrieval index management")
app.add_typer(index_app, name="index")


@index_app.command()
def build(
    collection_manifest: Path = typer.Option(
        ..., "--collection-manifest", help="Collection manifest"
    ),
) -> None:
    \"\"\"Build retrieval index from collection.\"\"\"
    configure_logging("INFO")
    console.print(f"[yellow]Build index from: {collection_manifest}[/yellow]")
    console.print("[dim]Implementation in M6 milestone[/dim]")


@index_app.command()
def search(
    image: Path = typer.Option(..., help="Query image path"),
    top_k: int = typer.Option(5, help="Number of results"),
) -> None:
    \"\"\"Search for similar designs.\"\"\"
    configure_logging("INFO")
    if not image.exists():
        console.print(f"[red]Image not found: {image}[/red]")
        raise typer.Exit(code=1)
    console.print(f"[yellow]Search similar to: {image}[/yellow]")
    console.print("[dim]Implementation in M6 milestone[/dim]")


# --- Model/LoRA commands ---

model_app = typer.Typer(help="Model management")
app.add_typer(model_app, name="model")


@model_app.command(name="list")
def model_list() -> None:
    \"\"\"List registered base models.\"\"\"
    configure_logging("INFO")
    console.print("[dim]No models registered yet[/dim]")


lora_app = typer.Typer(help="LoRA adapter management")
app.add_typer(lora_app, name="lora")


@lora_app.command(name="list")
def lora_list() -> None:
    \"\"\"List registered LoRA adapters.\"\"\"
    configure_logging("INFO")
    console.print("[dim]No LoRA adapters registered yet[/dim]")


@lora_app.command()
def promote(
    lora_id: str = typer.Option(..., help="LoRA adapter ID to promote"),
) -> None:
    \"\"\"Promote a LoRA adapter status.\"\"\"
    configure_logging("INFO")
    console.print(f"[yellow]Promote LoRA: {lora_id}[/yellow]")
    console.print("[dim]Implementation in M4 milestone[/dim]")
"""
with open('src/carpet_designer/cli.py', 'w') as f:
    f.write('\\n'.join(good_lines) + '\\n' + append)
