"""The Raku language profile.

Raku (formerly Perl 6) is debugged through Nimala's DAP server,
``nimala-raku-dap``, which drives MoarVM's native remote debugging
protocol.  Nimala ships with the Nimala::Raku-LSP distribution::

    zef install Nimala::Raku-LSP

``nimala-raku-dap`` must be on PATH, or point tdb at it with
``{"adapters": {"nimala-raku-dap": "/path/to/nimala-raku-dap"}}`` in
config.json (``--adapter /path/to/nimala-raku-dap`` works too).  A Raku
source file is run through the ``raku`` interpreter on PATH; when the
adapter path has no executable bit or ends in a Raku extension, tdb
starts it as ``raku <path>``.

Launch only: Nimala's DAP server does not implement attach, so remote
attach and pid attach are not offered for Raku.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from tdb.languages.base import (
    AdapterNotFoundError,
    AdapterQuirks,
    AdapterSpec,
    LanguageNotSupportedError,
    LanguageProfile,
    Presentation,
    ProfileCapabilities,
)
from tdb.languages.errors import parse_raku_error

ADAPTER_ID = "nimala-raku-dap"
INSTALL_HINT = "zef install Nimala::Raku-LSP"


def _is_raku_script(path: str) -> bool:
    """True when `path` starts with a raku/perl6 shebang."""
    try:
        with open(path, "rb") as f:
            first = f.readline(200)
    except OSError:
        return False
    return first.startswith(b"#!") and (
        b"raku" in first or b"perl6" in first
    )


class NimalaAdapter(AdapterSpec):
    """Nimala's ``nimala-raku-dap`` server, run as a stdio DAP adapter."""

    id = ADAPTER_ID
    # Nimala reports the debuggee in DAP's `process` event, so run mode
    # can deliver Ctrl-C to the pid.  Its OwnedProcess binds the
    # debuggee's stdin to /dev/null, so there is no stdin route; under
    # --terminal the debuggee gets the terminal's own stdin.
    quirks = AdapterQuirks(interrupt_route="pid")

    def __init__(
        self, executable: str | None = None, raku_executable: str | None = None
    ) -> None:
        self._executable = executable
        # config.json's adapters.raku, like perl/rdbg, names the
        # interpreter rather than the adapter.
        self._raku = raku_executable

    def resolve_executable(self) -> str:
        exe = self._executable or shutil.which(ADAPTER_ID)
        if exe is None:
            raise AdapterNotFoundError(
                f"{ADAPTER_ID} not found on PATH — install Nimala with "
                f"`{INSTALL_HINT}`, or set "
                '{"adapters": {"nimala-raku-dap": "/path/to/'
                'nimala-raku-dap"}} in tdb\'s config.json'
            )
        return exe

    def command(self) -> list[str]:
        exe = self.resolve_executable()
        path = Path(exe)
        # A checkout's bin/nimala-raku-dap is a Raku script.  Running it
        # through the interpreter also covers an unpacked copy that lost
        # its executable bit.
        raku_script = _is_raku_script(exe)
        run_with_raku = (
            path.suffix.lower() in (".raku", ".p6", ".pl6", ".pm6")
            or not os.access(exe, os.X_OK)
            # An interpreter override must beat an executable script's
            # `#!/usr/bin/env raku` shebang.
            or (self._raku is not None and raku_script)
        )
        if run_with_raku:
            raku = self._raku or shutil.which("raku") or shutil.which("perl6")
            if raku is None:
                raise AdapterNotFoundError(
                    f"{ADAPTER_ID} is a Raku script but no raku (or perl6) "
                    "interpreter was found on PATH"
                )
            return [raku, exe]
        return [exe]

    def diagnose_exit(self, stderr: str) -> str | None:
        """Explain the common Nimala dependency failures."""
        missing = {
            "JSON::Fast": "JSON::Fast",
            "DBIish": "DBIish",
            "Nimala::Raku-DAP": "Nimala::Raku-LSP",
        }
        for module, package in missing.items():
            if f"Could not find {module}" in stderr:
                return (
                    f"the Raku module {module} is missing — run "
                    f"`zef install {package}`"
                )
        return None

    def launch_body(
        self,
        *,
        program: str,
        args: list[str],
        cwd: str,
        env: dict[str, str] | None,
        stop_on_entry: bool,
        console: str,
        opts: dict[str, Any],
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "type": "raku",
            "request": "launch",
            "program": program,
            "args": args,
            "cwd": cwd,
            "stopOnEntry": stop_on_entry,
            "console": console,
        }
        if env:
            body["env"] = env
        if self._raku:
            body["executable"] = self._raku
        return body

    def attach_body(
        self, *, host: str, port: int, opts: dict[str, Any]
    ) -> dict[str, Any]:
        raise LanguageNotSupportedError(
            "Raku does not support attach yet: Nimala's DAP server "
            "implements launch only"
        )


def build_raku_profile(
    adapter: str | None = None,
    adapter_paths: dict[str, str] | None = None,
    program: str | None = None,
) -> LanguageProfile:
    if adapter not in (None, ADAPTER_ID):
        raise LanguageNotSupportedError(
            f"unknown adapter {adapter!r} for raku (known: {ADAPTER_ID})"
        )
    return LanguageProfile(
        id="raku",
        display_name="Raku",
        adapter=NimalaAdapter(
            executable=(adapter_paths or {}).get(ADAPTER_ID),
            raku_executable=(adapter_paths or {}).get("raku"),
        ),
        presentation=Presentation(
            lexer="raku",
            parse_error=parse_raku_error,
            frame_placeholder="<unit>",
        ),
        capabilities=ProfileCapabilities(
            # Nimala implements DAP pause (MoarVM Suspend All) and reports
            # the debuggee pid in its `process` event.
            pause_while_running=True,
        ),
    )
