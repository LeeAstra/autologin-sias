"""Fresh Windows WLAN observations; no subprocesses or cached connection state."""
import ctypes as C
import os
from functools import cache

DWORD = C.c_uint32
ENUM = C.c_int32
HANDLE = C.c_void_p

class GUID(C.Structure):
    _fields_ = [('data1', DWORD), ('data2', C.c_uint16),
                ('data3', C.c_uint16), ('data4', C.c_ubyte * 8)]

class Interface(C.Structure):
    _fields_ = [('guid', GUID), ('description', C.c_uint16 * 256), ('state', ENUM)]

class ListHeader(C.Structure):
    _fields_ = [('count', DWORD), ('index', DWORD)]

class SSID(C.Structure):
    _fields_ = [('length', DWORD), ('value', C.c_ubyte * 32)]

class Association(C.Structure):
    _fields_ = [('ssid', SSID), ('bss_type', ENUM), ('bssid', C.c_ubyte * 6),
                ('phy_type', ENUM), ('phy_index', DWORD), ('quality', DWORD),
                ('rx_rate', DWORD), ('tx_rate', DWORD)]

class Security(C.Structure):
    _fields_ = [('enabled', ENUM), ('one_x', ENUM), ('authentication', ENUM), ('cipher', ENUM)]

class Connection(C.Structure):
    _fields_ = [('state', ENUM), ('mode', ENUM), ('profile', C.c_uint16 * 256),
                ('association', Association), ('security', Security)]

@cache
def _load_api():
    # Cache only immutable DLL bindings, never Wi-Fi observations or handles.
    # Restrict loading to System32: never load a WLAN DLL from the install directory.
    api = C.WinDLL('wlanapi.dll', winmode=0x800)
    signatures = {
        'WlanOpenHandle': ([DWORD, HANDLE, C.POINTER(DWORD), C.POINTER(HANDLE)], DWORD),
        'WlanEnumInterfaces': ([HANDLE, HANDLE, C.POINTER(HANDLE)], DWORD),
        'WlanQueryInterface': ([HANDLE, C.POINTER(GUID), ENUM, HANDLE,
                                C.POINTER(DWORD), C.POINTER(HANDLE), C.POINTER(ENUM)], DWORD),
        'WlanFreeMemory': ([HANDLE], None),
        'WlanCloseHandle': ([HANDLE, HANDLE], DWORD),
    }
    for name, (arguments, result) in signatures.items():
        function = getattr(api, name)
        function.argtypes, function.restype = arguments, result
    return api

def _observe(api, expected):
    handle, listing, version = HANDLE(), HANDLE(), DWORD()
    result = 'network_unverified'
    try:
        if api.WlanOpenHandle(2, None, C.byref(version), C.byref(handle)) != 0 or not handle:
            return result
        if api.WlanEnumInterfaces(handle, None, C.byref(listing)) != 0 or not listing:
            return result
        count = C.cast(listing, C.POINTER(ListHeader)).contents.count
        if count > 1024:
            return result
        uncertain = False
        result = 'wrong_network'
        for index in range(count):
            address = listing.value + C.sizeof(ListHeader) + index * C.sizeof(Interface)
            interface = Interface.from_address(address)
            if interface.state == 4:  # explicitly disconnected
                continue
            if interface.state != 1:
                uncertain = True
                continue
            data, size = HANDLE(), DWORD()
            try:
                status = api.WlanQueryInterface(handle, C.byref(interface.guid), 7, None,
                                                C.byref(size), C.byref(data), None)
                if status != 0 or not data or size.value < C.sizeof(Connection):
                    uncertain = True
                    continue
                connection = C.cast(data, C.POINTER(Connection)).contents
                length = connection.association.ssid.length
                if connection.state != 1 or not 1 <= length <= 32:
                    uncertain = True
                    continue
                if bytes(connection.association.ssid.value[:length]) == expected:
                    result = 'target_network'
                    break
            finally:
                if data:
                    api.WlanFreeMemory(data)
        if result != 'target_network' and uncertain:
            result = 'network_unverified'
    finally:
        try:
            if listing:
                api.WlanFreeMemory(listing)
        finally:
            if handle and api.WlanCloseHandle(handle, None) != 0:
                result = 'network_unverified'
    return result

def target_wifi(ssid):
    try:
        if os.name != 'nt':
            return 'network_unverified'
        expected = ssid.encode('utf-8')
        if not 1 <= len(expected) <= 32:
            return 'network_unverified'
        return _observe(_load_api(), expected)
    except Exception:
        return 'network_unverified'
