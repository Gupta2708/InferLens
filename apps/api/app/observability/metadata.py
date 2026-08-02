SENSITIVE_KEYS = {"authorization", "api_key", "token", "cookie", "headers", "secret", "password"}


def safe_metadata(data: dict | None) -> dict:
    clean = {}
    for key, value in (data or {}).items():
        lowered = key.lower()
        if any(sensitive in lowered for sensitive in SENSITIVE_KEYS):
            continue
        if isinstance(value, dict):
            clean[key] = safe_metadata(value)
        elif isinstance(value, list):
            clean[key] = [safe_metadata(v) if isinstance(v, dict) else v for v in value]
        else:
            clean[key] = value
    return clean


def preview(messages: list[dict], limit: int = 500) -> str:
    text = "\n".join(f"{m.get('role')}: {m.get('content')}" for m in messages)
    return text[:limit]
