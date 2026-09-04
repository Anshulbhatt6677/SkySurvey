#!/usr/bin/env python3
"""Prove an NTRIP caster works, layer by layer, before blaming the app.

Each layer is checked independently so a failure names its own cause:

  1 DNS + TCP      is the caster reachable on this host/port at all
  2 SOURCETABLE    does it speak NTRIP, and what mountpoints exist
  3 AUTH           do the credentials open the mountpoint
  4 RTCM STREAM    are real, CRC-valid RTCM3 frames arriving
  5 CONTENT        are they the message types a ZED-F9P needs for RTK

Usage:
    python3 tools/ntrip_check.py --host HOST [--port 2101] [--mount NAME] [--user NAME]

The password is never taken on the command line (it would land in your shell
history); it is prompted for, or read from the NTRIP_PASS environment variable.
"""

import argparse
import getpass
import os
import socket
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gps.ntrip_client import fetch_sourcetable, _auth_header, USER_AGENT  # noqa: E402


# RTCM3 message types a ZED-F9P needs for an RTK fix.
BASE_POSITION = {1005, 1006}
MSM_OBSERVATIONS = {
    1074, 1075, 1076, 1077,   # GPS
    1084, 1085, 1086, 1087,   # GLONASS
    1094, 1095, 1096, 1097,   # Galileo
    1124, 1125, 1126, 1127,   # BeiDou
}
LEGACY_OBSERVATIONS = {1001, 1002, 1003, 1004, 1009, 1010, 1011, 1012}


def crc24q(data: bytes) -> int:
    """CRC-24Q as used by RTCM3. Proves a frame is genuine, not noise."""
    crc = 0
    for byte in data:
        crc ^= byte << 16
        for _ in range(8):
            crc <<= 1
            if crc & 0x1000000:
                crc ^= 0x1864CFB
    return crc & 0xFFFFFF


def parse_rtcm3(buf: bytearray):
    """Pulls complete, CRC-valid RTCM3 frames out of a rolling buffer.

    Returns (message_types, good_frames, bad_crc). Consumes what it uses.
    """
    types, good, bad = [], 0, 0
    while True:
        start = buf.find(b"\xd3")
        if start < 0:
            buf.clear()
            break
        if start:
            del buf[:start]
        if len(buf) < 6:
            break
        length = ((buf[1] & 0x03) << 8) | buf[2]
        frame_len = 3 + length + 3
        if len(buf) < frame_len:
            break
        frame = bytes(buf[:frame_len])
        got = int.from_bytes(frame[-3:], "big")
        if crc24q(frame[:-3]) == got:
            good += 1
            if length >= 2:
                types.append((frame[3] << 4) | (frame[4] >> 4))
            del buf[:frame_len]
        else:
            bad += 1
            del buf[:1]   # false preamble; resync one byte along
    return types, good, bad


def step(n, title):
    print(f"\n[{n}] {title}")


