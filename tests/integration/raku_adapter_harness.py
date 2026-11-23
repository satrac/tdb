"""Scripted DAP client for Nimala's Raku debug adapter."""

import os
import shutil
from pathlib import Path

from tdb.languages.raku import NimalaAdapter

FIXTURES = Path(__file__).parent.parent.parent / "examples" / "Raku"


def nimala_command() -> list[str] | None:
    """The Nimala adapter argv, or None when Raku/Nimala are unavailable.

    TDB_NIMALA_DAP points at a checkout's bin/nimala-raku-dap, which is
    useful when Nimala is not installed into ~/.raku/bin.
    """
    if shutil.which("raku") is None and shutil.which("perl6") is None:
        return None
    path = os.environ.get("TDB_NIMALA_DAP") or shutil.which("nimala-raku-dap")
    if not path:
        return None
    try:
        return NimalaAdapter(executable=path).command()
    except Exception:
        return None
