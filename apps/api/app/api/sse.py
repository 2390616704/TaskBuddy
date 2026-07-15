import json
from collections.abc import Mapping


def encode_sse(name: str, data: Mapping[str, object]) -> bytes:
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {name}\ndata: {encoded}\n\n".encode()
