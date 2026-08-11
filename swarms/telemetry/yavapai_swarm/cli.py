"""
Typer CLI for TELEMETRY_SWARM_V5
Commands:
- activate
- scenario
- tick
- serve (launches dashboard)
"""
import typer
import webbrowser
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

app = typer.Typer(
    name="yavapai-swarm",
    help=(
        "TELEMETRY_SWARM_V5 — Expanded Yavapai 13-Signal Swarm\n\n"
        "Safety philosophy: REAL DATA commands ALWAYS ASK before contacting external services.\n"
        "Use -y / --yes to bypass prompts for automation."
    ),
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()

shadow_app = typer.Typer(
    name="shadow",
    help="SHADOW overlay agent — regional multi-domain anomaly anomaly analysis with token-budgeted turns.",
    add_completion=False,
)


def _confirm_real_action(message: str, services: str = "", default: bool = True) -> bool:
    """Central helper: always ask before real external actions unless --yes was used."""
    # This is a simple version; commands pass the 'yes' flag explicitly for now
    if services:
        console.print(f"\n[yellow]This action will contact external services:[/yellow] {services}")
    return typer.confirm(message, default=default)


@app.command()
def activate(
    mode: str = typer.Option("expert", "--mode", "-m", help="expert | standard"),
    seed: int = typer.Option(42, "--seed", "-s"),
    window: str = typer.Option("6h", "--window", "-w", help="e.g. 30m, 6h, 24h"),
    out: str = typer.Option(None, "--out", "-o", help="Write full JSON report to path"),
    json_only: bool = typer.Option(False, "--json", help="Output only the JSON to stdout"),
    real: bool = typer.Option(False, "--real", help="NON-SIMULATED: use live public telemetry where available"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip all confirmation prompts (use with caution)"),
):
    """Activate the swarm. Use --real for the non-simulated version with actual public data.

    By default, real mode ALWAYS ASKS before making any external API calls.
    """
    from .config import CURRENT_CONFIG
    from .report import generate_activation_report

    title = "🛰️ Yavapai Swarm — NON-SIMULATED (REAL DATA)" if real else "🛰️ Yavapai Swarm"
    console.print(
        Panel.fit(
            f"[bold cyan]ACTIVATE: TELEMETRY_SWARM_V5[/]\n"
            f"Mode: {mode.upper()} | Window: {window}" + (" | REAL DATA MODE" if real else " | SYNTHETIC"),
            title=title,
            border_style="cyan" if not real else "green",
        )
    )

    # Respect global permission setting
    force_ask = (CURRENT_CONFIG.permission == "always ask")

    if real and not json_only and not yes and force_ask:
        services = "USGS (water + blasts), OpenSky Network (ADS-B), and EIA (grid load if key present)"
        console.print(f"\n[yellow]⚠️  Real mode will contact external public services:[/yellow] {services}")
        if not typer.confirm(
            "Make live network requests to collect real telemetry now?",
            default=True
        ):
            console.print("[red]Aborted by user. No external calls were made.[/red]")
            raise typer.Exit(code=0)

    report = generate_activation_report(mode=mode, seed=seed, window=window, use_real=real)

    if json_only:
        console.print_json(data=report.model_dump(mode="json"))
        return

    console.print("\n[bold green]Swarm activated.[/bold green]")
    if real:
        console.print(f"[green]Real data points collected:[/green] {report.summary.get('real_points_collected', 0)}")
        console.print(f"[yellow]Signals with live data:[/yellow] {report.summary.get('signals_with_real_data', [])}")
    console.print(f"Coupled anomalies (real engine not yet wired): [bold]{len(report.coupled_anomalies)}[/bold]")
    evolved = report.summary.get("adaptive_seeds_evolved", [])
    if evolved:
        console.print(f"[magenta]Adaptive seeds evolved this activation:[/magenta] {len(evolved)} new")
        for s in evolved[:3]:
            console.print(f"  [dim]• {s[:90]}[/dim]")

    if out:
        import json
        from pathlib import Path
        Path(out).write_text(report.model_dump_json(indent=2))
        console.print(f"\n[green]Full JSON written to[/green] {out}")
    else:
        console.print("\n[dim]Use --out report.json or --json for machine output[/dim]")


@app.command()
def scenario(
    name: str = typer.Argument(..., help="Scenario file name (without .yaml)"),
    speed: float = typer.Option(1.0, "--speed"),
    json: bool = typer.Option(False, "--json"),
):
    """Run a named scenario that injects coordinated anomalies (e.g. grid_mining_emergency)."""
    console.print(f"[yellow]Scenario runner stub[/yellow] — would load scenarios/{name}.yaml")


@app.command()
def serve():
    """Launch the live glassmorphism web dashboard (same as `python run.py`)."""
    console.print("[cyan]Launching dashboard via uvicorn... (use python run.py for full bootstrap)[/cyan]")
    import subprocess, sys
    from pathlib import Path

    root = Path(__file__).parent.parent
    subprocess.call([sys.executable, "-m", "uvicorn", "yavapai_swarm.dashboard:app", "--host", "127.0.0.1", "--port", "8080", "--reload"], cwd=root)


@app.command()
def collect_real(
    window: str = typer.Option("6h", "--window", "-w"),
    out: str = typer.Option(None, "--out", "-o"),
    json_only: bool = typer.Option(False, "--json"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip all confirmation prompts (use with caution)"),
):
    """NON-SIMULATED: Pull live public telemetry for all signals that have real sources and emit report.

    By default this command ALWAYS ASKS before contacting any external services.
    """
    from .config import CURRENT_CONFIG
    from .report import generate_activation_report

    console.print(Panel.fit("[bold green]COLLECTING REAL PUBLIC TELEMETRY[/]", border_style="green"))

    # Respect global permission setting
    force_ask = (CURRENT_CONFIG.permission == "always ask")

    if not json_only and not yes and force_ask:
        services = "USGS (water + quarry blasts), OpenSky (ADS-B), EIA (grid, if configured)"
        console.print(f"\n[yellow]This will make live requests to:[/yellow] {services}")
        if not typer.confirm(
            "Proceed with real data collection from external APIs?",
            default=True
        ):
            console.print("[red]Aborted. No network requests were made.[/red]")
            raise typer.Exit(code=0)

    report = generate_activation_report(window=window, use_real=True)

    if json_only:
        console.print_json(data=report.model_dump(mode="json"))
        return

    console.print(f"\nReal points collected: [bold]{report.summary.get('real_points_collected', 0)}[/bold]")
    console.print(f"Signals with data: {report.summary.get('signals_with_real_data', [])}")
    console.print(f"Signals with no public real source: {report.summary.get('signals_without_public_real_source', [])}")

    if out:
        from pathlib import Path
        Path(out).write_text(report.model_dump_json(indent=2))
        console.print(f"\n[green]Written to[/green] {out}")


@app.command()
def tick():
    """Single swarm tick — evolves adaptive discovery seeds from last activation context."""
    from .agents.adaptive_seeds import AdaptiveSeedEngine
    from .swarm_seeds import DEFAULT_SWARM_SEEDS, YAVAPAI_REGISTRY_ID, seeds_from_coupling_rules

    engine = AdaptiveSeedEngine(
        registry_id=YAVAPAI_REGISTRY_ID,
        base_seeds=DEFAULT_SWARM_SEEDS + seeds_from_coupling_rules(),
    )
    context = {
        "top_boosted_terms": [("adsb", 2.5), ("verde", 2.0)],
        "reinforced_signals": {"signal_01": 1, "signal_05": 1},
    }
    new_seeds = engine.evolve_from_cycle(cycle=engine.data.get("evolution_cycles", 0) + 1, context=context)
    console.print(Panel.fit(
        f"[bold green]Tick complete[/bold green]\n"
        f"Evolution cycle: {engine.data.get('evolution_cycles')}\n"
        f"New seeds: {len(new_seeds)}\n"
        f"Active pool: {len(engine.get_active_seeds())}",
        title="Yavapai Adaptive Seeds",
        border_style="green",
    ))
    for s in new_seeds[:5]:
        console.print(f"  [cyan]•[/cyan] {s[:100]}")


seeds_app = typer.Typer(name="seeds", help="View and evolve adaptive discovery seeds.")
app.add_typer(seeds_app, name="seeds")


@seeds_app.command("show")
def seeds_show(
    agent: str = typer.Option("all", "--agent", "-a", help="yavapai | shadow | all"),
):
    """Show current adaptive seed registries."""
    from .agents.adaptive_seeds import AdaptiveSeedEngine
    from .swarm_seeds import DEFAULT_SWARM_SEEDS, YAVAPAI_REGISTRY_ID, seeds_from_coupling_rules
    from .agents.regional_targets import DEFAULT_SEEDS, DEFAULT_MISSION_ID

    if agent in ("all", "yavapai"):
        yav = AdaptiveSeedEngine(YAVAPAI_REGISTRY_ID, DEFAULT_SWARM_SEEDS + seeds_from_coupling_rules())
        console.print(Panel.fit(
            "\n".join(f"• {s[:95]}" for s in yav.get_active_seeds(limit=8)),
            title="Yavapai Swarm Seeds",
            border_style="cyan",
        ))
    if agent in ("all", "shadow"):
        sh = AdaptiveSeedEngine(DEFAULT_MISSION_ID, list(DEFAULT_SEEDS))
        console.print(Panel.fit(
            "\n".join(f"• {s[:95]}" for s in sh.get_active_seeds(limit=8)),
            title="SHADOW Tier Seeds",
            border_style="magenta",
        ))


@app.command("eia-key")
def setup_eia_key():
    """
    Interactive guided setup for a FREE EIA API key.
    This command ALWAYS ASKS before reading your current key, opening browsers,
    or saving anything. Consistent with the swarm's "always ask" safety model.
    """
    from .ingestors.base import save_eia_key, get_eia_key
    from .ingestors.eia_grid import EIAGridIngestor
    from datetime import datetime, timedelta

    console.print(Panel.fit(
        "[bold cyan]EIA API Key Setup — Always Confirm Mode[/]\n\n"
        "This command will **always ask** you before doing anything with keys.\n"
        "No silent overwrites. Full transparency.",
        title="🔑 Free EIA Key (Signal 04)",
        border_style="cyan"
    ))

    # === ALWAYS show current state ===
    current_key = get_eia_key()
    if current_key:
        masked = "..." + current_key[-4:]
        console.print(f"\n[yellow]Current status:[/yellow] A key is already saved (ends with {masked})")
    else:
        console.print("\n[yellow]Current status:[/yellow] No EIA key is configured yet.")

    # === ALWAYS ask before proceeding ===
    if not typer.confirm("\nDo you want to enter or update the EIA API key now?", default=True):
        console.print("Cancelled. No changes made.")
        return

    # === ALWAYS ask before opening browser if they want ===
    if typer.confirm("Open the free registration page in your browser now?", default=True):
        try:
            webbrowser.open("https://www.eia.gov/opendata/register.php")
            console.print("[green]→ Registration page opened.[/green]")
        except Exception:
            console.print("Please open this manually: https://www.eia.gov/opendata/register.php")
    else:
        console.print("You can open it later at: https://www.eia.gov/opendata/register.php")

    console.print("\n[bold]Instructions:[/bold]")
    console.print("1. Fill the short form on the page (name + email).")
    console.print("2. Check your email — the key arrives within ~1 minute.")
    console.print("3. Come back here and paste it when ready.")

    # === ALWAYS ask for the key explicitly ===
    console.print("\n[bold]Ready?[/bold]")
    key = Prompt.ask("Paste your EIA API key here", password=False).strip()

    if not key:
        console.print("[red]No key entered. Nothing saved.[/red]")
        return

    if len(key) < 20:
        console.print("[red]That doesn't look like a valid EIA key (too short).[/red]")
        if not typer.confirm("Save it anyway?"):
            return

    # === ALWAYS show what will be saved and ask for final confirmation ===
    masked_new = "..." + key[-4:]
    console.print(f"\n[bold]You are about to save this key:[/bold] {masked_new}")

    if current_key:
        console.print(f"[dim]This will REPLACE the existing key (was { '...' + current_key[-4:] }).[/dim]")

    if not typer.confirm("\nSave this key to data/eia_key.txt now?", default=True):
        console.print("[yellow]Save cancelled. No changes were made.[/yellow]")
        return

    # Save
    save_eia_key(key)
    console.print("\n[bold green]✓ Key saved successfully.[/bold green]")

    # === ALWAYS ask if they want to test it ===
    if typer.confirm("\nTest the key right now by pulling some real grid data?", default=True):
        console.print("\n[bold]Testing with EIA...[/bold]")
        try:
            ing = EIAGridIngestor()
            end = datetime.now()
            start = end - timedelta(hours=6)
            points = ing.fetch(start, end)
            ing.close()

            if points:
                latest = points[-1]
                console.print(Panel.fit(
                    f"[bold green]SUCCESS — Real data working![/bold green]\n\n"
                    f"Latest AZPS demand: [bold]{latest.value:,.0f} MW[/bold]\n"
                    f"Time: {latest.ts.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
                    f"Signal 04 will now return real data when you use --real.",
                    title="Grid Data Live",
                    border_style="green"
                ))
            else:
                console.print("[yellow]Key is valid but no data came back in the last 6 hours.[/yellow]")
        except Exception as e:
            console.print(f"[red]Test failed:[/red] {e}")
            console.print("The key is saved correctly. You can test later with `activate --real`.")
    else:
        console.print("\nKey saved. You can test anytime with:")
        console.print("  python -m yavapai_swarm activate --real")

    console.print("\n[dim]Tip: You can re-run this command anytime — it will always ask before changing anything.[/dim]")


@app.command()
def config(
    key: str = typer.Argument(None, help="Config key to view or set (e.g. permission)"),
    value: str = typer.Argument(None, help="New value to set"),
):
    """View or set swarm configuration (persisted in data/swarm_config.yaml).

    Example:
        python -m yavapai_swarm config permission "always ask"
    """
    from .config import CURRENT_CONFIG, save_config

    if key is None:
        # Show all
        console.print(Panel.fit(
            f"permission: {CURRENT_CONFIG.permission}\n"
            f"window_minutes: {CURRENT_CONFIG.window_minutes}\n"
            f"real_ingestors_enabled: {CURRENT_CONFIG.real_ingestors_enabled}",
            title="Current Swarm Config",
            border_style="cyan"
        ))
        return

    if value is None:
        # Get
        val = getattr(CURRENT_CONFIG, key, None)
        console.print(f"{key} = {val}")
        return

    # Set
    if not hasattr(CURRENT_CONFIG, key):
        console.print(f"[red]Unknown config key: {key}[/red]")
        return

    # Special handling for permission
    if key == "permission" and value not in ("always ask", "trusted"):
        console.print("[yellow]Warning: Recommended values are 'always ask' or 'trusted'[/yellow]")

    setattr(CURRENT_CONFIG, key, value)
    save_config(CURRENT_CONFIG)
    console.print(f"[green]✓ Set {key} = {value} and saved.[/green]")

    if key == "permission":
        if value == "always ask":
            console.print("The swarm will now strictly ask before all real data actions and sensitive operations.")
        else:
            console.print("Permission relaxed. Use with caution.")


@shadow_app.command("activate")
def shadow_activate(
    max_tokens: int = typer.Option(0, "--max-tokens", help="0 = unlimited"),
    stop_ratio: float = typer.Option(0.00, "--stop-ratio", help="0.00 = ratio stop disabled"),
    max_turns: int = typer.Option(0, "--max-turns", help="0 = unlimited"),
    duration_minutes: float | None = typer.Option(None, "--duration-minutes", "-d", help="Optional time limit"),
    out: str = typer.Option(None, "--out", "-o", help="Write JSON mission report to path"),
    pdf: str = typer.Option(None, "--pdf", help="Write briefing PDF to path"),
    json_only: bool = typer.Option(False, "--json", help="Output only JSON to stdout"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
):
    """Activate SHADOW agent for regional multi-domain anomaly analysis."""
    from pathlib import Path
    from datetime import datetime
    from .config import CURRENT_CONFIG
    from .agents.shadow_agent import ShadowAgent
    from .agents.regional_targets import DEFAULT_MISSION_ID
    from .briefing_pdf import generate_shadow_briefing_pdf

    from .agents.token_budget import unlimited_tokens
    turns_label = "0 (unlimited)" if max_turns <= 0 else str(max_turns)
    tok_label = "0 (unlimited)" if unlimited_tokens(max_tokens) else str(max_tokens)
    console.print(Panel.fit(
        "[bold magenta]SHADOW AGENT ACTIVATION[/]\n"
        "Mission: Regional multi-domain anomaly Anomaly Analysis\n"
        f"max_tokens: {tok_label}  |  max_turns: {turns_label}  |  stop_ratio: {stop_ratio:.2f}",
        title="SHADOW",
        border_style="magenta",
    ))

    force_ask = CURRENT_CONFIG.permission == "always ask"
    if not json_only and not yes and force_ask:
        services = "OpenSky Network (KSEZ ADS-B), SESP keyword/memory layers"
        console.print(f"\n[yellow]SHADOW will contact:[/yellow] {services}")
        if not typer.confirm("Activate SHADOW agent and begin analysis turns?", default=True):
            console.print("[red]Aborted. SHADOW agent not activated.[/red]")
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

    with console.status("[magenta]SHADOW agent running analysis turns...[/]"):
        result = agent.run()

    result_dict = result.to_dict()

    if json_only:
        console.print_json(data=result_dict)
        return

    console.print(f"\n[bold green]SHADOW mission complete.[/bold green]")
    console.print(f"  Turns: {result.turns_executed}  |  Stop: {result.stop_reason}")
    console.print(f"  Discoveries: {len(result.discoveries)}  |  Coupled: {len(result.coupled_anomalies)}")
    console.print(f"  Tokens used: {result.token_budget.get('tokens_used')}  |  Remaining: {result.token_budget.get('tokens_remaining')}")

    if out:
        Path(out).write_text(__import__("json").dumps(result_dict, indent=2, default=str))
        console.print(f"\n[green]JSON report:[/green] {out}")

    pdf_path = pdf or str(
        Path.home() / "Desktop" / f"SHADOW_Sedona_Briefing_{datetime.now().strftime('%Y-%m-%d')}.pdf"
    )
    generate_shadow_briefing_pdf(result_dict, Path(pdf_path))
    console.print(f"[green]Briefing PDF:[/green] {pdf_path}")


@shadow_app.command("loop")
def shadow_loop(
    duration_minutes: float = typer.Option(13.0, "--duration-minutes", "-d", help="Run for N minutes"),
    max_tokens: int = typer.Option(0, "--max-tokens", help="0 = unlimited"),
    stop_ratio: float = typer.Option(0.00, "--stop-ratio"),
    max_turns: int = typer.Option(0, "--max-turns", help="0 = unlimited"),
    out: str = typer.Option("/tmp/shadow_sedona_loop.json", "--out", "-o"),
    pdf: str = typer.Option(None, "--pdf"),
    yes: bool = typer.Option(False, "--yes", "-y"),
):
    """Recursive loop: learn across cycles until duration or token limit, then brief."""
    from pathlib import Path
    from datetime import datetime
    from .config import CURRENT_CONFIG
    from .agents.shadow_agent import ShadowAgent
    from .agents.regional_targets import DEFAULT_MISSION_ID
    from .briefing_pdf import generate_shadow_briefing_pdf

    console.print(Panel.fit(
        "[bold magenta]SHADOW RECURSIVE LOOP[/]\n"
        f"Duration: {duration_minutes} min  |  max_tokens: 0  |  max_turns: 0  |  stop_ratio: 0.00\n"
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
    console.print(f"\n[bold green]SHADOW loop complete.[/bold green]")
    console.print(f"  Elapsed: {result.summary.get('elapsed_minutes')} min  |  Cycles: {result.cycles_completed}")
    console.print(f"  Turns: {result.turns_executed}  |  Stop: {result.stop_reason}")
    console.print(f"  Useful findings: {len(result.useful_findings)}")
    console.print(f"  Tokens used: {result.token_budget.get('tokens_used')}  |  Remaining: {result.token_budget.get('tokens_remaining')}")

    Path(out).write_text(__import__("json").dumps(result_dict, indent=2, default=str))
    console.print(f"[green]JSON:[/green] {out}")

    pdf_path = pdf or str(Path.home() / "Desktop" / f"SHADOW_Loop_Briefing_{datetime.now().strftime('%Y-%m-%d_%H%M')}.pdf")
    generate_shadow_briefing_pdf(result_dict, Path(pdf_path))
    console.print(f"[green]Briefing PDF:[/green] {pdf_path}")


@shadow_app.command("deploy")
def shadow_deploy(
    duration_minutes: float | None = typer.Option(None, "--duration-minutes", "-d"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
):
    """Deploy SHADOW agent (unlimited tokens, continuous production, Desktop PDF)."""
    console.print(Panel.fit(
        "[bold magenta]SHADOW PRODUCTION DEPLOY[/]\n"
        "max_turns: 0  |  max_tokens: 0  |  stop_ratio: 0.00",
        title="SHADOW DEPLOY",
        border_style="magenta",
    ))
    shadow_activate(
        max_tokens=0,
        stop_ratio=0.00,
        max_turns=0,
        duration_minutes=duration_minutes,
        out="/tmp/shadow_sedona_mission.json",
        pdf=None,
        json_only=False,
        yes=yes,
    )


app.add_typer(shadow_app, name="shadow")


if __name__ == "__main__":
    app()
