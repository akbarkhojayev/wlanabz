# WlanAbz

**Wi-Fi Scanner & Attack Tool by Abz**

Ubuntu va Kali Linux uchun o‘zbekcha interfeysli Wi‑Fi laboratoriya vositasi (airgeddon usuli).

> ⚠️ **Muhim:** Faqat **o‘zingizga tegishli** tarmoqda yoki **yozma ruxsat** bilan foydalaning. Boshqa tarmoqlarga ruxsatsiz hujum qonunga zid va jazo bilan yakunlanishi mumkin. Muallif noto‘g‘ri foydalanish uchun javobgar emas.

---

## Tarkib

- [Tizim talablari](#tizim-talablari)
- [O‘rnatish](#ornatish)
- [Ishga tushirish](#ishga-tushirish)
- [Asosiy menyu](#asosiy-menyu)
- [Qanday ishlatiladi](#qanday-ishlatiladi)
- [Imkoniyatlar](#imkoniyatlar)
- [Fayllar tuzilmasi](#fayllar-tuzilmasi)
- [Muammolarni bartaraf etish](#muammolarni-bartaraf-etish)
- [Qo‘llab-quvvatlash](#qollab-quvvatlash)
- [Litsenziya / javobgarlik](#litsenziya--javobgarlik)

---

## Tizim talablari

| Talab | Izoh |
|--------|------|
| OS | **Ubuntu** 22.04+ yoki **Kali Linux** (boshqa Debian asoslilar ham ishlashi mumkin) |
| Huquq | **root** (`sudo`) |
| Wi‑Fi | Monitor rejimini qo‘llab-quvvatlovchi adapter |
| Python | 3.8+ |
| Grafik terminal | Yon skaner oynasi uchun (`xterm` tavsiya) |

### Tavsiya etiladigan apparat

- **Yaxshi:** tashqi USB Wi‑Fi (Alfa, mt76x, RT5572 va h.k.) — monitor + AP
- **O‘rtacha:** noutbukning ichki Intel kartasi — ishlashi mumkin, lekin evil twin ba’zan cheklangan
- **Ideal:** 2 ta Wi‑Fi karta (bittasi AP, bittasi deauth)

---

## O‘rnatish

### 1. Loyihani olish

```bash
cd ~/Desktop/ddos
# yoki loyiha joylashgan papkaga o'ting
```

### 2. Tizim paketlari

```bash
sudo apt update
sudo apt install -y aircrack-ng hostapd dnsmasq iw iptables mdk4 \
  python3-scapy python3-pip xterm
```

Ubuntu da `mdk4` topilmasa:

```bash
sudo add-apt-repository -y universe
sudo apt update
sudo apt install -y mdk4
```

### 3. Python kutubxonasi

```bash
pip3 install rich
# yoki
sudo apt install -y python3-rich
```

### 4. Avtomatik o‘rnatish

Dastur birinchi marta `sudo` bilan ishga tushganda yetishmayotgan paketlarni o‘zi o‘rnatishga urinadi.

---

## Ishga tushirish

```bash
cd ~/Desktop/ddos
sudo python3 main.py
```

**Root shart.** Oddiy foydalanuvchi bilan ishlamaydi.

Ishga tushganda:
1. Qisqa **logo animatsiyasi** (markazda)
2. **Bosh menyu** ochiladi

Animatsiyani o‘tkazib yuborish uchun hozircha alohida bayroq yo‘q — kutib turing yoki keyingi versiyada qo‘shilishi mumkin.

---

## Asosiy menyu

| Tanlov | Vazifa |
|--------|--------|
| **1** | Skaner va hujum — to‘liq oqim |
| **2** | Tarmoqni tiklash — monitor/NM holatini qaytarish |
| **0** | Chiqish |

---

## Qanday ishlatiladi

### To‘liq oqim (1)

```
1) Skaner va hujum
   → Wi-Fi interfeys tanlash (bir nechta bo'lsa)
   → Monitor rejim (airmon-ng)
   → Yon oynada airodump-ng skaner
   → Enter — skaner to'xtaydi
   → Natijalar jadvali (faqat tarmoqlar)
   → Raqam — target tanlash
   → Hujum: Deauth yoki Soxta Wi-Fi
```

### Skaner

1. O‘ng tomonda **kichik terminal** ochiladi (`airodump-ng`).
2. Tarmoqlarni u yerda ko‘rasiz.
3. Asosiy oynada **Enter** — skaner yopiladi, natija jadvalga tushadi.
4. Jadvalda:
   - **raqam** — target tanlash
   - **r** — qayta skaner
   - **0** — chiqish / tiklash

Agar yon oyna ochilmasa, skaner shu terminalda ishlaydi (zaxira). `xterm` o‘rnating:

```bash
sudo apt install -y xterm
```

### Target menyusi

| Tanlov | Vazifa |
|--------|--------|
| **1** | **Uzish (Deauth)** — cheksiz deauth (Ctrl+C to‘xtatadi) |
| **2** | **Soxta Wi-Fi (Evil Twin)** — ochiq AP + portal + deauth |
| **3** | Qayta skaner |
| **4** | Bosh menyu |
| **0** | Chiqish |

### Deauth (1)

- Asl AP kanaliga sozlanadi
- `aireplay-ng` + `mdk4` (bor bo‘lsa) + client MAC
- **Ctrl+C** — to‘xtatish

### Soxta Wi-Fi / Evil Twin (2)

1. Telefonda haqiqiy tarmoqni **Unutish**
2. Dastur ochiq (parolsiz) twin AP chiqaradi
3. Telefondan shu SSID ga ulaning
4. Portal: `http://192.168.1.1/`
5. **Ctrl+C** — to‘xtatish

**Eslatma:** Saqlangan WPA parol haqiqiy APni afzal ko‘radi — shuning uchun «Unutish» muhim.

### Tarmoqni tiklash (2 — bosh menyu)

Monitor, hostapd, iptables tozalanadi, **NetworkManager** qayta yoqiladi.  
Internet yo‘qolsa yoki Wi‑Fi “yo‘qolsa” — shu menyuni ishlating.

```bash
# yoki qo'lda:
sudo airmon-ng stop wlan0mon   # mon nomingiz
sudo systemctl restart NetworkManager
```

---

## Imkoniyatlar

| Modul | Tavsif |
|--------|--------|
| Monitor | `airmon-ng` / `iw` (xavfsiz check kill — Python o‘ldirilmaydi) |
| Skaner | `airodump-ng` (2.4 + 5 GHz), scapy zaxira |
| Deauth | aireplay broadcast/directed + mdk4 + client sniff |
| Evil Twin | hostapd + dnsmasq + iptables captive + HTTP portal |
| Dual karta | 2 adapter bo‘lsa: AP + alohida deauth |
| UI | O‘zbekcha menyu, logo animatsiya |

---

## Fayllar tuzilmasi

```
ddos/
├── main.py           # Kirish nuqtasi (sudo python3 main.py)
├── wlanabz.py        # Asosiy dastur: menyu, skaner, UI
├── wifi_util.py      # Interfeys, airmon, paketlar
├── deauth_engine.py  # Deauth stack
├── eviltwin.py       # Evil Twin + portal
└── README.md         # Ushbu qo'llanma
```

---

## Muammolarni bartaraf etish

### `Root talab qilinadi`

```bash
sudo python3 main.py
```

### Monitor yoqilmaydi / `Device or resource busy`

```bash
sudo airmon-ng check kill
sudo airmon-ng start wlan0    # o'z iface nomingiz
sudo iw dev                   # type monitor bo'lishi kerak
```

Dasturni qayta ishga tushiring. Yoki bosh menyudan **Tarmoqni tiklash**, keyin qayta urinib ko‘ring.

### Skaner 0 ta tarmoq

- `sudo iw dev` → **type monitor**
- Router yaqinmi?
- `sudo rfkill list` → Soft blocked: **no**
- Yon oynada airodump ishlayaptimi?

### Yon oyna ochilmaydi

```bash
sudo apt install -y xterm
echo $DISPLAY   # bo'sh bo'lmasligi kerak (masalan :0)
```

### `AP iface yo'qoldi` (Evil Twin)

1. Bosh menyu → **Tarmoqni tiklash**
2. Qayta ishga tushirish
3. Imkon bo‘lsa tashqi USB Wi‑Fi ishlating

### Twin ga ulanadi, lekin portal yo‘q

1. Haqiqiy SSID ni telefonda **Unutish**
2. Ochiq twin ga ulanish
3. Brauzerda: `http://192.168.1.1/`
4. Logda `DHCPACK` / `PAROL` chiqishini kuzating

### Internet umuman yo‘qoldi

```bash
sudo python3 main.py
# → 2) Tarmoqni tiklash
```

yoki:

```bash
sudo systemctl restart NetworkManager
sudo nmcli radio wifi on
```

### mdk4 yo‘q

Dastur ishlayveradi (faqat aireplay). Kuchliroq deauth uchun:

```bash
sudo apt install -y mdk4
```

---

## Qo‘llab-quvvatlash

### O‘zingiz tekshiring

1. `sudo` bilan ishga tushirilganmi?
2. `airmon-ng`, `airodump-ng`, `hostapd` o‘rnatilganmi?
3. `sudo iw dev` — monitor / managed holati
4. Adapter monitor rejimini qo‘llab-quvvatlaydimi?

### Xato haqida xabar berishda yozing

- OS: Ubuntu / Kali + versiya  
- Adapter: model (masalan Intel AX200, Alfa AWUS…)  
- Buyruq: `sudo python3 main.py`  
- To‘liq xato matni  
- `sudo iw dev` chiqishi  
- Nima qilganingiz (skaner / deauth / twin)

### Foydali buyruqlar

```bash
# interfeyslar
sudo iw dev
sudo iwconfig

# radio
sudo rfkill list
sudo rfkill unblock all

# monitor
sudo airmon-ng check
sudo airmon-ng start wlan0
sudo airmon-ng stop wlan0mon

# tarmoqni qaytarish
sudo systemctl restart NetworkManager
```

### Muallif

**Abz** — WlanAbz  
Wi-Fi Scanner & Attack Tool by Abz

---

## Litsenziya / javobgarlik

- Vosita **ta’lim va o‘z tarmog‘ini test qilish** maqsadida.
- Ruxsatsiz tarmoqlarga hujum **taqiqlangan**.
- Foydalanish oqibatlari uchun mas’uliyat **foydalanuvchida**.
- Muallif hech qanday kafolat bermaydi (barqarorlik, zarar, qonuniy oqibatlar).

---

## Qisqa cheklist

```text
[ ] Ubuntu yoki Kali
[ ] sudo apt install aircrack-ng hostapd dnsmasq mdk4 xterm
[ ] pip3 install rich  /  python3-scapy
[ ] sudo python3 main.py
[ ] 1 → skaner → target → deauth yoki twin
[ ] Tugagach: 2 → Tarmoqni tiklash (yoki Ctrl+C restore)
```

**Omad — faqat qonuniy va o‘z tarmog‘ingizda.**
