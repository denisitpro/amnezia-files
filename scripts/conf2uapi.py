#!/usr/bin/env python3
"""Convert an AmneziaWG wg-quick style .conf into an amneziawg-go UAPI
"set" request.

Usage: conf2uapi.py path/to.conf > out.uapi

Mirrors go/internal/wgconf's Parse()/ToUAPI() key order and semantics
exactly (see that package), except for this script's own framing:
  - output starts with "set=1" and ends with one blank line (the UAPI
    terminator);
  - random_trailers/disable_cookies emit "true"/"false" instead of Go's
    "1"/"0" (amneziawg-go's UAPI parser accepts both via strconv.ParseBool).
Address/DNS/MTU/Table/PostUp/... are parsed (so unknown/repeated-key
errors match Go) but never emitted - ToUAPI doesn't use them either.
"""
import base64
import ipaddress
import socket
import sys

INTERFACE_MULTI_KEYS = {"address", "dns"}
PEER_MULTI_KEYS = {"allowedips"}

# Numeric/range fields passed through verbatim, in ToUAPI's key order.
# conf attribute name == UAPI key name for all of these.
INTERFACE_RANGE_KEYS = [
    "jc", "jmin", "jmax",
    "s1", "s2", "s3", "s4",
    "h1", "h2", "h3", "h4",
    "i1", "i2", "i3", "i4", "i5",
]

# (UAPI key, conf attribute key) pairs emitted after header_protection_key,
# in ToUAPI's order.
INTERFACE_TIMING_KEYS = [
    ("content_padding_addition", "contentpaddingaddition"),
    ("rekey_after_time", "rekeyaftertime"),
    ("rekey_timeout", "rekeytimeout"),
    ("reject_after_time", "rejectaftertime"),
    ("keepalive_timeout", "keepalivetimeout"),
    ("max_handshake_attempts", "maxhandshakeattempts"),
]


def die(msg):
    sys.stderr.write("conf2uapi.py: %s\n" % msg)
    sys.exit(1)


def split_list(s):
    """Mirrors wgconf.splitList: comma-split, trim, drop empties."""
    if not s:
        return []
    return [p.strip() for p in s.split(",") if p.strip()]


def parse_conf(text):
    """Mirrors wgconf.Parse: '#' strips to end of line, case-insensitive
    [Interface]/[Peer] sections and keys, address/dns/allowedips accumulate
    (comma-joined) across repeats, any other repeated key is an error."""
    iface = None
    peers = []
    section = None
    attrs = {}

    def flush():
        nonlocal iface
        if section == "interface":
            if iface is not None:
                die("multiple [Interface] sections")
            iface = dict(attrs)
        elif section == "peer":
            if not attrs.get("publickey"):
                die("[Peer] has no PublicKey")
            peers.append(dict(attrs))

    for raw in text.split("\n"):
        line = raw
        idx = line.find("#")
        if idx >= 0:
            line = line[:idx]
        line = line.strip()
        if not line:
            continue

        lower = line.lower()
        if lower in ("[interface]", "[peer]"):
            flush()
            section = "interface" if lower == "[interface]" else "peer"
            attrs = {}
            continue

        eq = line.find("=")
        if eq < 0:
            die("invalid line (no '='): %r" % line)
        key = line[:eq].strip().lower()
        value = line[eq + 1:].strip()

        if section is None:
            die("attribute %r outside of any section" % key)

        multi_ok = (section == "interface" and key in INTERFACE_MULTI_KEYS) or (
            section == "peer" and key in PEER_MULTI_KEYS
        )
        if key in attrs:
            if not multi_ok:
                die("multiple entries for key %r" % key)
            attrs[key] = attrs[key] + "," + value
        else:
            attrs[key] = value

    flush()

    if iface is None:
        die("no [Interface] section")
    if not iface.get("privatekey"):
        die("[Interface] has no PrivateKey")

    return iface, peers


def b64_key_to_hex(b64):
    """Mirrors wgconf.base64KeyToHex: standard base64, must decode to
    exactly 32 raw bytes, re-encoded as lowercase hex."""
    try:
        raw = base64.b64decode(b64, validate=True)
    except Exception as e:
        die("invalid base64 key: %s" % e)
        return ""  # unreachable, keeps type-checkers happy
    if len(raw) != 32:
        die("key has %d bytes, want 32" % len(raw))
    return raw.hex()


