"""Run the PSLog unittest suite safely for the Windows build.

Why this wrapper exists
-----------------------
The PSLog GUI tests can finish with every unittest passing and print the normal
``Ran ... / OK`` summary, but the *test interpreter* may then terminate during
PySide/Qt native teardown with Windows status 0xC0000409.  That happens after
unittest has already produced a successful result and can make PowerShell see a
false non-zero exit code.

To keep the build strict without masking real test failures, this launcher runs
unittest in a child process, streams its output unchanged, and accepts the known
0xC0000409 teardown status only when the captured unittest summary itself is an
unambiguous successful ``OK`` result.  Any ordinary unittest failure/error, any
other process exit code, or a missing success summary still fails the build.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

# Windows STATUS_STACK_BUFFER_OVERRUN, observed only after a fully successful
# PySide/Qt unittest run during interpreter teardown.
_QT_TEARDOWN_CODES = {0xC0000409, -1073740791}

# unittest's successful trailer.  Keep this deliberately strict: the workaround
# is only allowed if the child actually printed a complete successful summary.
_OK_TRAILER = re.compile(
    rb"Ran\s+\d+\s+tests?\s+in\s+[0-9.]+s\s*\r?\n\s*\r?\n"
    rb"OK(?:\s+\([^\r\n]*\))?\s*$",
    re.DOTALL,
)


def _stream_and_capture(command: list[str], cwd: Path) -> tuple[int, bytes]:
    proc = subprocess.Popen(
        command,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
    )
    assert proc.stdout is not None
    chunks: list[bytes] = []
    out = getattr(sys.stdout, "buffer", None)

    while True:
        block = proc.stdout.read(8192)
        if not block:
            break
        chunks.append(block)
        if out is not None:
            out.write(block)
            out.flush()
        else:  # pragma: no cover - ordinary Windows console has .buffer
            sys.stdout.write(block.decode(errors="replace"))
            sys.stdout.flush()

    return proc.wait(), b"".join(chunks)


def _has_clean_ok_summary(output: bytes) -> bool:
    # Do not let an earlier 'OK' hide a genuine unittest failure trailer.
    if b"FAILED (" in output or b"FAIL:" in output or b"ERROR:" in output:
        return False
    # The final unittest trailer must be a complete successful result.
    tail = output[-8192:]
    return _OK_TRAILER.search(tail) is not None


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)

    return_code, output = _stream_and_capture(
        [sys.executable, "-m", "unittest", "discover", "-v"], root
    )

    if return_code == 0:
        return 0

    if return_code in _QT_TEARDOWN_CODES and _has_clean_ok_summary(output):
        print(
            "\n[build] Tests are all OK. Ignoring known PySide/Qt teardown "
            "status 0xC0000409 after the successful unittest summary.",
            flush=True,
        )
        return 0

    print(f"\n[build] Test process exit code: {return_code}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
