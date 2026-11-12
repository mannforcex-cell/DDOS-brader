# MFX Blackhat Mode — L4/L7 Attack-Vector Engine

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Termux-lightgrey.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-lab--only-red.svg)]()

> ⚠️ **DISCLAIMER HUKUM**
> Tool ini dibuat **HANYA untuk uji ketahanan (authorized stress-testing)**, riset keamanan, CTF, dan lab pribadi. **DILARANG** digunakan terhadap sistem yang bukan milikmu atau tanpa izin tertulis dari pemilik. Penyalahgunaan = pelanggaran UU ITE Pasal 30–32 (Indonesia), CFAA (AS), Computer Misuse Act (UK), dan hukum pidana di hampir semua negara. Penulis **tidak bertanggung jawab** atas penyalahgunaan. Gunakan dengan risiko sendiri.

---

## 📌 Fitur

| Vektor | Layer | Butuh Root | Butuh Lib | Deskripsi |
|---|---|---|---|---|
| `syn`     | L4 | ✅ | scapy | TCP SYN flood + source spoof |
| `udp`     | L4 | ✅ | scapy | UDP flood + source spoof |
| `ack`     | L4 | ✅ | scapy | TCP ACK flood + source spoof |
| `dnsamp`  | L4 | ✅ | scapy | DNS amplification (source = target) |
| `h2reset` | L7 | ❌ | h2 | HTTP/2 Rapid Reset (CVE-2023-44487) |
| `rudy`    | L7 | ❌ | – | Slow POST body (R U Dead Yet) |
| `brute`   | L7 | ❌ | cloudscraper | Credential stuffing probe |
| `tlsfp`   | L7 | ❌ | curl_cffi | TLS/JA3 fingerprint spoof |
| `mix`     | all | ✅ | all | Semua vektor sekaligus |

---

## ⚡ Quick Install & Run (One-Liner)

### Linux / Kali / Ubuntu / Debian

```bash
git clone https://github.com/mannforcex-cell/DDOS-brader.git && cd mfx-blackhat && chmod +x install.sh && ./install.sh

sudo python3 DdosFkootbrader.py -A <TARGET_IP> P 80.443 T 500 -M mix -D 60 -X
