"""Hold one machine-wide installer mutex across discovery, deployment and rollback."""
import ctypes
import os
import threading

_owner = threading.local()

class InstallationLock:
    def __enter__(self):
        self.handle = None
        if os.name != 'nt':
            return self
        if getattr(_owner, 'depth', 0):
            _owner.depth += 1
            return self
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        self.kernel.CreateMutexW.restype = ctypes.c_void_p
        self.kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        self.handle = self.kernel.CreateMutexW(None, False, 'Global\\SIAS_AutoLoginInstaller')
        error = ctypes.get_last_error()
        if not self.handle:
            raise ctypes.WinError(error)
        if error == 183:
            self.kernel.CloseHandle(self.handle)
            self.handle = None
            raise RuntimeError('另一个安装器正在运行，请关闭它后重试。')
        _owner.depth = 1
        return self

    def __exit__(self, *args):
        if os.name == 'nt':
            _owner.depth -= 1
            if self.handle:
                self.kernel.CloseHandle(self.handle)
