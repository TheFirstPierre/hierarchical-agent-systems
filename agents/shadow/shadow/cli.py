"""Standalone SHADOW agent CLI — no yavapai_swarm dependency."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from .agent import ShadowAgent
from .briefing_pdf import generate_shadow_briefing_pdf
from .config import CURRENT_CONFIG
from .targets import DEFAULT_MISSION_ID
from .token_budget import unlimited_tokens

app = typer.Typer(help="SHADOW — standalone regional multi-domain anomaly anomaly analyst")
console = Console()


def _limits_label(max_tokens: int, stop_ratio: float, max_turns: int) -> str:
    tok = "0 (unlimited)" if unlimited_tokens(max_tokens) else str(max_tokens)
    turns = "0 (unlimited)" if max_turns <= 0 else str(max_turns)
    ratio = f"{stop_ratio:.2f}"
    return f"max_tokens: {tok}  |  max_turns: {turns}  |  stop_ratio: {ratio}"


@app.command("activate")
def activate(
    max_tokens: int = typer.Option(0, "--max-tokens", help="0 = unlimited"),
    stop_ratio: float = typer.Option(0.00, "--stop-ratio", help="0.00 = ratio stop disabled"),
    max_turns: int = typer.Option(0, "--max-turns", help="0 = unlimited"),
    duration_minutes: float | None = typer.Option(None, "--duration-minutes", "-d", help="Optional time limit"),
    out: str | None = typer.Option(None, "--out", "-o", help="Write JSON mission report"),
    pdf: str | None = typer.Option(None, "--pdf", help="Write briefing PDF path"),
    json_only: bool = typer.Option(False, "--json", help="Output only JSON to stdout"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
):
    """Activate SHADOW for regional multi-domain anomaly analysis."""
    console.print(Panel.fit(
        "[bold magenta]SHADOW STANDALONE ACTIVATION[/]\n"
        "Mission: Regional multi-domain anomaly Anomaly Analysis\n"
        + _limits_label(max_tokens, stop_ratio, max_turns),
        title="SHADOW",
        border_style="magenta",
    ))

    force_ask = CURRENT_CONFIG.permission == "always ask"
    if not json_only and not yes and force_ask:
        services = "OpenSky Network (KSEZ ADS-B), SESP keyword/memory layers, public web intel"
        console.print(f"\n[yellow]SHADOW will contact:[/yellow] {services}")
        if not typer.confirm("Activate SHADOW agent and begin analysis turns?", default=True):
            console.print("[red]Aborted. SHADOW not activated.[/red]")
            raise typer.Exit(code=0)

    agent = ShadowAgent(
        mission_id=DEFAULT_MISSION_ID,
        max_tokens=max_tokens,
        stop_ratio=stop_ratio,
        max_turns=max_turns,
        duration_minutes=duration_minutes,
        deep_mode=True,
        continue_after_discovery=True,
    )

    with console.status("[magenta]SHADOW running analysis turns...[/]"):
        result = agent.run()

    result_dict = result.to_dict()

    if json_only:
        console.print_json(data=result_dict)
        return

    console.print("\n[bold green]SHADOW mission complete.[/bold green]")
    console.print(f"  Turns: {result.turns_executed}  |  Stop: {result.stop_reason}")
    console.print(f"  Discoveries: {len(result.discoveries)}  |  Coupled: {len(result.coupled_anomalies)}")
    console.print(
        f"  Tokens used: {result.token_budget.get('tokens_used')}  |  "
        f"Remaining: {result.token_budget.get('tokens_remaining')}"
    )

    if out:
        Path(out).write_text(json.dumps(result_dict, indent=2, default=str))
        console.print(f"\n[green]JSON report:[/green] {out}")

    pdf_path = pdf or str(
        Path.home() / "Desktop" / f"SHADOW_Sedona_Briefing_{datetime.now().strftime('%Y-%m-%d')}.pdf"
    )
    generate_shadow_briefing_pdf(result_dict, Path(pdf_path))
    console.print(f"[green]Briefing PDF:[/green] {pdf_path}")


@app.command("loop")
def loop(
    duration_minutes: float = typer.Option(13.0, "--duration-minutes", "-d"),
    max_tokens: int = typer.Option(0, "--max-tokens", help="0 = unlimited"),
    stop_ratio: float = typer.Option(0.00, "--stop-ratio"),
    max_turns: int = typer.Option(0, "--max-turns", help="0 = unlimited"),
    out: str = typer.Option("/tmp/shadow_sedona_loop.json", "--out", "-o"),
    pdf: str | None = typer.Option(None, "--pdf"),
    yes: bool = typer.Option(False, "--yes", "-y"),
):
    """Recursive loop: learn across cycles until duration or optional caps."""
    console.print(Panel.fit(
        "[bold magenta]SHADOW RECURSIVE LOOP (STANDALONE)[/]\n"
        f"Duration: {duration_minutes} min\n"
        + _limits_label(max_tokens, stop_ratio, max_turns) + "\n"
        "Learning persists across cycles; continues after discoveries.",
        title="SHADOW LOOP",
        border_style="magenta",
    ))

    force_ask = CURRENT_CONFIG.permission == "always ask"
    if not yes and force_ask:
        if not typer.confirm(
            f"Run recursive SHADOW loop for {duration_minutes} min?",
            default=True,
        ):
            raise typer.Exit(code=0)

    agent = ShadowAgent(
        mission_id=DEFAULT_MISSION_ID,
        max_tokens=max_tokens,
        stop_ratio=stop_ratio,
        max_turns=max_turns,
        recursive_loop=True,
        duration_minutes=duration_minutes,
        continue_after_discovery=True,
        deep_mode=True,
    )

    with console.status(f"[magenta]SHADOW recursive loop ({duration_minutes} min)...[/]"):
        result = agent.run()

    result_dict = result.to_dict()
    console.print("\n[bold green]SHADOW loop complete.[/bold green]")
    console.print(f"  Elapsed: {result.summary.get('elapsed_minutes')} min  |  Cycles: {result.cycles_completed}")
    console.print(f"  Turns: {result.turns_executed}  |  Stop: {result.stop_reason}")
    console.print(f"  Useful findings: {len(result.useful_findings)}")
    console.print(
        f"  Tokens used: {result.token_budget.get('tokens_used')}  |  "
        f"Remaining: {result.token_budget.get('tokens_remaining')}"
    )

    Path(out).write_text(json.dumps(result_dict, indent=2, default=str))
    console.print(f"[green]JSON:[/green] {out}")

    pdf_path = pdf or str(
        Path.home() / "Desktop" / f"SHADOW_Loop_Briefing_{datetime.now().strftime('%Y-%m-%d_%H%M')}.pdf"
    )
    generate_shadow_briefing_pdf(result_dict, Path(pdf_path))
    console.print(f"[green]Briefing PDF:[/green] {pdf_path}")


@app.command("deploy")
def deploy(
    duration_minutes: float | None = typer.Option(None, "--duration-minutes", "-d"),
    yes: bool = typer.Option(False, "--yes", "-y"),
):
    """Deploy SHADOW — max_turns:0 max_tokens:0 stop_ratio:0.00 (all unlimited)."""
    console.print(Panel.fit(
        "[bold magenta]SHADOW PRODUCTION DEPLOY[/]\n"
        "max_turns: 0  |  max_tokens: 0  |  stop_ratio: 0.00\n"
        "No artificial caps — stops only on --duration-minutes if set.",
        title="SHADOW DEPLOY",
        border_style="magenta",
    ))
    activate(
        max_tokens=0,
        stop_ratio=0.00,
        max_turns=0,
        duration_minutes=duration_minutes,
        out="/tmp/shadow_sedona_mission.json",
        pdf=None,
        json_only=False,
        yes=yes,
    )


@app.command("seeds")
def seeds_show():
    """Show adaptively evolved SHADOW discovery seeds."""
    from .adaptive_seeds import AdaptiveSeedEngine
    from .targets import DEFAULT_SEEDS, DEFAULT_MISSION_ID

    engine = AdaptiveSeedEngine(DEFAULT_MISSION_ID, list(DEFAULT_SEEDS))
    ctx = engine.get_context()
    console.print(Panel.fit(
        f"Generation: {ctx['generation']}  |  Cycles: {ctx['evolution_cycles']}\n"
        f"Active pool: {ctx['active_seed_count']} records",
        title="SHADOW Adaptive Seeds",
        border_style="magenta",
    ))
    for s in engine.get_active_seeds(limit=12):
        console.print(f"  [cyan]•[/cyan] {s[:100]}")


if __name__ == "__main__":
    app()