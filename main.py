#!/usr/bin/env python3
"""
WlanAbz — Wi-Fi Scanner & Attack Tool by Abz
Ishga tushirish:  sudo python3 main.py
"""

from wlanabz import start, restore_all, _active_evil_twin, console

if __name__ == "__main__":
    try:
        start()
    except KeyboardInterrupt:
        console.print("\n[yellow]  To'xtatildi (Ctrl+C)[/yellow]")
        if _active_evil_twin:
            try:
                _active_evil_twin.stop()
            except Exception:
                pass
        restore_all()
        raise SystemExit(0)
