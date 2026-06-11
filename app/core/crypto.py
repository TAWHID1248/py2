"""Fernet encryption keyed to a machine-specific identifier."""
import hashlib
import base64
import sys
from cryptography.fernet import Fernet


def _machine_key() -> bytes:
    guid = "fallback-guid-bm2ultra"
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
            ) as key:
                guid, _ = winreg.QueryValueEx(key, "MachineGuid")
        except OSError:
            pass
    elif sys.platform == "darwin":
        try:
            import subprocess
            result = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True, text=True
            )
            for line in result.stdout.splitlines():
                if "IOPlatformUUID" in line:
                    guid = line.split('"')[-2]
                    break
        except Exception:
            pass
    digest = hashlib.sha256(guid.encode()).digest()
    return base64.urlsafe_b64encode(digest)


_fernet = Fernet(_machine_key())


def encrypt(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet.decrypt(token.encode()).decode()
