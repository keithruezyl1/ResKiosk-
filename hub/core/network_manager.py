import socket
import threading
import time
from typing import Dict, List
from datetime import datetime, timedelta

class ConnectedKiosk:
    def __init__(self, kiosk_id: str, ip: str, status: str = "online"):
        self.kiosk_id = kiosk_id
        self.ip = ip
        self.status = status
        self.last_seen = datetime.utcnow()

class NetworkManager:
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self):
        self.connected_kiosks: Dict[str, ConnectedKiosk] = {}
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = cls()
        return cls._instance

    def detect_ip(self) -> str:
        """
        Detects the LAN IP address of the machine.
        Uses multiple strategies to work both online and offline:
        1. UDP socket trick to 8.8.8.8 (works when online, doesn't send data)
        2. UDP socket trick to a local broadcast address (works offline on LAN)
        3. gethostbyname fallback (works offline)
        4. Final fallback: 127.0.0.1
        """
        # Strategy 1: UDP socket to public DNS (works when internet route exists)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            if ip and ip != "0.0.0.0":
                return ip
        except Exception:
            pass

        # Strategy 2: UDP socket to local broadcast (works offline on LAN)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1)
            # Use a non-routable address on the local subnet
            s.connect(("192.168.255.255", 1))
            ip = s.getsockname()[0]
            s.close()
            if ip and ip != "0.0.0.0":
                return ip
        except Exception:
            pass

        # Strategy 3: gethostbyname (works offline, may return wrong IP on multi-homed)
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            if ip and ip != "127.0.0.1" and ip != "0.0.0.0":
                return ip
        except Exception:
            pass
        
        # Strategy 4: Enumerate all addresses via getaddrinfo
        try:
            hostname = socket.gethostname()
            addrs = socket.getaddrinfo(hostname, None, socket.AF_INET)
            for addr in addrs:
                ip = addr[4][0]
                if ip and ip != "127.0.0.1" and ip != "0.0.0.0":
                    return ip
        except Exception:
            pass

        return "127.0.0.1"

    def register_heartbeat(self, kiosk_id: str, ip: str, status: str):
        with self._lock:
            if kiosk_id in self.connected_kiosks:
                k = self.connected_kiosks[kiosk_id]
                k.ip = ip
                k.status = status
                k.last_seen = datetime.utcnow()
            else:
                self.connected_kiosks[kiosk_id] = ConnectedKiosk(kiosk_id, ip, status)

    def register_ping(self, kiosk_id: str, ip: str):
        self.register_heartbeat(kiosk_id, ip, "online")

    def get_connected_count(self) -> int:
        with self._lock:
            now = datetime.utcnow()
            active = [k for k in self.connected_kiosks.values() if (now - k.last_seen).total_seconds() < 60]
            return len(active)

    def get_connected_kiosks(self) -> List[dict]:
        with self._lock:
            now = datetime.utcnow()
            active = [k for k in self.connected_kiosks.values() if (now - k.last_seen).total_seconds() < 60]
            return [
                {
                    "kiosk_id": k.kiosk_id,
                    "ip": k.ip,
                    "last_seen": k.last_seen.isoformat(),
                    "status": k.status
                }
                for k in active
            ]

    def _cleanup_loop(self):
        while True:
            time.sleep(10)
            with self._lock:
                now = datetime.utcnow()
                stale = [k_id for k_id, k in self.connected_kiosks.items() if (now - k.last_seen).total_seconds() > 60]
                for k_id in stale:
                    del self.connected_kiosks[k_id]

network_manager = NetworkManager.get_instance()
