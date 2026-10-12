"""Meaningful fail-closed tests for the external-data downloader."""
from pathlib import Path
import stat
import zipfile
import h5py
import pytest
from scripts.download_open_guided_waves import BoundedRemoteZip, safe_member, inspect_hdf5


@pytest.mark.parametrize("name", ["../signal.h5", "/signal.h5", "C:/signal.h5", "dir\\signal.h5"])
def test_archive_paths_cannot_escape(name):
    with pytest.raises(ValueError): safe_member(zipfile.ZipInfo(name))


def test_archive_symlink_is_not_written():
    info = zipfile.ZipInfo("signal.h5")
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with pytest.raises(ValueError): safe_member(info)


def test_range_server_cannot_force_a_full_download():
    class Response:
        status_code = 200
        headers = {}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def iter_content(self, *args): pytest.fail("Full archive body was read")
    class Session:
        def get(self, *args, **kwargs): return Response()
    source = BoundedRemoteZip(Session(), "https://example.invalid/huge.zip", 100000000000,
                              {"received_bytes": 0, "maximum_bytes": 65536})
    with pytest.raises(ValueError, match="ignored range"): source.read(1024)


def test_hdf5_external_link_is_not_followed(tmp_path):
    path = tmp_path / "external.h5"
    with h5py.File(path, "w") as source: source["signal"] = h5py.ExternalLink("private.h5", "/signal")
    with pytest.raises(ValueError, match="External or soft"): inspect_hdf5(path)


def test_hdf5_unbounded_shape_is_not_allocated(tmp_path):
    path = tmp_path / "shape.h5"
    with h5py.File(path, "w") as source: source.create_dataset("signal", (100000000,), dtype="float64")
    with pytest.raises(ValueError, match="exceeds cap"): inspect_hdf5(path)


def test_hdf5_vlen_signal_is_not_read(tmp_path):
    path = tmp_path / "vlen.h5"
    with h5py.File(path, "w") as source: source.create_dataset("signal", (2,), dtype=h5py.vlen_dtype("float64"))
    with pytest.raises(ValueError, match="Object/reference"): inspect_hdf5(path)
