def show_selected_target_menu(target_bssid, target_info, monitor_iface):
    """Tanlangan tarmoqning xavfsizlik va xarakteristika tahlili."""
    print_banner()

    details = (
        f"[bold white]SSID (Tarmoq Nomi):[/bold white]"
        f" [cyan]{target_info['ssid']}[/cyan]\n"
        f"[bold white]BSSID (MAC Manzil):[/bold white]"
        f" [yellow]{target_bssid}[/yellow]\n"
        f"[bold white]Diapazon (Chastota):[/bold white]"
        f" [blue]{target_info['band']}[/blue]\n"
        f"[bold white]Ishchi Kanal (CH):[/bold white]"
        f" [green]{target_info['channel']}[/green]\n"
        f"[bold white]Signal Darajasi:[/bold white]"
        f" [magenta]{target_info['signal']} dBm[/magenta]\n"
        f"[bold white]Himoya Turi:[/bold white]"
        f" [blue]{target_info['crypto']}[/blue]"
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
            "\n[bold cyan][*] Tarmoq xavfsizligi va PMF (802.11w)"
            " tahlil qilinmoqda...[/bold cyan]"
        )
        time.sleep(1.5)
        if "WPA3" in target_info["crypto"]:
            console.print(
                "[bold green][+] Tarmoq WPA3 va PMF bilan himoyalangan."
                " Boshqaruv kadrlari shifrlangan.[/bold green]"
            )
        else:

	    sudo aireplay-ng --deauth 1000 -a target_bssid wlan0mon
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
