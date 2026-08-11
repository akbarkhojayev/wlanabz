#!/usr/bin/env python3
"""
WlanAbz — dizayn namunalari (tanlash uchun).
Ishga tushirish:  python3 dizayn_namuna.py
Logo o'zgarmaydi.
"""

import os
import sys

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    from rich.align import Align
    from rich.text import Text
except ImportError:
    print("rich kerak: pip install rich")
    sys.exit(1)

console = Console(highlight=False)

BANNER = r"""
 __        ___                _    _         
 \ \      / / | __ _ _ __    / \  | |__ ____ 
  \ \ /\ / /| |/ _` | '_ \  / _ \ | '_ \_  / 
   \ V  V / | | (_| | | | |/ ___ \| |_) / /  
    \_/\_/  |_|\__,_|_| |_/_/   \_\_.__/___| 
"""


def clear():
    os.system("clear" if os.name == "posix" else "cls")


def logo():
    console.print(f"[bold bright_cyan]{BANNER}[/bold bright_cyan]")
    console.print("[bold green]" + "=" * 57 + "[/bold green]")
    console.print(
        "[bold green]   Wi-Fi Dual-Band Tool by WlanAbz  ·  UBUNTU[/bold green]"
    )
    console.print("[bold green]" + "=" * 57 + "[/bold green]\n")


def pause():
    try:
        console.input("\n[dim]  Enter — keyingi namunaga...[/dim] ")
    except (KeyboardInterrupt, EOFError):
        pass


# ─── 1) AIRGEDDON YULDUZCHA ───────────────────────────
def style_1():
    clear()
    logo()
    console.print("[bold yellow]  NAMUNA 1 — Airgeddon (yulduzcha)[/bold yellow]\n")
    W = 55
    star = "*" * W
    console.print(f"[bold cyan]{star}[/bold cyan]")
    console.print(f"[bold cyan]*{' ' * (W-2)}*[/bold cyan]")
    for line, c in [
        ("     1)  Skaner + hujum", "green"),
        ("     2)  Faqat monitor", "cyan"),
        ("     3)  Tarmoqni tiklash", "yellow"),
        ("     0)  Chiqish", "white"),
    ]:
        fill = W - 2 - len(line)
        console.print(
            f"[bold cyan]*[/bold cyan][bold {c}]{line}[/bold {c}]"
            f"{' ' * fill}[bold cyan]*[/bold cyan]"
        )
    console.print(f"[bold cyan]*{' ' * (W-2)}*[/bold cyan]")
    console.print(f"[bold cyan]{star}[/bold cyan]")
    console.print("\n[green]  Tanlov > [/green]_")


# ─── 2) SODDA RO'YXAT ─────────────────────────────────
def style_2():
    clear()
    logo()
    console.print("[bold yellow]  NAMUNA 2 — Sodda ro'yxat[/bold yellow]\n")
    console.print("  Bosh menyu")
    console.print("  " + "─" * 28 + "\n")
    console.print("  [green]1[/green]  Skaner + hujum")
    console.print("  [cyan]2[/cyan]  Faqat monitor")
    console.print("  [yellow]3[/yellow]  Tarmoqni tiklash")
    console.print("  [white]0[/white]  Chiqish")
    console.print("\n  [?] Tanlov: _")


# ─── 3) BITTA PANEL (yumshoq) ─────────────────────────
def style_3():
    clear()
    logo()
    console.print("[bold yellow]  NAMUNA 3 — Bitta yumshoq panel[/bold yellow]\n")
    body = (
        "[green]1[/green]  Skaner + hujum\n"
        "[cyan]2[/cyan]  Faqat monitor\n"
        "[yellow]3[/yellow]  Tarmoqni tiklash\n"
        "[white]0[/white]  Chiqish"
    )
    console.print(
        Panel(
            body,
            title="[bold]Menyu[/bold]",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 3),
            width=40,
        )
    )
    console.print("\n  [?] Tanlov: _")


