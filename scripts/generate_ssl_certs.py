#!/usr/bin/env python3
"""
AutoInsta - TLS / SSL Self-Signed Certificate Generator
Generates high-security X.509 self-signed certificates with Subject Alternative Names (SAN)
matching localhost, 127.0.0.1, and local LAN IPs for secure PC <-> Smartphone HTTPS traffic.
"""

import sys
import os
import socket
import ipaddress
import datetime
from pathlib import Path

# Force UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CERTS_DIR = PROJECT_ROOT / "certs"

def get_lan_ips():
    """Retrieves all detectable IPv4 addresses of this machine."""
    ips = set(["127.0.0.1"])
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    
    try:
        hostname = socket.gethostname()
        for addr in socket.getaddrinfo(hostname, None):
            ip = addr[4][0]
            if ":" not in ip: # IPv4
                ips.add(ip)
    except Exception:
        pass
    return sorted(list(ips))

def generate_self_signed_cert(output_dir: Path = CERTS_DIR):
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
    except ImportError:
        print("[!] The 'cryptography' library is required to generate SSL certificates.")
        print("    Install it via: pip install cryptography")
        return False

    output_dir.mkdir(parents=True, exist_ok=True)
    cert_path = output_dir / "cert.pem"
    key_path = output_dir / "key.pem"

    lan_ips = get_lan_ips()
    print(f"[*] Generating SSL/TLS private key (RSA 2048-bit)...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    print(f"[*] Configuring Subject Alternative Names (SAN) for: localhost, {', '.join(lan_ips)}")
    san_entries = [
        x509.DNSName("localhost"),
        x509.DNSName("autoinsta.local"),
    ]
    for ip_str in lan_ips:
        try:
            san_entries.append(x509.IPAddress(ipaddress.IPv4Address(ip_str)))
        except ValueError:
            pass

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "FR"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AutoInsta Autonomous Lab"),
        x509.NameAttribute(NameOID.COMMON_NAME, "AutoInsta Local Root"),
    ])

    now = datetime.datetime.now(datetime.timezone.utc)
    # 825 days validity (maximum allowed by modern browsers/OS without warning about excessive lifespan)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=825))
        .add_extension(
            x509.SubjectAlternativeName(san_entries),
            critical=False,
        )
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=0),
            critical=True,
        )
        .sign(private_key, hashes.SHA256())
    )

    # Save private key
    with open(key_path, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    # Save certificate
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"[✓] SSL Certificate successfully created:")
    print(f"    - Certificate : {cert_path}")
    print(f"    - Private Key : {key_path}")
    print(f"    - Valid for   : localhost, 127.0.0.1, {', '.join(lan_ips)}")
    return True

if __name__ == "__main__":
    generate_self_signed_cert()