def uapi_bool(value):
    """Mirrors wgconf.uapiBool's on/off/1/0/true/false/yes recognition,
    but emits true/false (see module docstring)."""
    return "true" if value.strip().lower() in ("on", "1", "true", "t", "yes") else "false"


def resolve_host_port(hostport):
    """Mirrors wgconf.resolveHostPort: split host:port (bracketed for
    IPv6), resolve a hostname to an IP (IPv4-preferred), return "ip:port"
    (bracketed for IPv6)."""
    if hostport.startswith("["):
        end = hostport.find("]")
        if end < 0 or not hostport[end + 1:].startswith(":"):
            die("invalid endpoint %r" % hostport)
        host = hostport[1:end]
        port = hostport[end + 2:]
    else:
        if hostport.count(":") != 1:
            die("invalid endpoint %r" % hostport)
        host, _, port = hostport.partition(":")
    if not port:
        die("invalid endpoint %r" % hostport)

    try:
        ip = str(ipaddress.ip_address(host))
    except ValueError:
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror as e:
            die("resolving endpoint host %r: %s" % (host, e))
            return ""  # unreachable
        addrs = []
        seen = set()
        for family, _, _, _, sockaddr in infos:
            addr = sockaddr[0]
            if addr not in seen:
                seen.add(addr)
                addrs.append((family, addr))
        if not addrs:
            die("no addresses found for endpoint host %r" % host)
        ip = next((a for f, a in addrs if f == socket.AF_INET), addrs[0][1])

    return "[%s]:%s" % (ip, port) if ":" in ip else "%s:%s" % (ip, port)


def build_uapi_lines(iface, peers):
    """Mirrors wgconf.Config.ToUAPI's key order and semantics exactly."""
    lines = []

    lines.append("private_key=%s" % b64_key_to_hex(iface.get("privatekey", "")))

    listen_port = iface.get("listenport", "")
    if listen_port:
        lines.append("listen_port=%s" % listen_port)

    for key in INTERFACE_RANGE_KEYS:
        val = iface.get(key, "")
        if val:
            lines.append("%s=%s" % (key, val))

    hpk = iface.get("headerprotectionkey", "")
    if hpk:
        lines.append("header_protection_key=%s" % b64_key_to_hex(hpk))

    for uapi_key, conf_key in INTERFACE_TIMING_KEYS:
        val = iface.get(conf_key, "")
        if val:
            lines.append("%s=%s" % (uapi_key, val))

    random_trailers = iface.get("randomtrailers", "")
    if random_trailers:
        lines.append("random_trailers=%s" % uapi_bool(random_trailers))
    disable_cookies = iface.get("disablecookies", "")
    if disable_cookies:
        lines.append("disable_cookies=%s" % uapi_bool(disable_cookies))

    if peers:
        lines.append("replace_peers=true")

    for peer in peers:
        lines.append("public_key=%s" % b64_key_to_hex(peer.get("publickey", "")))

        psk = peer.get("presharedkey", "")
        if psk:
            lines.append("preshared_key=%s" % b64_key_to_hex(psk))

        endpoint = peer.get("endpoint", "")
        if endpoint:
            lines.append("endpoint=%s" % resolve_host_port(endpoint))

        keepalive = peer.get("persistentkeepalive", "") or "0"
        lines.append("persistent_keepalive_interval=%s" % keepalive)

        allowed_ips = split_list(peer.get("allowedips", ""))
        if allowed_ips:
            lines.append("replace_allowed_ips=true")
            for ip in allowed_ips:
                lines.append("allowed_ip=%s" % ip)

    return lines


def main():
    if len(sys.argv) != 2:
        die("usage: conf2uapi.py path/to.conf")

    try:
        with open(sys.argv[1], "r") as f:
            text = f.read()
    except OSError as e:
        die("reading %s: %s" % (sys.argv[1], e))
        return  # unreachable

    iface, peers = parse_conf(text)
    lines = build_uapi_lines(iface, peers)

    sys.stdout.write("set=1\n")
    for line in lines:
        sys.stdout.write(line + "\n")
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
