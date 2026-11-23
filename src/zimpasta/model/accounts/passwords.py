"""Password hashing with scrypt from Python's standard library.

Only a salted hash is stored, never the password. A hash looks like
``scrypt$16384$8$1$<salt>$<key>`` (base64), so its cost settings travel with it and can be
raised later without breaking existing accounts.
"""

import base64
import hashlib
import hmac
import os
from functools import cache

N, R, P = 2**14, 8, 1
"""scrypt's CPU/memory cost, block size, and parallelism: about 16 MB and tens of
milliseconds per hash, which makes guessing slow."""

KEY_LENGTH = 32
SALT_LENGTH = 16


def hash_password(password: str) -> str:
    salt = os.urandom(SALT_LENGTH)
    key = _derive(password, salt, N, R, P)
    return f"scrypt${N}${R}${P}${_encode(salt)}${_encode(key)}"


def verify_password(password: str, stored: str) -> bool:
    """Whether ``password`` matches ``stored``. A malformed hash never matches."""
    try:
        scheme, n, r, p, salt, key = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(key)
        actual = _derive(password, base64.b64decode(salt), int(n), int(r), int(p))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def check_against_nothing(password: str) -> None:
    """Spend the time a real check takes, for an unknown username, so a failed login
    takes as long whether or not the username exists."""
    verify_password(password, _dummy_hash())


@cache
def _dummy_hash() -> str:
    return hash_password("not a real password")


def _derive(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=KEY_LENGTH, maxmem=2**26
    )


def _encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")
