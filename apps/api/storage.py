from pathlib import Path

from core.config import get_settings
from core.errors import APIError


def storage_root() -> Path:
    root = Path(get_settings().storage_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def path_for(storage_key: str) -> Path:
    root = storage_root()
    path = (root / storage_key).resolve()
    if root not in path.parents:
        raise APIError(500, "invalid_storage_key", "Stored file path is invalid")
    return path


def save_bytes(storage_key: str, content: bytes) -> None:
    path = path_for(storage_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def remove_file(storage_key: str) -> None:
    path = path_for(storage_key)
    if path.exists():
        path.unlink()
