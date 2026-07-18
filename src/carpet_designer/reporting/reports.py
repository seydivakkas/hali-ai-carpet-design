"""Standalone JSON and HTML report generation for design runs."""

from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from carpet_designer.domain.schemas import DesignRunResult


class ReportWriter:
    """Write traceable, presentation-ready reports for a generated design."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def paths_for(self, generation_id: str) -> tuple[Path, Path]:
        """Return the JSON and HTML report paths for a generation."""
        return (
            self.output_dir / f"{generation_id}.json",
            self.output_dir / f"{generation_id}.html",
        )

    def write(self, run: DesignRunResult) -> tuple[Path, Path]:
        """Write JSON and self-contained HTML reports."""
        json_path, html_path = self.paths_for(run.generation.generation_id)
        json_path.write_text(run.model_dump_json(indent=2), encoding="utf-8")
        html_path.write_text(self._render_html(run), encoding="utf-8")
        return json_path, html_path

    def _render_html(self, run: DesignRunResult) -> str:
        generation = run.generation
        analysis = run.analysis
        image_bytes = Path(generation.image_path).read_bytes()
        image_data = base64.b64encode(image_bytes).decode("ascii")
        color_swatches = "".join(
            (
                '<div class="swatch">'
                f'<span style="background:{html.escape(color.hex)}"></span>'
                f"<b>{html.escape(color.hex.upper())}</b>"
                f"<small>{color.proportion:.1%}</small>"
                "</div>"
            )
            for color in analysis.color.dominant_colors
        )
        warnings = "".join(f"<li>{html.escape(item)}</li>" for item in generation.warnings)
        motifs = ", ".join(run.recipe.motifs) or "—"
        return f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Halı AI Carpet Design · {html.escape(generation.generation_id)}</title>
<style>
:root{{--ink:#17211c;--muted:#667269;--paper:#f6f3ec;--brand:#8b1e2d;--gold:#b9904a;--card:#fff}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 Arial,sans-serif}}
.wrap{{max-width:1160px;margin:0 auto;padding:36px}} header{{display:flex;justify-content:space-between;gap:24px;border-bottom:1px solid #d8d2c5;padding-bottom:22px}}
h1{{margin:0;font-size:30px}} .eyebrow{{color:var(--brand);font-weight:800;letter-spacing:.12em;text-transform:uppercase;font-size:12px}}
.badge{{background:#e7efe9;color:#245438;border-radius:99px;padding:8px 14px;height:max-content;font-weight:700}}
.hero{{display:grid;grid-template-columns:1.1fr .9fr;gap:28px;margin:28px 0}} .card{{background:var(--card);border:1px solid #e3ded3;border-radius:18px;padding:22px;box-shadow:0 8px 30px #29352d0b}}
img{{display:block;width:100%;border-radius:12px}} h2{{font-size:18px;margin:0 0 16px}} dl{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:0}} dt{{color:var(--muted);font-size:12px}} dd{{margin:2px 0 0;font-weight:700}}
.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}} .metric strong{{display:block;font-size:27px;color:var(--brand)}} .metric span{{color:var(--muted);font-size:12px}}
.swatches{{display:flex;gap:10px;flex-wrap:wrap}} .swatch{{min-width:105px}} .swatch span{{display:block;height:48px;border-radius:9px;border:1px solid #0001}} .swatch b,.swatch small{{display:block;margin-top:4px}} .swatch small{{color:var(--muted)}}
code{{display:block;white-space:pre-wrap;background:#18231d;color:#eef4ef;border-radius:12px;padding:16px}} footer{{margin-top:28px;color:var(--muted);font-size:12px}}
@media(max-width:800px){{.hero{{grid-template-columns:1fr}}.metrics{{grid-template-columns:1fr 1fr}}.wrap{{padding:20px}}}}
</style></head><body><main class="wrap">
<header><div><div class="eyebrow">AI Design Evidence Report</div><h1>Halı Tasarım Koşusu</h1><div>{html.escape(generation.generation_id)}</div></div><div class="badge">{html.escape(generation.status.value)}</div></header>
<section class="hero"><div class="card"><img src="data:image/png;base64,{image_data}" alt="Generated carpet design"></div>
<div class="card"><h2>Tasarım reçetesi</h2><dl>
<div><dt>Motor</dt><dd>{html.escape(run.engine_mode)}</dd></div><div><dt>Seed</dt><dd>{generation.seed}</dd></div>
<div><dt>Stil</dt><dd>{html.escape(run.recipe.style_family or "—")}</dd></div><div><dt>Kompozisyon</dt><dd>{html.escape(run.recipe.composition or "—")}</dd></div>
<div><dt>Palet</dt><dd>{html.escape(run.recipe.palette_id or "—")}</dd></div><div><dt>Motifler</dt><dd>{html.escape(motifs)}</dd></div>
<div><dt>Boyut</dt><dd>{generation.width} × {generation.height}</dd></div><div><dt>Toplam süre</dt><dd>{generation.timing.total_ms:.0f} ms</dd></div>
</dl><h2 style="margin-top:22px">Uyarılar</h2><ul>{warnings or "<li>Uyarı yok</li>"}</ul></div></section>
<section class="metrics">
<div class="card metric"><strong>{analysis.symmetry.central_alignment_score:.0%}</strong><span>Merkez simetrisi</span></div>
<div class="card metric"><strong>{analysis.seam.overall_score:.0%}</strong><span>Seam sürekliliği</span></div>
<div class="card metric"><strong>{analysis.repeatability.periodicity_score:.0%}</strong><span>Tekrar skoru</span></div>
<div class="card metric"><strong>{analysis.color.coverage_ratio:.0%}</strong><span>Palet kapsamı</span></div>
</section>
<section class="card" style="margin-top:20px"><h2>Baskın renkler</h2><div class="swatches">{color_swatches}</div></section>
<section class="card" style="margin-top:20px"><h2>Üretilen pozitif prompt</h2><code>{html.escape(run.positive_prompt)}</code></section>
<footer>Bu rapor dijital tasarım değerlendirmesidir. Üretilebilirlik, kültürel özgünlük veya hukuki özgünlük iddiası taşımaz.</footer>
</main></body></html>"""
