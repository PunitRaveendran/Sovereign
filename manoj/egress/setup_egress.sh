#!/bin/bash
# Sovereign — Egress firewall setup script
# Run as root on the demo machine (or inside a privileged container).
# Purpose: prove that the AI workbench makes ZERO external network calls.
#
# Strategy:
#   1. Allow established/related traffic so existing connections stay up.
#   2. Allow loopback (127.0.0.1) — all Sovereign services communicate locally.
#   3. Allow LAN only for intra-team traffic (optional — remove for full air-gap).
#   4. DROP everything else outbound.

set -euo pipefail

LOOPBACK="lo"
LAN_CIDR="192.168.0.0/16"     # adjust to your local subnet

echo "[*] Flushing existing OUTPUT rules..."
iptables -F OUTPUT

echo "[*] Allow loopback..."
iptables -A OUTPUT -o "$LOOPBACK" -j ACCEPT

echo "[*] Allow already-established connections..."
iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

echo "[*] Allow LAN (optional — comment out for full air-gap)..."
iptables -A OUTPUT -d "$LAN_CIDR" -j ACCEPT

echo "[*] DROP everything else..."
iptables -A OUTPUT -j DROP

echo "[*] Current OUTPUT rules:"
iptables -L OUTPUT -v -n

echo "[+] Egress firewall active. All external traffic is blocked."