# ─── 4) IKKITA USTUN ──────────────────────────────────
def style_4():
    clear()
    logo()
    console.print("[bold yellow]  NAMUNA 4 — Ikki ustun (status + menyu)[/bold yellow]\n")
    left = (
        "[dim]Status[/dim]\n"
        "airmon   [green]ok[/green]\n"
        "airodump [green]ok[/green]\n"
        "hostapd  [green]ok[/green]\n"
        "mdk4     [green]ok[/green]"
    )
    right = (
        "[bold]Menyu[/bold]\n\n"
        "[green]1[/green] Skaner\n"
        "[cyan]2[/cyan] Monitor\n"
        "[yellow]3[/yellow] Tiklash\n"
        "[white]0[/white] Chiqish"
    )
    t = Table(show_header=False, expand=True, show_edge=False, box=None, padding=(0, 3))
    t.add_column()
    t.add_column()
    t.add_row(
        Panel(left, border_style="dim", box=box.SIMPLE, width=22),
        Panel(right, border_style="cyan", box=box.SIMPLE, width=22),
    )
    console.print(t)
    console.print("\n  [?] Tanlov: _")


# ─── 5) MATRIX / HACKER ───────────────────────────────
def style_5():
    clear()
    logo()
    console.print("[bold yellow]  NAMUNA 5 — Matrix / hacker[/bold yellow]\n")
    console.print("[green]  > SYSTEM ONLINE[/green]")
    console.print("[green]  > MODULE: wlp1s0mon[/green]")
    console.print("[green]  > MODE: ready[/green]\n")
    console.print("[bold green]  [01][/bold green] explore targets")
    console.print("[bold green]  [02][/bold green] monitor only")
    console.print("[bold green]  [03][/bold green] restore network")
    console.print("[bold green]  [00][/bold green] exit shell")
    console.print("\n[green]  root@wlanabz:~#[/green] _")


# ─── 6) KATTA RAQAMLAR ────────────────────────────────
def style_6():
    clear()
    logo()
    console.print("[bold yellow]  NAMUNA 6 — Katta raqamlar[/bold yellow]\n")
    items = [
        ("1", "SKANER + HUJUM", "green"),
        ("2", "FAQAT MONITOR", "cyan"),
        ("3", "TARMOQNI TIKLASH", "yellow"),
        ("0", "CHIQISH", "red"),
    ]
    for n, t, c in items:
        console.print(f"  [bold {c} on black]  {n}  [/bold {c} on black]  [bold]{t}[/bold]")
        console.print()
    console.print("  Tanlang (0-3): _")


# ─── 7) JADVAL MENYU ──────────────────────────────────
def style_7():
    clear()
    logo()
    console.print("[bold yellow]  NAMUNA 7 — Jadval menyu[/bold yellow]\n")
    t = Table(
        show_header=True,
        header_style="bold cyan",
        show_edge=True,
        box=box.SIMPLE_HEAVY,
        expand=False,
        padding=(0, 2),
    )
    t.add_column("#", style="bold", justify="center")
    t.add_column("Amal", style="white")
    t.add_column("Tavsif", style="dim")
    t.add_row("1", "Skaner", "Wi-Fi topish + hujum")
    t.add_row("2", "Monitor", "Faqat monitor rejim")
    t.add_row("3", "Tiklash", "NetworkManager qaytarish")
    t.add_row("0", "Chiqish", "Dasturdan chiqish")
    console.print(t)
    console.print("\n  [?] Tanlov: _")


# ─── 8) MINIMAL MARKAZ ────────────────────────────────
def style_8():
    clear()
    logo()
    console.print("[bold yellow]  NAMUNA 8 — Minimal markaz[/bold yellow]\n")
    console.print(Align.center("[bold]1[/bold]  skaner"))
    console.print(Align.center("[bold]2[/bold]  monitor"))
    console.print(Align.center("[bold]3[/bold]  tiklash"))
    console.print(Align.center("[bold]0[/bold]  chiqish"))
    console.print()
    console.print(Align.center("[dim]?[/dim]"))


