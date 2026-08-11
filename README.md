# WlanAbz

**Wi-Fi Scanner & Attack Tool by Abz**

Ubuntu / Kali uchun Wi‑Fi skaner va laboratoriya vositasi.

> ⚠️ Faqat **o‘z tarmog‘ingizda** yoki **ruxsat** bilan ishlating.

---

## O‘rnatish

```bash
sudo apt update
sudo apt install -y aircrack-ng hostapd dnsmasq iw iptables mdk4 \
  python3-scapy python3-pip xterm
pip3 install rich
```

---

## Ishga tushirish

```bash
cd ~/Desktop/ddos
sudo python3 main.py
```

**Root (`sudo`) shart.**

---

## Menyu

| # | Amal |
|---|------|
| **1** | Skaner va hujum |
| **2** | Tarmoqni tiklash |
| **0** | Chiqish |

### Skaner oqimi

1. Interfeys tanlanadi → monitor yoqiladi  
2. Yon oynada `airodump` ochiladi  
3. **Enter** — skaner tugaydi, jadval chiqadi  
4. Tarmoq raqamini tanlang  

### Target

| # | Amal |
|---|------|
| **1** | Uzish (deauth) — Ctrl+C to‘xtatadi |
| **2** | Soxta Wi-Fi (eviltwin) — portal `http://192.168.1.1/` |
| **3** | Qayta skaner |
| **4** | Bosh menyu |
| **0** | Chiqish |

**Evil Twin:** telefonda haqiqiy SSID ni **unutish** → ochiq twin ga ulanish → portal.

---

## Fayllar

| Fayl | Vazifa |
|------|--------|
| `main.py` | Ishga tushirish |
| `wlanabz.py` | Menyu va skaner |
| `wifi_util.py` | Monitor / tarmoq |
| `deauth_engine.py` | Deauth |
| `eviltwin.py` | Evil Twin |

---

## Muammolar

| Muammo | Yechim |
|--------|--------|
| Root talab | `sudo python3 main.py` |
| Monitor / busy | Menyu **2** yoki `sudo airmon-ng check kill` |
| 0 ta tarmoq | `sudo iw dev` → type **monitor** |
| Yon oyna yo‘q | `sudo apt install -y xterm` |
| Internet yo‘qoldi | Menyu **2** — Tarmoqni tiklash |

```bash
sudo systemctl restart NetworkManager
```

---

## Qisqa checklist

```text
[ ] sudo apt install aircrack-ng hostapd dnsmasq mdk4 xterm
[ ] pip3 install rich
[ ] sudo python3 main.py
[ ] 1 → skaner → target → deauth / eviltwin
[ ] Tugagach: 2 → tarmoqni tiklash
```

**Abz** · faqat qonuniy foydalanish.
