"""Bounded readers for untrusted research artifacts; never deserialize objects."""
from __future__ import annotations

import io
import json
import math
from pathlib import Path, PurePosixPath
import stat
import zipfile

import numpy as np


MAX_ARTIFACT_BYTES = 100 * 1024 * 1024
MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_SIGNAL_SAMPLES = 384_000
MAX_BANK_ACTIONS = 1_000


def strict_json_loads(content: str | bytes, *, maximum_bytes: int = MAX_JSON_BYTES, maximum_nodes: int = 1_000_000):
    try:
        size = len(content.encode("utf-8")) if isinstance(content, str) else len(content)
    except UnicodeEncodeError as exc:
        raise ValueError("Research JSON contains invalid Unicode") from exc
    if size > maximum_bytes:
        raise ValueError("Research JSON exceeds the size limit")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Research JSON contains duplicate keys")
            result[key] = value
        return result

    def number(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("Research JSON contains a non-finite number")
        return result

    try:
        value = json.loads(content, object_pairs_hook=pairs, parse_float=number,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Non-finite JSON number")))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("Research artifact contains invalid JSON") from exc
    nodes = 0

    def visit(item, depth):
        nonlocal nodes
        nodes += 1
        if depth > 64 or nodes > maximum_nodes:
            raise ValueError("Research JSON nesting or item count exceeds supported bounds")
        if isinstance(item, dict):
            for key, child in item.items():
                visit(key, depth + 1)
                visit(child, depth + 1)
        elif isinstance(item, list):
            for child in item:
                visit(child, depth + 1)
        elif isinstance(item, str):
            try:
                item.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise ValueError("Research JSON contains invalid Unicode") from exc
    visit(value, 0)
    return value


def read_bounded(path: Path, maximum: int = MAX_ARTIFACT_BYTES) -> bytes:
    if not path.is_file() or path.stat().st_size > maximum:
        raise ValueError("Research artifact is missing or exceeds the size limit")
    with path.open("rb") as source:
        content = source.read(maximum + 1)
    if len(content) > maximum:
        raise ValueError("Research artifact exceeds the size limit")
    return content


def validate_archive(archive: zipfile.ZipFile, *, maximum_members: int, maximum_bytes: int = MAX_ARTIFACT_BYTES) -> None:
    members = archive.infolist()
    if len(members) > maximum_members or len({item.filename for item in members}) != len(members):
        raise ValueError("Research archive contains too many or duplicate members")
    if sum(item.file_size for item in members) > maximum_bytes:
        raise ValueError("Expanded research archive exceeds the size limit")
    for item in members:
        path = PurePosixPath(item.filename)
        mode = item.external_attr >> 16
        if (path.is_absolute() or ".." in path.parts or "\\" in item.filename or ":" in item.filename
                or item.orig_filename != item.filename or str(path) != item.filename or item.is_dir() or stat.S_ISLNK(mode)
                or item.flag_bits & 1 or item.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}):
            raise ValueError("Research archive contains an unsafe or unsupported member")


def load_bounded_npy(content: bytes, *, maximum_elements: int = MAX_SIGNAL_SAMPLES,
                     allowed_ndim: tuple[int, ...] = (1,), allowed_kinds: str = "iuf") -> np.ndarray:
    """Validate header dimensions and byte count *before* NumPy allocates."""
    if len(content) > MAX_ARTIFACT_BYTES:
        raise ValueError("NumPy acquisition exceeds the size limit")
    source = io.BytesIO(content)
    try:
        version = np.lib.format.read_magic(source)
        if version == (1, 0):
            shape, _, dtype = np.lib.format.read_array_header_1_0(source, max_header_size=10_000)
        elif version == (2, 0):
            shape, _, dtype = np.lib.format.read_array_header_2_0(source, max_header_size=10_000)
        else:
            raise ValueError("Unsupported NumPy acquisition format")
        count = math.prod(shape)
        if (len(shape) not in allowed_ndim or count < 1 or count > maximum_elements
                or dtype.hasobject or dtype.fields is not None or dtype.kind not in allowed_kinds
                or count * dtype.itemsize != len(content) - source.tell()):
            raise ValueError("NumPy acquisition header has an invalid shape, dtype, or byte count")
        return np.load(io.BytesIO(content), allow_pickle=False, max_header_size=10_000)
    except (OSError, EOFError, TypeError, OverflowError) as exc:
        raise ValueError("Invalid NumPy acquisition") from exc


def validate_signal(signal: np.ndarray) -> np.ndarray:
    array = np.asarray(signal)
    if (array.ndim != 1 or not 8 <= array.size <= MAX_SIGNAL_SAMPLES
            or array.dtype.kind not in "iuf" or not np.isfinite(array).all()
            or np.max(np.abs(array.astype(np.float64))) > np.finfo(np.float32).max):
        raise ValueError("Observations must be bounded, finite, one-dimensional numeric signals")
    return array.astype(np.float32, copy=True)
