"""Portable encryption and login response classification."""
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


def response_indicates_success(body: bytes) -> tuple[bool | None, str]:
    text = body.decode("utf-8", errors="replace").strip()
    if not text:
        return None, "empty response"

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        # The portal uses a JavaScript object with single quotes. Parse its
        # top-level boolean field before inspecting message text; never eval it.
        tokens = re.findall(r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|[{}\[\]:,]|[A-Za-z_][A-Za-z_0-9]*", text)
        depth = 0
        for index, token in enumerate(tokens):
            if token in ("{", "["):
                depth += 1
            elif token in ("}", "]"):
                depth -= 1
            elif (depth == 1 and token.strip("\"'").lower() == "success"
                  and index > 0 and tokens[index - 1] in ("{", ",")
                  and tokens[index + 1:index + 2] == [":"]
                  and tokens[index + 2:index + 3] in (["true"], ["false"])):
                return tokens[index + 2] == "true", "portal success boolean field"
        lowered = text.lower()
        if any(word in lowered for word in ("error", "fail", "invalid", "wrong", "密码错误")):
            return False, "failure marker in response"
        if any(word in lowered for word in ("logon success", "login ok", "登录成功")):
            return True, "success marker in response"
        return None, f"unrecognized response ({len(body)} bytes)"

    if isinstance(payload, dict):
        success = payload.get("success")
        if isinstance(success, bool):
            return success, "JSON success field"
        if success in (1, "1", "true", "True"):
            return True, "JSON success field"
        if success in (0, "0", "false", "False"):
            return False, "JSON success field"

        for key in ("result", "status", "code"):
            value = payload.get(key)
            if isinstance(value, bool):
                return value, f"JSON {key} field"
            normalized = str(value).lower()
            if normalized in ("success", "ok", "1", "200", "0"):
                return True, f"JSON {key} field"
            if normalized in ("fail", "failed", "error", "-1"):
                return False, f"JSON {key} field"

        message = str(payload.get("msg") or payload.get("message") or "")
        lowered = message.lower()
        if any(word in lowered for word in ("成功", "success", "already", "在线")):
            return True, "JSON message"
        if any(word in lowered for word in ("失败", "错误", "error", "fail", "密码")):
            return False, "JSON message"

    return None, "unrecognized JSON response"
