#!/usr/bin/env python3
"""Crypto manager — AES-256-GCM encryption for C2 comms."""
import os
import hashlib
import struct
from typing import Optional

try:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

class CryptoManager:
    """AES-256-GCM encryption with per-session keys."""
    def __init__(self):
        self.key = None
        self.counter = 0

    def derive_key(self, seed: str):
        """Derive a 256-bit key from a seed string."""
        # PBKDF2-like derivation
        self.key = hashlib.pbkdf2_hmac("sha256",
            seed.encode("utf-8"),
            b"absolutespy_framework_salt",
            10000,
            dklen=32)

    def set_key(self, key: bytes):
        """Set the encryption key directly."""
        if len(key) != 32:
            raise ValueError("Key must be 32 bytes")
        self.key = key

    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt data with AES-256-GCM. Returns [nonce(12)][ciphertext+tag]."""
        if not self.key:
            return plaintext  # No encryption if key not set
        if not HAS_CRYPTO:
            # Fallback: XOR encryption (weak, for environments without pycryptodome)
            return self._xor_encrypt(plaintext)

        nonce = get_random_bytes(12)
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext)
        return nonce + ciphertext + tag

    def decrypt(self, data: bytes) -> bytes:
        """Decrypt AES-256-GCM data. Expects [nonce(12)][ciphertext+tag]."""
        if not self.key:
            return data
        if not HAS_CRYPTO:
            return self._xor_decrypt(data)

        if len(data) < 28:  # 12 nonce + 16 tag minimum
            return data
        nonce = data[:12]
        ciphertext = data[12:-16]
        tag = data[-16:]
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag)

    def _xor_encrypt(self, data: bytes) -> bytes:
        """Simple XOR fallback (NOT secure — use only when pycryptodome unavailable)."""
        if not self.key:
            return data
        nonce = os.urandom(8)
        result = bytearray()
        for i, b in enumerate(data):
            result.append(b ^ self.key[i % len(self.key)])
        return nonce + bytes(result)

    def _xor_decrypt(self, data: bytes) -> bytes:
        """XOR decrypt fallback."""
        if not self.key or len(data) < 8:
            return data
        payload = data[8:]
        result = bytearray()
        for i, b in enumerate(payload):
            result.append(b ^ self.key[i % len(self.key)])
        return bytes(result)

    @staticmethod
    def generate_key() -> bytes:
        """Generate a random 256-bit key."""
        return os.urandom(32)

    @staticmethod
    def key_to_hex(key: bytes) -> str:
        return key.hex()

    @staticmethod
    def hex_to_key(hex_str: str) -> bytes:
        return bytes.fromhex(hex_str)
