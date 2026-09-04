"""NTRIP client — pulls RTCM3 corrections from a caster and feeds them to the receiver.

RTK requires a correction stream from a base station or CORS network. The receiver
does the RTK computation itself; this module is the transport that gets the RTCM
bytes to it. Uses the standard library only (socket + base64), no extra dependency.
"""

import base64
import socket
import time
from typing import List, Optional

from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker


DEFAULT_NTRIP_PORT = 2101
USER_AGENT = "NTRIP SkySurvey/1.0"


class NtripSourceEntry:
    """One STR record from a caster sourcetable."""

    def __init__(self, mountpoint: str, identifier: str = "", fmt: str = ""):
        self.mountpoint = mountpoint
        self.identifier = identifier
        self.format = fmt

    def label(self) -> str:
        bits = [self.mountpoint]
        if self.identifier:
            bits.append(self.identifier)
        if self.format:
            bits.append(self.format)
        return "  |  ".join(bits)


def _auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Authorization: Basic {token}\r\n"


def fetch_sourcetable(host: str, port: int, username: str = "", password: str = "",
                      timeout: float = 10.0) -> List[NtripSourceEntry]:
    """Requests the caster's sourcetable and returns the available mountpoints.

    Raises OSError / RuntimeError on failure so the caller can surface the reason.
    """
    req = (
        f"GET / HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        f"Ntrip-Version: Ntrip/2.0\r\n"
        f"User-Agent: {USER_AGENT}\r\n"
    )
    if username:
        req += _auth_header(username, password)
    req += "Connection: close\r\n\r\n"

    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(req.encode("ascii"))
        chunks = []
        sock.settimeout(timeout)
        while True:
            try:
                buf = sock.recv(4096)
            except socket.timeout:
                break
            if not buf:
                break
            chunks.append(buf)
            if b"ENDSOURCETABLE" in b"".join(chunks[-2:]):
                break

    text = b"".join(chunks).decode("latin-1", errors="ignore")
    if "401" in text.split("\r\n")[0]:
        raise RuntimeError("Caster rejected credentials (HTTP 401)")

    entries = []
    for line in text.splitlines():
        if not line.startswith("STR;"):
            continue
        f = line.split(";")
        if len(f) > 1 and f[1]:
            entries.append(NtripSourceEntry(
                mountpoint=f[1],
                identifier=f[2] if len(f) > 2 else "",
                fmt=f[3] if len(f) > 3 else "",
            ))
    if not entries:
        raise RuntimeError("No mountpoints found in caster response")
    return entries