# ─── 9) TARGET + JADVAL NAMUNA ────────────────────────
def style_9():
    clear()
    logo()
    console.print("[bold yellow]  NAMUNA 9 — Natija/jadval (skaner keyin)[/bold yellow]\n")
    t = Table(show_header=True, header_style="bold magenta", expand=True, show_edge=False)
    t.add_column("№", width=3)
    t.add_column("SSID", style="cyan bold")
    t.add_column("BSSID", style="yellow")
    t.add_column("CH", style="green", width=4)
    t.add_column("PWR", width=5)
    t.add_row("1", "Abbosxoja", "00:EB:D8:B1:44:47", "9", "-31")
    t.add_row("2", "Abbosxoja_5G", "00:EB:D8:B1:44:49", "40", "-46")
    t.add_row("3", "Natasha", "70:D3:13:71:57:30", "1", "-79")
    console.print(t)
    console.print()
    console.print("  [green]raqam[/green] = hujum   [yellow]r[/yellow] = qayta   [white]0[/white] = chiqish")
    console.print("\n  Tanlov > _")


# ─── 10) KOMBO: yulduzcha + sodda target ──────────────
def style_10():
    clear()
    logo()
    console.print("[bold yellow]  NAMUNA 10 — Kombo (yulduzcha + target)[/bold yellow]\n")
    console.print("[bold cyan]*******************************************[/bold cyan]")
    console.print("[bold cyan]*[/bold cyan]  SSID:   [cyan]Abbosxoja[/cyan]")
    console.print("[bold cyan]*[/bold cyan]  BSSID:  [yellow]00:EB:D8:B1:44:47[/yellow]")
    console.print("[bold cyan]*[/bold cyan]  CH:     [green]9[/green]  2.4 GHz   -31 dBm")
    console.print("[bold cyan]*******************************************[/bold cyan]\n")
    console.print("[bold cyan]*******************************************[/bold cyan]")
    console.print("[bold cyan]*[/bold cyan]     [red]1)[/red] Deauth")
    console.print("[bold cyan]*[/bold cyan]     [yellow]2)[/yellow] Evil Twin")
    console.print("[bold cyan]*[/bold cyan]     [cyan]3)[/cyan] Qayta skaner")
    console.print("[bold cyan]*[/bold cyan]     [green]4)[/green] Bosh menyu")
    console.print("[bold cyan]*[/bold cyan]     [white]0)[/white] Chiqish")
    console.print("[bold cyan]*******************************************[/bold cyan]")
    console.print("\n[green]  Tanlov > [/green]_")


STYLES = [
    ("1", "Airgeddon yulduzcha", style_1),
    ("2", "Sodda ro'yxat", style_2),
    ("3", "Bitta yumshoq panel", style_3),
    ("4", "Ikki ustun (status+menyu)", style_4),
    ("5", "Matrix / hacker", style_5),
    ("6", "Katta raqamlar", style_6),
    ("7", "Jadval menyu", style_7),
    ("8", "Minimal markaz", style_8),
    ("9", "Natija jadvali", style_9),
    ("10", "Kombo yulduzcha+target", style_10),
]


def main():
    while True:
        clear()
        logo()
        console.print("[bold white]  DIZAYN NAMUNALARI[/bold white]")
        console.print("  [dim]Logoga tegilmagan. Tanlang, ko'ring, raqam yuboring.[/dim]\n")
        for n, name, _ in STYLES:
            console.print(f"  [cyan]{n:>2}[/cyan]  {name}")
        console.print("  [cyan] a[/cyan]  Hammasini ketma-ket ko'rish")
        console.print("  [cyan] 0[/cyan]  Chiqish\n")
        try:
            c = console.input("  [green]Namuna raqami > [/green]").strip().lower()
        except (KeyboardInterrupt, EOFError):
            break
        if c in ("0", "q", "exit"):
            console.print("\n  Xayr! Tanlagan raqamingizni chatda yozing.\n")
            break
        if c == "a":
            for n, name, fn in STYLES:
                fn()
                pause()
            continue
        found = False
        for n, name, fn in STYLES:
            if c == n:
                fn()
                pause()
                found = True
                break
        if not found:
            console.print("[red]  Noto'g'ri[/red]")
            pause()


if __name__ == "__main__":
    main()
