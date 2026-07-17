"""Helpers for safely extracting ZIP archives.

``zipfile.ZipFile.extractall`` is vulnerable to "Zip Slip": a crafted archive
may contain member names such as ``../../../.bashrc`` or absolute paths that,
once extracted, escape the intended destination directory and overwrite files
elsewhere on disk. Since this launcher extracts archives coming from untrusted
sources (user-supplied ``.mcpack``/``.mcaddon``/``.zip`` files and mods
downloaded from a remote moddb), every extraction must validate member paths
before writing them.
"""

import os
import zipfile


class UnsafeArchiveError(Exception):
    """Raised when an archive member would be written outside the destination."""


def _is_within_directory(directory, target):
    directory = os.path.realpath(directory)
    target = os.path.realpath(target)
    prefix = os.path.commonpath([directory])
    return os.path.commonpath([prefix, target]) == prefix


def safe_extractall(zip_ref, dest_dir, members=None):
    """Safely extract ``zip_ref`` into ``dest_dir``.

    Behaves like ``zip_ref.extractall(dest_dir)`` but rejects any member whose
    resolved path would fall outside ``dest_dir`` (Zip Slip / path traversal).

    Raises ``UnsafeArchiveError`` if such a member is found.
    """
    os.makedirs(dest_dir, exist_ok=True)
    dest_dir = os.path.realpath(dest_dir)

    names = members if members is not None else zip_ref.namelist()
    for name in names:
        # Reject absolute paths and drive-relative names outright.
        target = os.path.realpath(os.path.join(dest_dir, name))
        if not _is_within_directory(dest_dir, target):
            raise UnsafeArchiveError(
                f"Blocked unsafe path in archive: {name!r}"
            )

    zip_ref.extractall(dest_dir, members=members)


def safe_extractall_path(zip_path, dest_dir):
    """Convenience wrapper that opens ``zip_path`` and safely extracts it."""
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        safe_extractall(zip_ref, dest_dir)
