#!/usr/bin/env python3
"""
WlanAbz — O'zbekcha Airgeddon.
Kirish: sudo python3 main.py
"""

from test2 import main, restore_all, _active_evil_twin, console

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow][!] Ctrl+C[/yellow]")
        if _active_evil_twin:
            try:
                _active_evil_twin.stop()
            except Exception:
                pass
        restore_all()
        raise SystemExit(0)
