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


def extract_all_apk_native_libs(apk_path, dest_dir):
    """
    Extract all native .so libraries (e.g. libmaesdk.so, libPlayFabMultiplayer.so,
    libpairipcore.so, libminecraftpe.so, libfmod.so, etc.) from an APK into dest_dir/lib/<arch>/.
    Crucial fallback if mcpelauncher-extract misses secondary libraries.
    """
    import shutil
    from src.utils.logger import logger

    if not os.path.isfile(apk_path) or not zipfile.is_zipfile(apk_path):
        return
    try:
        with zipfile.ZipFile(apk_path, "r") as zf:
            for member in zf.namelist():
                # Members match patterns like "lib/x86_64/libmaesdk.so"
                if member.startswith("lib/") and member.endswith(".so"):
                    target_file = os.path.join(dest_dir, member)
                    # Extract if missing or incomplete (0 bytes)
                    if not os.path.exists(target_file) or os.path.getsize(target_file) == 0:
                        os.makedirs(os.path.dirname(target_file), exist_ok=True)
                        with zf.open(member) as src_f, open(target_file, "wb") as dst_f:
                            shutil.copyfileobj(src_f, dst_f)
                        try:
                            os.chmod(target_file, 0o755)
                        except OSError:
                            pass
                        logger.info(f"Fallback extracted native lib from APK: {member} -> {target_file}")
    except Exception as e:
        logger.warning(f"Failed extracting native libraries from {apk_path}: {e}")
