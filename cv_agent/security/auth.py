import secrets


def valid_bearer(authorization: str | None, expected_key: str | None) -> bool:
    if not expected_key:
        return True
    if not authorization or not authorization.startswith("Bearer "):
        return False
    supplied = authorization.removeprefix("Bearer ").strip()
    return bool(supplied) and secrets.compare_digest(supplied, expected_key)
