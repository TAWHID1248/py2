"""Fernet encryption keyed to the Windows machine GUID."""
import winreg
import hashlib
import base64
from cryptography.fernet import Fernet


def _machine_key() -> bytes:
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
        ) as key:
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
    except OSError:
        guid = "fallback-guid-bm2ultra"
    digest = hashlib.sha256(guid.encode()).digest()
    return base64.urlsafe_b64encode(digest)


_fernet = Fernet(_machine_key())


def encrypt(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet.decrypt(token.encode()).decode()