class NtripClientThread(QThread):
    """Streams RTCM3 from an NTRIP caster; emits the raw bytes for the receiver."""

    rtcm_received = Signal(bytes)            # raw RTCM3 to forward to the receiver
    status_changed = Signal(bool, str)       # (streaming, message)
    error_occurred = Signal(str)
    stats_updated = Signal(int, float)       # (total bytes, seconds since last data)

    # Network RTK / VRS mountpoints only start sending once they know roughly
    # where you are, so the client has to push its own GGA back up the socket.
    GGA_INTERVAL_SEC = 10.0

    def __init__(self, host: str, port: int, mountpoint: str,
                 username: str = "", password: str = "", parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self.mountpoint = mountpoint.lstrip("/")
        self.username = username
        self.password = password

        self.running = False
        self.total_bytes = 0
        self.last_data_time: Optional[float] = None

        self._gga: Optional[str] = None
        self._gga_lock = QMutex()
        self._gga_sent = False

    def set_gga(self, gga_sentence: str):
        """Stores the latest GGA so it can be pushed upstream for VRS casters."""
        if not gga_sentence:
            return
        with QMutexLocker(self._gga_lock):
            self._gga = gga_sentence.strip()

    def _take_gga(self) -> Optional[str]:
        with QMutexLocker(self._gga_lock):
            return self._gga

    def stop(self):
        self.running = False
        self.wait(2000)

    def run(self):
        self.running = True
        try:
            self._stream()
        except socket.timeout:
            self.error_occurred.emit("NTRIP timeout: caster did not respond")
        except (socket.gaierror, ConnectionRefusedError) as e:
            self.error_occurred.emit(f"NTRIP connection failed: {e}")
        except RuntimeError as e:
            self.error_occurred.emit(str(e))
        except Exception as e:
            self.error_occurred.emit(f"NTRIP error: {e}")
        finally:
            self.status_changed.emit(False, "Corrections stopped")

    def _stream(self):
        req = (
            f"GET /{self.mountpoint} HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            f"Ntrip-Version: Ntrip/2.0\r\n"
            f"User-Agent: {USER_AGENT}\r\n"
        )
        if self.username:
            req += _auth_header(self.username, self.password)
        req += "\r\n"

        with socket.create_connection((self.host, self.port), timeout=15.0) as sock:
            sock.sendall(req.encode("ascii"))
            sock.settimeout(1.0)

            header, leftover = self._read_header(sock)
            self._check_header(header)

            self.status_changed.emit(True, f"Streaming {self.mountpoint}")
            self.last_data_time = time.time()

            # An initial GGA gets VRS casters generating corrections immediately.
            self._push_gga(sock)
            last_gga = time.time()
            last_stats = 0.0

            if leftover:
                self._on_data(leftover)

            while self.running:
                try:
                    buf = sock.recv(4096)
                    if not buf:
                        raise RuntimeError("Caster closed the connection")
                    self._on_data(buf)
                except socket.timeout:
                    pass  # no data this tick; keep the loop alive to push GGA / stats

                now = time.time()
                # Send the very first position as soon as it exists rather than
                # waiting a full interval - a VRS caster sends nothing until it
                # knows where we are, so that delay is dead time at startup.
                due = now - last_gga >= self.GGA_INTERVAL_SEC
                if due or (not self._gga_sent and self._take_gga()):
                    self._push_gga(sock)
                    last_gga = now
                if now - last_stats >= 1.0:
                    age = now - self.last_data_time if self.last_data_time else 0.0
                    self.stats_updated.emit(self.total_bytes, age)
                    last_stats = now

    @staticmethod
    def _read_header(sock) -> tuple[str, bytes]:
        """Reads up to the end of the response header, returning any stream bytes after it."""
        buf = b""
        deadline = time.time() + 15.0
        while b"\r\n\r\n" not in buf and time.time() < deadline:
            try:
                chunk = sock.recv(1024)
            except socket.timeout:
                continue
            if not chunk:
                break
            buf += chunk
            # NTRIP v1 casters answer "ICY 200 OK" with no blank-line terminator.
            if buf.startswith(b"ICY 200 OK") and b"\r\n" in buf:
                head, _, rest = buf.partition(b"\r\n")
                return head.decode("latin-1", "ignore"), rest.lstrip(b"\r\n")
        head, _, rest = buf.partition(b"\r\n\r\n")
        return head.decode("latin-1", "ignore"), rest

    @staticmethod
    def _check_header(header: str):
        first = header.split("\r\n")[0] if header else ""
        if "200" in first and ("ICY" in first or "OK" in first):
            return
        if "401" in first:
            raise RuntimeError("Authentication failed — check username and password")
        if "404" in first:
            raise RuntimeError("Mountpoint not found on this caster")
        if "SOURCETABLE" in first:
            raise RuntimeError("Caster returned its sourcetable — the mountpoint name is wrong")
        raise RuntimeError(f"Caster refused the stream: {first or 'no response'}")

    def _on_data(self, buf: bytes):
        self.total_bytes += len(buf)
        self.last_data_time = time.time()
        self.rtcm_received.emit(buf)

    def _push_gga(self, sock):
        gga = self._take_gga()
        if not gga:
            return
        try:
            sock.sendall((gga + "\r\n").encode("ascii", errors="ignore"))
            self._gga_sent = True
        except OSError:
            pass  # caster may not accept upstream data; not fatal
