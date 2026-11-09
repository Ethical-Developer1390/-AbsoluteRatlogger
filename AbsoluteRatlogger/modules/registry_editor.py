#!/usr/bin/env python3
"""Registry editor — read/write/create/delete registry values."""
import platform

def read(key_path, value_name=None):
    """Read a registry value or all values under a key."""
    if platform.system() != "Windows":
        return b"error: registry requires Windows"
    try:
        import winreg
        root, subkey = _parse_key(key_path)
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ) as k:
            if value_name:
                val, typ = winreg.QueryValueEx(k, value_name)
                return f"{value_name} = {val} (type={typ})".encode()
            else:
                # Enumerate all values
                results = []
                i = 0
                while True:
                    try:
                        name, val, typ = winreg.EnumValue(k, i)
                        results.append(f"  {name} = {val} (type={typ})")
                        i += 1
                    except OSError:
                        break
                # Also enumerate subkeys
                j = 0
                subkeys = []
                while True:
                    try:
                        subkeys.append(winreg.EnumKey(k, j))
                        j += 1
                    except OSError:
                        break
                result = f"Key: {key_path}\nValues:\n" + "\n".join(results)
                if subkeys:
                    result += f"\nSubkeys: {', '.join(subkeys)}"
                return result.encode()
    except FileNotFoundError:
        return b"error: key not found"
    except Exception as e:
        return f"error: {e}".encode()

def write(key_path, value_name, data, reg_type="REG_SZ"):
    """Write a registry value."""
    if platform.system() != "Windows":
        return b"error: registry requires Windows"
    try:
        import winreg
        root, subkey = _parse_key(key_path)
        type_map = {
            "REG_SZ": winreg.REG_SZ,
            "REG_DWORD": winreg.REG_DWORD,
            "REG_BINARY": winreg.REG_BINARY,
            "REG_EXPAND_SZ": winreg.REG_EXPAND_SZ,
            "REG_MULTI_SZ": winreg.REG_MULTI_SZ,
        }
        rt = type_map.get(reg_type, winreg.REG_SZ)

        with winreg.CreateKeyEx(root, subkey, 0, winreg.KEY_SET_VALUE) as k:
            if rt == winreg.REG_DWORD:
                data = int(data)
            winreg.SetValueEx(k, value_name, 0, rt, data)
        return f"ok: wrote {value_name} = {data} to {key_path}".encode()
    except Exception as e:
        return f"error: {e}".encode()

def create_key(key_path):
    """Create a registry key."""
    if platform.system() != "Windows":
        return b"error: registry requires Windows"
    try:
        import winreg
        root, subkey = _parse_key(key_path)
        with winreg.CreateKeyEx(root, subkey, 0, winreg.KEY_WRITE) as k:
            pass
        return f"ok: created {key_path}".encode()
    except Exception as e:
        return f"error: {e}".encode()

def delete_value(key_path, value_name):
    """Delete a registry value."""
    if platform.system() != "Windows":
        return b"error: registry requires Windows"
    try:
        import winreg
        root, subkey = _parse_key(key_path)
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, value_name)
        return f"ok: deleted {value_name} from {key_path}".encode()
    except FileNotFoundError:
        return b"error: value not found"
    except Exception as e:
        return f"error: {e}".encode()

def delete_key(key_path):
    """Delete a registry key (must be empty)."""
    if platform.system() != "Windows":
        return b"error: registry requires Windows"
    try:
        import winreg
        root, subkey = _parse_key(key_path)
        winreg.DeleteKey(root, subkey)
        return f"ok: deleted {key_path}".encode()
    except Exception as e:
        return f"error: {e}".encode()

def _parse_key(key_path):
    """Parse a registry path like HKLM\Software\Microsoft\..."""
    roots = {
        "HKLM": winreg.HKEY_LOCAL_MACHINE,
        "HKCU": winreg.HKEY_CURRENT_USER,
        "HKCR": winreg.HKEY_CLASSES_ROOT,
        "HKU": winreg.HKEY_USERS,
        "HKCC": winreg.HKEY_CURRENT_CONFIG,
    }
    parts = key_path.split("\\", 1)
    root_name = parts[0].upper()
    root = roots.get(root_name)
    if root is None:
        raise ValueError(f"Unknown root: {root_name}")
    subkey = parts[1] if len(parts) > 1 else ""
    return root, subkey

# Import winreg at module level for _parse_key
if platform.system() == "Windows":
    import winreg
