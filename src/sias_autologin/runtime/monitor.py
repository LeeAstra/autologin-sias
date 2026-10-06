"""Portable loop; platform and authentication operations are injected."""
from datetime import datetime, time as day_time
import time

def in_window(now, start, end):
    value = now.time().replace(tzinfo=None)
    return start <= value < end if start < end else value >= start or value < end

def maintain(*, mode, network, query, login, logger, start=day_time(2,55),
             end=day_time(3,15), interval=None, retry=15, clock=datetime.now,
             monotonic=time.monotonic, sleep=time.sleep):
    if mode not in ('continuous', 'night') or start == end:
        raise ValueError('Invalid maintenance policy')
    interval = interval if interval is not None else (5 if mode == 'night' else 30)
    if interval <= 0 or retry <= 0:
        raise ValueError('Intervals must be positive')
    next_login = 0
    previous = None
    logger.info('Maintenance started: mode=%s interval=%s', mode, interval)
    while mode == 'continuous' or in_window(clock(), start, end):
        net = network()
        if net == 'wrong_network':
            logger.info('Maintenance stopped: left target Wi-Fi')
            return 0
        state, reason = query() if net == 'target_network' else ('unknown', 'network_unverified')
        if state != previous:
            logger.info('Maintenance state: %s -> %s reason=%s', previous, state, reason)
            previous = state
        if state == 'auth_required' and monotonic() >= next_login:
            # Recheck both platform permission and window before any authentication.
            if (mode == 'night' and not in_window(clock(), start, end)):
                break
            if network() != 'target_network':
                sleep(interval)
                continue
            code = login()
            logger.info('Maintenance login result: exit_code=%s', code)
            next_login = monotonic() + retry
        sleep(interval)
    logger.info('Maintenance stopped: outside night window')
    return 0