def main():
    ap = argparse.ArgumentParser(description="Diagnose an NTRIP caster end to end.")
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, default=2101)
    ap.add_argument("--mount", default=None, help="mountpoint; omit to only list them")
    ap.add_argument("--user", default="")
    ap.add_argument("--seconds", type=int, default=15, help="how long to sample the stream")
    ap.add_argument("--gga", default="", help="GGA sentence to push (needed by VRS mountpoints)")
    args = ap.parse_args()

    password = os.environ.get("NTRIP_PASS", "")
    if args.user and not password:
        password = getpass.getpass("NTRIP password (not echoed): ")

    print(f"NTRIP check -> {args.host}:{args.port}" + (f"/{args.mount}" if args.mount else ""))

    # ---- 1. reachability -------------------------------------------------
    step(1, "DNS + TCP reachability")
    try:
        ip = socket.gethostbyname(args.host)
        print(f"    resolves to {ip}")
    except OSError as e:
        print(f"    FAIL - cannot resolve '{args.host}': {e}")
        print("    -> check the hostname from your account approval.")
        return 1
    try:
        t0 = time.time()
        s = socket.create_connection((args.host, args.port), timeout=12)
        s.close()
        print(f"    TCP {args.port} open ({(time.time()-t0)*1000:.0f} ms)")
    except Exception as e:
        print(f"    FAIL - port {args.port} unreachable: {e}")
        print("    -> wrong port, or a firewall is blocking it. Common: 2101, 2102, 8080.")
        return 1

    # ---- 2. sourcetable --------------------------------------------------
    step(2, "NTRIP sourcetable")
    try:
        entries = fetch_sourcetable(args.host, args.port, args.user, password, timeout=15)
        print(f"    caster speaks NTRIP - {len(entries)} mountpoints:")
        for e in entries[:25]:
            print(f"      {e.label()}")
        if len(entries) > 25:
            print(f"      ... and {len(entries)-25} more")
    except Exception as e:
        print(f"    FAIL - {type(e).__name__}: {e}")
        print("    -> host answers TCP but is not an NTRIP caster on this port.")
        return 1

    if not args.mount:
        print("\nNo --mount given; stopping after the mountpoint list.")
        print("Re-run with --mount NAME to test authentication and the stream.")
        return 0

    # ---- 3. auth + 4. stream --------------------------------------------
    step(3, f"Authenticate and open '{args.mount}'")

    def build_request(ntrip_v2: bool) -> str:
        r = f"GET /{args.mount.lstrip('/')} HTTP/1.1\r\n"
        if ntrip_v2:
            r += f"Host: {args.host}:{args.port}\r\n"
            r += "Ntrip-Version: Ntrip/2.0\r\n"
        r += f"User-Agent: {USER_AGENT}\r\n"
        if args.user:
            r += _auth_header(args.user, password)
        r += "\r\n"
        return r

    def try_open(ntrip_v2: bool):
        """Opens the mountpoint. Returns (sock, first_response_line) or (None, line)."""
        sock = socket.create_connection((args.host, args.port), timeout=15)
        sock.sendall(build_request(ntrip_v2).encode("ascii"))
        sock.settimeout(1.0)
        header = b""
        while b"\r\n\r\n" not in header and b"ICY 200 OK\r\n" not in header:
            try:
                c = sock.recv(512)
            except socket.timeout:
                break
            if not c:
                break
            header += c
        line = header.decode("latin-1", "ignore").split("\r\n")[0]
        if "200" in line and ("ICY" in line or "OK" in line):
            return sock, line
        sock.close()
        return None, line

    buf = bytearray()
    types = Counter()
    good = bad = total = 0
    try:
        sock, first = try_open(ntrip_v2=True)
        print(f"    NTRIP v2 response: {first or '(none)'}")

        # Some casters (especially older government installs) only speak NTRIP 1.0
        # and reject the v2 handshake outright. Retry before blaming the password.
        if sock is None and "401" in first:
            sock2, first2 = try_open(ntrip_v2=False)
            print(f"    NTRIP v1 response: {first2 or '(none)'}")
            if sock2 is not None:
                print("    -> this caster requires NTRIP v1. Credentials are FINE.")
                print("       (tell me and I will switch the app's client to v1)")
                sock, first = sock2, first2
            else:
                first = first2 if "401" not in first2 else first

        with (sock or socket.socket()) as sock:
            if sock.fileno() == -1 or first is None:
                print("    FAIL - could not open the mountpoint.")
                return 1
            if "401" in first:
                print("    FAIL - credentials rejected on BOTH NTRIP v1 and v2.")
                print("    -> the request format is not the problem; the account is.")
                print("       Common cause: the web portal login is NOT the streaming")
                print("       login. Look in the portal for separate NTRIP/caster")
                print("       credentials, or for a mountpoint subscription to enable.")
                return 1
            if "404" in first:
                print("    FAIL - mountpoint does not exist. Pick one from step 2.")
                return 1
            if "SOURCETABLE" in first:
                print("    FAIL - caster returned the sourcetable: mountpoint name is wrong.")
                return 1
            if "200" not in first:
                print("    FAIL - caster refused the stream.")
                return 1
            print("    authenticated, stream opened")

            step(4, f"Sampling RTCM for {args.seconds}s")
            if args.gga:
                sock.sendall((args.gga.strip() + "\r\n").encode("ascii"))
                print("    pushed GGA upstream (required by VRS mountpoints)")

            t0 = time.time()
            last_gga = t0
            while time.time() - t0 < args.seconds:
                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        print("    caster closed the connection early")
                        break
                    total += len(chunk)
                    buf.extend(chunk)
                    t, g, b = parse_rtcm3(buf)
                    types.update(t); good += g; bad += b
                except socket.timeout:
                    pass
                if args.gga and time.time() - last_gga > 10:
                    sock.sendall((args.gga.strip() + "\r\n").encode("ascii"))
                    last_gga = time.time()
    except Exception as e:
        print(f"    FAIL - {type(e).__name__}: {e}")
        return 1

    rate = total / max(args.seconds, 1)
    print(f"    {total} bytes in {args.seconds}s  ({rate:.0f} B/s)")
    print(f"    RTCM3 frames: {good} valid, {bad} bad CRC")

    if total == 0:
        print("\n    NO DATA. The caster accepted you but sent nothing.")
        print("    -> This is the classic VRS symptom: pass --gga with a real GGA")
        print("       sentence so the caster knows where to place the virtual base.")
        return 1

    # ---- 5. content ------------------------------------------------------
    step(5, "Are these the messages a ZED-F9P needs?")
    if not types:
        print("    FAIL - data arrived but no valid RTCM3 frames were decoded.")
        print("    -> the stream may be RTCM 2.x or a proprietary format the F9P cannot use.")
        return 1
    for t, c in sorted(types.items()):
        tag = ""
        if t in BASE_POSITION:
            tag = "base station position"
        elif t in MSM_OBSERVATIONS:
            tag = "MSM observations (usable)"
        elif t in LEGACY_OBSERVATIONS:
            tag = "legacy observations"
        print(f"      {t:<5} x{c:<5} {tag}")

    has_pos = bool(set(types) & BASE_POSITION)
    has_msm = bool(set(types) & MSM_OBSERVATIONS)
    has_legacy = bool(set(types) & LEGACY_OBSERVATIONS)

    print()
    if has_pos and has_msm:
        print("    PASS - base position + MSM observations present.")
        print("    This caster can drive an RTK fix. If SkySurvey still shows 3D Fix,")
        print("    the problem is the antenna or the receiver, not the corrections.")
        return 0
    if not has_pos:
        print("    WARN - no 1005/1006 base position seen. Without the base coordinates")
        print("           the receiver cannot resolve ambiguities; RTK will not fix.")
    if not has_msm:
        if has_legacy:
            print("    WARN - only legacy observations. The F9P prefers MSM4/MSM7;")
            print("           ask the provider for an MSM mountpoint.")
        else:
            print("    WARN - no observation messages at all.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
