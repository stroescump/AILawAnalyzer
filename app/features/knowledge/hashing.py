import hashlib
import json
from typing import Any


def canonical_json_dumps(obj: Any) -> str:
    """Deterministic JSON serialization for hashing/versioning.

    Rules:
    - UTF-8, no ASCII escaping
    - sorted keys
    - no insignificant whitespace
    """

    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash_sha256(obj: Any) -> str:
    payload = canonical_json_dumps(obj).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
