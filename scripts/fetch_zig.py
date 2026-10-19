"""Fetch and checksum-check a pinned official Windows x64 Zig C toolchain."""

from __future__ import annotations

import hashlib
import platform
import urllib.request
import zipfile
from pathlib import Path

VERSION = "0.14.1"
ARCHIVE = f"zig-x86_64-windows-{VERSION}.zip"
URL = f"https://ziglang.org/download/{VERSION}/{ARCHIVE}"
SHA256 = "554f5378228923ffd558eac35e21af020c73789d87afeabf4bfd16f2e6feed2c"
ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    if platform.system() != "Windows" or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise SystemExit(
            "This bootstrap is for Windows x64. Use your platform's C compiler instead."
        )
    destination = ROOT / ".toolchains"
    destination.mkdir(exist_ok=True)
    archive = destination / ARCHIVE
    if not archive.is_file():
        partial = archive.with_suffix(".download")
        print(f"Downloading official Zig {VERSION} (about 82 MB)...", flush=True)
        urllib.request.urlretrieve(URL, partial)
        partial.replace(archive)
    hasher = hashlib.sha256()
    with archive.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    if digest != SHA256:
        raise SystemExit(f"SHA256 mismatch for {archive}; expected {SHA256}, got {digest}.")
    executable = destination / f"zig-x86_64-windows-{VERSION}" / "zig.exe"
    if not executable.is_file():
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(destination)
    print(f"Verified SHA256: {digest}")
    print(f"Toolchain: {executable}")


if __name__ == "__main__":
    main()
