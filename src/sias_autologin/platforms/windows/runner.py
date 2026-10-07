"""Windows maintenance entry: Wi-Fi permission and per-user singleton."""
import ctypes
import os
from datetime import datetime, time
from ...runtime.monitor import maintain, in_window, LoginResult, record_event
from ...version import VERSION
import uuid
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
            record_event(app.LOGGER, uuid.uuid4().hex, 'duplicate', mode=arguments.maintain, version=VERSION)
            return 0
        start, end = time.fromisoformat(arguments.window_start), time.fromisoformat(arguments.window_end)
        def allowed():
            return target_wifi('UESTC') == 'target_network' and (arguments.maintain != 'night' or in_window(datetime.now(), start, end))
        def authenticate():
            submitted = [False]
            def on_submit(): submitted[0] = True
            code = app.run_login(require_auth_required=True, before_auth=allowed, on_submit=on_submit)
            return LoginResult(code, submitted[0], code == 0)
        return maintain(mode=arguments.maintain, network=lambda: target_wifi('UESTC'),
                        query=app.query_authentication_state, login=authenticate,
                        logger=app.LOGGER, start=start, end=end, version=VERSION)
    finally:
        kernel.CloseHandle(handle)
