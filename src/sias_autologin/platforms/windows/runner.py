"""Windows maintenance entry: Wi-Fi permission and per-user singleton."""
import ctypes
import os
from datetime import time
from ...runtime.monitor import maintain
from .network import target_wifi

def run(app, arguments):
    if os.name != 'nt':
        app.LOGGER.error('Maintenance modes require Windows')
        return 2
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    kernel.CreateMutexW.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    name = 'Global\\SIAS_AutoLoginMaintenance_' + os.environ.get('USERDOMAIN', '') + '_' + os.environ.get('USERNAME', '')
    handle = kernel.CreateMutexW(None, False, name)
    error = ctypes.get_last_error()
    if not handle:
        app.LOGGER.error('Cannot create maintenance mutex: %s', error)
        return 9
    try:
        if error == 183:
            app.LOGGER.info('Maintenance already running; duplicate skipped')
            return 0
        return maintain(mode=arguments.maintain, network=lambda: target_wifi('UESTC'),
                        query=app.query_authentication_state, login=app.run_login,
                        logger=app.LOGGER, start=time.fromisoformat(arguments.window_start),
                        end=time.fromisoformat(arguments.window_end))
    finally:
        kernel.CloseHandle(handle)
