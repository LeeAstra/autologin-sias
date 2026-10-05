"""Windows monitor lifetime: singleton and automatic sleep prevention."""
import ctypes
import os

class WindowsSession:
    def __enter__(self):
        if os.name != 'nt':
            raise RuntimeError('This monitor requires Windows.')
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        self.kernel.CreateMutexW.restype = ctypes.c_void_p
        self.kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        self.handle = self.kernel.CreateMutexW(None, False, 'Local\\SIAS_NightMonitor')
        error = ctypes.get_last_error()
        if not self.handle:
            raise ctypes.WinError(error)
        if error == 183:
            self.kernel.CloseHandle(self.handle)
            raise RuntimeError('Another SIAS monitor is running. Stop it first.')
        self.kernel.SetThreadExecutionState(0x80000001)
        return self

    def __exit__(self, *args):
        self.kernel.SetThreadExecutionState(0x80000000)
        self.kernel.CloseHandle(self.handle)
