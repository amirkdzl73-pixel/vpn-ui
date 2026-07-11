"""OpenConnect (ocserv) client connect/disconnect via the `openconnect` CLI.

Authenticates with the account's username/password (RADIUS PAP on the server).
The server cert is self-signed, so --no-cert-check. A single listener carries
both TLS (TCP) and DTLS (UDP) on the inbound port; the "tls" variant forces the
TLS data channel with --no-dtls, "dtls" leaves DTLS on (the default/fast path).
"""
from __future__ import annotations

import time

from .base import Client


def connect(client: Client, inbound, which: str, variant: str = "dtls",
            server_ip: str = "") -> tuple[bool, str, str]:
    """Bring up an OpenConnect tunnel for account A/B. Returns (ok, tunnel_ip, log)."""
    acct = inbound.accounts[which]
    port = inbound.udp_port
    if server_ip:
        client.pin_server_route(server_ip)

    no_dtls = "--no-dtls " if variant == "tls" else ""
    client.sh("pkill -f openconnect 2>/dev/null; rm -f /var/log/oc.log /run/oc.pid; true")
    # The server cert is self-signed and modern openconnect removed --no-cert-check,
    # so pin it. openconnect's native pin is pin-sha256:<base64> — the RFC7469
    # SHA-256 of the cert's SubjectPublicKeyInfo (NOT the cert-DER hash). Compute
    # that from the leaf cert over TLS. (Fall back to --no-cert-check for old
    # openconnect builds that still accept it.)
    _, fp = client.sh(
        f"echo | timeout 10 openssl s_client -connect {server_ip}:{port} 2>/dev/null | "
        "openssl x509 -pubkey -noout 2>/dev/null | "
        "openssl pkey -pubin -outform der 2>/dev/null | "
        "openssl dgst -sha256 -binary | openssl base64"
    )
    fp = fp.strip()
    trust = f"--servercert pin-sha256:{fp} " if fp else "--no-cert-check "
    # --interface=tun0 pins the device name so wait_iface('tun0') matches. openconnect
    # runs its bundled vpnc-script to configure the tunnel; --passwd-on-stdin feeds the
    # RADIUS password. --background daemonizes after the tunnel is up.
    cmd = (
        f"echo '{acct.password}' | openconnect --protocol=anyconnect "
        f"--user={acct.user} --passwd-on-stdin {trust}{no_dtls}"
        f"--interface=tun0 --background --pid-file=/run/oc.pid "
        f"{server_ip}:{port} >/var/log/oc.log 2>&1"
    )
    client.sh(cmd)

    ip = client.wait_iface("tun0", timeout=45)
    if ip:
        client.apply_tunnel_dns("tun0")
    _, log = client.sh("cat /var/log/oc.log 2>/dev/null | tail -n 40")
    if not ip:
        return False, "", f"tun0 never came up ({variant})\n{log}"
    time.sleep(2)
    _, log = client.sh("cat /var/log/oc.log 2>/dev/null | tail -n 40")
    return True, ip, log


def disconnect(client: Client):
    client.sh("kill $(cat /run/oc.pid 2>/dev/null) 2>/dev/null; "
              "pkill -f openconnect 2>/dev/null; true")
    time.sleep(2)
