"""Thin wrapper so services never touch raw credentials."""
from app.core.crypto import encrypt, decrypt


def store(plaintext: str) -> str:
    return encrypt(plaintext)


def retrieve(token: str) -> str:
    return decrypt(token)
