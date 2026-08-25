#!/usr/bin/env python3
from __future__ import annotations

import sys
import tarfile
from pathlib import Path, PurePosixPath


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate-backup-tar.py ARCHIVE", file=sys.stderr)
        return 2
    archive = Path(sys.argv[1])
    try:
        with tarfile.open(archive, "r:") as handle:
            for member in handle.getmembers():
                path = PurePosixPath(member.name)
                if path.is_absolute() or ".." in path.parts or member.issym() or member.islnk() or member.isdev():
                    raise ValueError(f"unsafe media archive member: {member.name}")
        print("Media archive member paths verified.")
        return 0
    except (OSError, tarfile.TarError, ValueError) as exc:
        print(f"media archive verification failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
