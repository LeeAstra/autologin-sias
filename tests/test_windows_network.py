import ctypes as C
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from sias_autologin.platforms.windows import network as n

class FakeAPI:
    def __init__(self, interfaces=(), error=0, short=False):
        self.interfaces, self.error, self.short = interfaces, error, short
        self.buffers, self.freed, self.closed = [], [], 0
    def WlanOpenHandle(self, version, reserved, negotiated, handle):
        C.cast(handle,C.POINTER(n.HANDLE))[0]=42
        return 0
    def WlanEnumInterfaces(self, handle, reserved, output):
        buffer=C.create_string_buffer(8+len(self.interfaces)*C.sizeof(n.Interface))
        n.ListHeader.from_buffer(buffer).count=len(self.interfaces)
        for i,(state,ssid) in enumerate(self.interfaces):
            item=n.Interface.from_buffer(buffer,8+i*C.sizeof(n.Interface))
            item.state=state; item.guid.data1=i
        self.buffers.append(buffer)
        C.cast(output,C.POINTER(n.HANDLE))[0]=C.addressof(buffer)
        return self.error if self.error==1062 else 0
    def WlanQueryInterface(self, handle, guid, opcode, reserved, size, output, kind):
        index=C.cast(guid,C.POINTER(n.GUID)).contents.data1
        state,ssid=self.interfaces[index]
        buffer=n.Connection(); buffer.state=state
        buffer.association.ssid.length=len(ssid)
        for i,b in enumerate(ssid[:32]): buffer.association.ssid.value[i]=b
        self.buffers.append(buffer)
        C.cast(output,C.POINTER(n.HANDLE))[0]=C.addressof(buffer)
        C.cast(size,C.POINTER(n.DWORD))[0]=1 if self.short else C.sizeof(buffer)
        return self.error
    def WlanFreeMemory(self, pointer): self.freed.append(pointer.value)
    def WlanCloseHandle(self, handle, reserved): self.closed+=1; return 0

class WindowsNetworkTests(unittest.TestCase):
    def check(self, interfaces, expected, **options):
        api=FakeAPI(interfaces,**options)
        self.assertEqual(n._observe(api,b'UESTC'),expected)
        self.assertEqual(api.closed,1)
        self.assertCountEqual(api.freed,[C.addressof(b) for b in api.buffers])
    def test_windows_abi(self):
        self.assertEqual(C.sizeof(n.Interface),532)
        self.assertEqual(C.sizeof(n.Connection),604)
    def test_target(self): self.check([(1,b'UESTC')],'target_network')
    def test_other(self): self.check([(1,b'Other')],'wrong_network')
    def test_disconnected(self): self.check([(4,b'')],'wrong_network')
    def test_no_interfaces(self): self.check([],'wrong_network')
    def test_multi_adapter(self): self.check([(1,b'Other'),(1,b'UESTC')],'target_network')
    def test_target_with_transitioning_other_adapter(self):
        self.check([(5,b''),(1,b'UESTC')],'target_network')
    def test_other_with_transitioning_adapter_is_unknown(self):
        self.check([(1,b'Other'),(5,b'')],'network_unverified')
    def test_loader_failure_is_unknown(self):
        with patch.object(n.os,'name','nt'), patch.object(n,'_load_api',side_effect=OSError('denied')):
            self.assertEqual(n.target_wifi('UESTC'),'network_unverified')
    def test_fresh_observations(self):
        with patch.object(n.os,'name','nt'), patch.object(n,'_load_api',
                side_effect=[FakeAPI([(1,b'UESTC')]),FakeAPI([(4,b'')]),FakeAPI([(1,b'Other')])]):
            self.assertEqual(n.target_wifi('UESTC'),'target_network')
            self.assertEqual(n.target_wifi('UESTC'),'wrong_network')
            self.assertEqual(n.target_wifi('UESTC'),'wrong_network')
    def test_transition(self): self.check([(5,b'')],'network_unverified')
    def test_service_unavailable(self): self.check([(1,b'UESTC')],'network_unverified',error=1062)
    def test_denied(self): self.check([(1,b'UESTC')],'network_unverified',error=5)
    def test_short_query(self): self.check([(1,b'UESTC')],'network_unverified',short=True)
    def test_invalid_ssid(self): self.check([(1,b'x'*33)],'network_unverified')
    def test_close_failure_is_unknown(self):
        api=FakeAPI([(1,b'UESTC')])
        api.WlanCloseHandle=lambda *args: 6
        self.assertEqual(n._observe(api,b'UESTC'),'network_unverified')
    def test_query_exception_releases_resources(self):
        api=FakeAPI([(1,b'UESTC')])
        def fail(*args): raise OSError('fixture')
        api.WlanQueryInterface=fail
        with self.assertRaises(OSError): n._observe(api,b'UESTC')
        self.assertEqual(api.closed,1)
        self.assertCountEqual(api.freed,[C.addressof(b) for b in api.buffers])
    def test_repeated_and_resume(self):
        for _ in range(100):
            self.check([(1,b'UESTC')],'target_network')
            self.check([(0,b'')],'network_unverified')
            self.check([(1,b'UESTC')],'target_network')
if __name__=='__main__': unittest.main()
