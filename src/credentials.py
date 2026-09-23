"""Versioned credential serialization with legacy .env compatibility."""
import json
from pathlib import Path

FORMAT_MARKER = '# AutoLogin_SIAS env-format=json-v1'


def load_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    encoded = FORMAT_MARKER in lines
    values = {}
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key, value = key.strip(), value.strip()
        if encoded:
            value = json.loads(value)
            if not isinstance(value, str):
                raise ValueError('Credential values must be strings')
        elif len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def write_env_file(path: Path, username: str, password: str) -> None:
    if any(c in username + password for c in '\r\n'):
        raise ValueError('账号或密码不能包含换行符')
    path.write_text(FORMAT_MARKER + '\n' +
                    'WLAN_USER=' + json.dumps(username, ensure_ascii=False) + '\n' +
                    'WLAN_PWD=' + json.dumps(password, ensure_ascii=False) + '\n', encoding='utf-8')
    try:
        path.chmod(0o600)
    except OSError:
        pass
