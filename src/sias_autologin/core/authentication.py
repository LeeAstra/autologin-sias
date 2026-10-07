"""Portable encryption and login response classification."""
import ast
import json
import re

def rc4_hex(plain_text: str, key_text: str) -> str:
    """Match the portal's do_encrypt_rc4() JavaScript implementation."""
    key_text = str(key_text)
    if not key_text:
        raise ValueError("RC4 key is empty")

    key = [ord(key_text[i % len(key_text)]) for i in range(256)]
    sbox = list(range(256))

    j = 0
    for i in range(256):
        j = (j + sbox[i] + key[i]) % 256
        sbox[i], sbox[j] = sbox[j], sbox[i]

    a = 0
    b = 0
    output: list[str] = []
    for character in plain_text:
        a = (a + 1) % 256
        b = (b + sbox[a]) % 256
        sbox[a], sbox[b] = sbox[b], sbox[a]
        c = (sbox[a] + sbox[b]) % 256
        output.append(f"{ord(character) ^ sbox[c]:02x}")
    return "".join(output)


def _message_result(text):
    lowered = text.lower()
    # Match words/phrases rather than the substring in "unsuccessful".
    negative = bool(re.search(r"\b(?:unsuccessful|fail(?:ed|ure)?|error|invalid|wrong|denied|rejected)\b|失败|错误|拒绝|(?:未|不|没有|并非).{0,6}(?:成功|认证|登录)|\b(?:not|never|no)\s+(?:\w+\s+){0,2}(?:success(?:ful)?|ok|authenticated|logged\s+in)\b", lowered))
    negation = bool(re.search(r"unsuccessful|(?:未|不|没有|并非).{0,6}(?:成功|认证|登录)|\b(?:not|never|no)\s+(?:\w+\s+){0,2}(?:success(?:ful)?|ok|authenticated|logged\s+in)\b", lowered))
    positive = bool(re.search(r"\b(?:login|logon|authentication)\s+(?:success(?:ful)?|succeeded|ok)\b|\bsuccessfully\s+(?:logged\s+in|authenticated)\b|登录成功|认证成功", lowered))
    if negation:
        return False
    if negative and positive:
        return None
    if negative:
        return False
    return True if positive else None


def _structured_result(key, value):
    if isinstance(value, bool):
        return value
    normalized = str(value).lower()
    positive = ("1", "true") if key == "success" else ("true", "success", "ok", "1", "200", "0")
    negative = ("0", "false") if key == "success" else ("false", "fail", "failed", "error", "-1")
    return True if normalized in positive else False if normalized in negative else None


def _portal_literal(text):
    # Convert only a complete literal object; never execute JavaScript.
    candidate = text.strip().removesuffix(';').strip()
    token_pattern = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}\[\]:,]|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|[A-Za-z_][A-Za-z_0-9]*|\s+'
    matches = list(re.finditer(token_pattern, candidate))
    tokens = []
    position = 0
    for match in matches:
        if match.start() != position:
            raise ValueError('Unsupported literal syntax')
        position = match.end()
        if not match.group().isspace():
            tokens.append(match.group())
    if position != len(candidate) or not tokens or tokens[0] != '{' or tokens[-1] != '}':
        raise ValueError('Incomplete literal object')
    normalized = []
    for index, token in enumerate(tokens):
        if token.startswith("'"):
            normalized.append(json.dumps(ast.literal_eval(token)))
        elif re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', token):
            if tokens[index + 1:index + 2] == [':']:
                normalized.append(json.dumps(token))
            elif token in ('true', 'false', 'null'):
                normalized.append(token)
            else:
                raise ValueError('Non-literal value')
        else:
            normalized.append(token)
    return ''.join(normalized)


def response_indicates_success(body: bytes) -> tuple[bool | None, str]:
    text = body.decode("utf-8", errors="replace").strip()
    if not text:
        return None, "empty response"
    try:
        duplicate_keys = []
        def object_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    duplicate_keys.append(key)
                result[key] = value
            return result
        payload = json.loads(text, object_pairs_hook=object_pairs)
        if duplicate_keys:
            return None, "duplicate JSON fields"
    except json.JSONDecodeError:
        try:
            payload = json.loads(_portal_literal(text), object_pairs_hook=object_pairs)
            if duplicate_keys:
                return None, "duplicate portal fields"
        except (ValueError, SyntaxError):
            if text.startswith(('{', '[')):
                return None, "unrecognized portal object"
            return _message_result(text), "response message"
    if not isinstance(payload, dict):
        return None, "unrecognized JSON response"
    results = []
    for key in ("success", "result", "status", "code"):
        if key not in payload:
            continue
        result = _structured_result(key, payload[key])
        if result is None:
            return None, "unrecognized structured result"
        results.append(result)
    if results:
        return (results[0] if len(set(results)) == 1 else None), "JSON structured result"
    message = " ".join(str(payload[key]) for key in ("msg", "message") if payload.get(key))
    return _message_result(message), "JSON message"
