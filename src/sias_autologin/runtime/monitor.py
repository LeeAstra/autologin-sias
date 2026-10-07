"""Portable loop; platform and authentication operations are injected."""
from dataclasses import dataclass
from datetime import datetime, time as day_time
import json
import time
import uuid

@dataclass(frozen=True)
class LoginResult:
    code: int
    submitted: bool
    confirmed: bool

def in_window(now, start, end):
    value = now.time().replace(tzinfo=None)
    return start <= value < end if start < end else value >= start or value < end

def record_event(logger, run_id, event, *, now=None, **values):
    stamp = (now or datetime.now()).astimezone().isoformat(timespec='milliseconds')
    logger.info('Maintenance event: %s', json.dumps(dict(schema=1, run_id=run_id,
                timestamp=stamp, event=event, **values), ensure_ascii=True, separators=(',', ':')))

def maintain(*, mode, network, query, login, logger, start=day_time(2,55),
             end=day_time(3,15), interval=None, retry=15, clock=datetime.now,
             monotonic=time.monotonic, sleep=time.sleep, run_id=None, version=None):
    if mode not in ('continuous', 'night') or start == end:
        raise ValueError('Invalid maintenance policy')
    interval = interval if interval is not None else (5 if mode == 'night' else 30)
    if interval <= 0 or retry <= 0:
        raise ValueError('Intervals must be positive')
    run_id = run_id or uuid.uuid4().hex
    def event(kind, **values): record_event(logger, run_id, kind, now=clock(), **values)
    next_login = 0
    previous = None
    reason = 'outside_night_window'
    logger.info('Maintenance started: mode=%s interval=%s', mode, interval)
    event('start', mode=mode, version=version)
    try:
        while mode == 'continuous' or in_window(clock(), start, end):
            net = network()
            if net == 'wrong_network':
                reason = 'left_target_wifi'
                logger.info('Maintenance stopped: left target Wi-Fi')
                return 0
            state, state_reason = query() if net == 'target_network' else ('unknown', 'network_unverified')
            if state != previous:
                logger.info('Maintenance state: %s -> %s reason=%s', previous, state, state_reason)
                event('state', previous=previous, state=state)
                previous = state
            if state == 'auth_required' and monotonic() >= next_login:
                if mode == 'night' and not in_window(clock(), start, end):
                    break
                if network() != 'target_network':
                    sleep(interval)
                    continue
                # The second network probe may itself cross the end boundary.
                if mode == 'night' and not in_window(clock(), start, end):
                    break
                result = login()
                code = result.code if isinstance(result, LoginResult) else result
                event('login_result', exit_code=code,
                      submitted=result.submitted if isinstance(result, LoginResult) else None,
                      confirmed=result.confirmed if isinstance(result, LoginResult) else None)
                logger.info('Maintenance login result: exit_code=%s', code)
                next_login = monotonic() + retry
            sleep(interval)
        logger.info('Maintenance stopped: outside night window')
        return 0
    except BaseException:
        reason = 'interrupted_or_error'
        raise
    finally:
        event('end', reason=reason)
