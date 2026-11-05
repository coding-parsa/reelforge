"""API keys at rest.

Windows: DPAPI (CryptProtectData) — the blob can only be read by the same
Windows user on the same machine, so a copied database leaks nothing.
Other OSes: file permissions plus an honest "plain:" prefix, so nobody is
misled into thinking it is encrypted.
"""
from __future__ import annotations

import base64
import os
import sys


def _dpapi(data: bytes, protect: bool) -> bytes:
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    blob_in = DATA_BLOB(len(data), ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_char)))
    blob_out = DATA_BLOB()
    fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    extra = [None, None, None, None, 0] if protect else [None, None, None, None, 0]
    if not fn(ctypes.byref(blob_in), *extra, ctypes.byref(blob_out)):
        raise OSError("DPAPI call failed")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(blob_out.pbData)


def protect(text: str) -> str:
    if not text:
        return ""
    raw = text.encode("utf-8")
    if sys.platform == "win32":
        try:
            return "dpapi:" + base64.b64encode(_dpapi(raw, True)).decode("ascii")
        except Exception:
            pass
    return "plain:" + base64.b64encode(raw).decode("ascii")


def unprotect(token: str) -> str:
    if not token:
        return ""
    try:
        kind, _, payload = token.partition(":")
        blob = base64.b64decode(payload)
        if kind == "dpapi":
            return _dpapi(blob, False).decode("utf-8")
        return blob.decode("utf-8")
    except Exception:
        return ""


def mask(token: str) -> str:
    """What the UI gets to see: never the key itself."""
    value = unprotect(token)
    if not value:
        return ""
    if len(value) <= 8:
        return "•" * len(value)
    return f"{value[:4]}…{value[-4:]}"
