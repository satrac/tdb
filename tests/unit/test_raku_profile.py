"""The Raku language profile and its Nimala DAP adapter."""

import os

import pytest

from tdb.languages import registry
from tdb.languages.base import AdapterNotFoundError, LanguageNotSupportedError
from tdb.languages.raku import (
    ADAPTER_ID,
    NimalaAdapter,
    build_raku_profile,
)


def test_profile_shape():
    p = build_raku_profile()
    assert p.id == "raku"
    assert p.display_name == "Raku"
    assert p.adapter.id == ADAPTER_ID
    assert p.presentation.lexer == "raku"
    assert p.presentation.frame_placeholder == "<unit>"
    assert p.presentation.parse_error is not None
    assert p.capabilities.pause_while_running is True
    # Nimala binds the debuggee's stdin to /dev/null; only --terminal
    # gives the program a real stdin.
    assert p.adapter.quirks.stdin_route is None
    assert p.adapter.quirks.interrupt_route == "pid"


def test_registered_in_registry():
    assert "raku" in registry.known_languages()
    assert registry.resolve("raku").id == "raku"


@pytest.mark.parametrize(
    "name",
    [
        "x.raku",
        "x.rakumod",
        "x.rakudoc",
        "x.rakutest",
        "x.p6",
        "x.pm6",
        "x.pl6",
        "x.t6",
    ],
)
def test_detects_raku_extensions(name):
    assert registry.detect(f"/tmp/{name}") == "raku"


@pytest.mark.parametrize(
    "shebang", ["#!/usr/bin/env raku", "#!/usr/bin/raku", "#!/usr/bin/env perl6"]
)
def test_detects_raku_shebang(tmp_path, shebang):
    f = tmp_path / "tool"
    f.write_text(f"{shebang}\nsay 1;\n")
    assert registry.detect(str(f)) == "raku"


def test_plain_perl_t_stays_perl(tmp_path):
    f = tmp_path / "x.t"
    f.write_text("use strict;\nuse warnings;\nprint \"ok\\n\";\n")
    assert registry.detect(str(f)) == "perl"


def test_raku_t_selected_by_use_v6(tmp_path):
    f = tmp_path / "x.t"
    f.write_text("use v6.d;\nuse Test;\n")
    assert registry.detect(str(f)) == "raku"


def test_command_uses_path_executable(monkeypatch, tmp_path):
    exe = tmp_path / ADAPTER_ID
    exe.write_text("#!/bin/sh\n")
    exe.chmod(0o755)
    monkeypatch.setattr(
        "shutil.which", lambda name: str(exe) if name == ADAPTER_ID else None
    )
    assert NimalaAdapter().command() == [str(exe)]


def test_command_runs_raku_script_through_interpreter(monkeypatch, tmp_path):
    exe = tmp_path / "nimala-raku-dap"
    exe.write_text("use v6.d;\n")
    exe.chmod(0o644)  # no executable bit
    raku = tmp_path / "raku"
    raku.write_text("#!/bin/sh\n")
    raku.chmod(0o755)
    monkeypatch.setattr(
        "shutil.which",
        lambda name: {"nimala-raku-dap": str(exe), "raku": str(raku)}.get(name),
    )
    assert NimalaAdapter().command() == [str(raku), str(exe)]


def test_interpreter_override_beats_executable_script_shebang(tmp_path):
    exe = tmp_path / ADAPTER_ID
    exe.write_text("#!/usr/bin/env raku\nuse v6.d;\n")
    exe.chmod(0o755)
    assert NimalaAdapter(
        executable=str(exe), raku_executable="/opt/bin/raku"
    ).command() == ["/opt/bin/raku", str(exe)]


def test_script_adapter_without_raku_names_the_interpreter(monkeypatch, tmp_path):
    exe = tmp_path / "nimala-raku-dap"
    exe.write_text("use v6.d;\n")
    exe.chmod(0o644)
    monkeypatch.setattr(
        "shutil.which",
        lambda name: str(exe) if name == "nimala-raku-dap" else None,
    )
    with pytest.raises(AdapterNotFoundError, match="no raku"):
        NimalaAdapter().command()


def test_missing_adapter_names_nimala_install(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    with pytest.raises(AdapterNotFoundError, match="zef install Nimala::Raku-LSP"):
        NimalaAdapter().command()


def test_launch_body():
    body = NimalaAdapter().launch_body(
        program="/x/p.raku",
        args=["a", "b"],
        cwd="/x",
        env={"RAKU_TEST": "1"},
        stop_on_entry=True,
        console="internalConsole",
        opts={},
    )
    assert body == {
        "type": "raku",
        "request": "launch",
        "program": "/x/p.raku",
        "args": ["a", "b"],
        "cwd": "/x",
        "stopOnEntry": True,
        "console": "internalConsole",
        "env": {"RAKU_TEST": "1"},
    }


def test_launch_body_carries_raku_interpreter_override():
    body = NimalaAdapter(raku_executable="/opt/bin/raku").launch_body(
        program="/x/p.raku",
        args=[],
        cwd="/x",
        env=None,
        stop_on_entry=False,
        console="internalConsole",
        opts={},
    )
    assert body["executable"] == "/opt/bin/raku"


def test_launch_body_omits_empty_env():
    body = NimalaAdapter().launch_body(
        program="/x/p.raku",
        args=[],
        cwd="/x",
        env=None,
        stop_on_entry=False,
        console="internalConsole",
        opts={},
    )
    assert "env" not in body
    assert body["stopOnEntry"] is False


def test_attach_is_rejected():
    with pytest.raises(LanguageNotSupportedError, match="launch only"):
        NimalaAdapter().attach_body(host="localhost", port=1, opts={})


def test_unknown_adapter_is_rejected():
    with pytest.raises(LanguageNotSupportedError, match=ADAPTER_ID):
        build_raku_profile(adapter="gdb")


def test_adapter_paths_names_the_adapter_and_interpreter():
    p = build_raku_profile(
        adapter_paths={ADAPTER_ID: "/opt/nimala-raku-dap", "raku": "/opt/bin/raku"}
    )
    assert p.adapter._executable == "/opt/nimala-raku-dap"
    assert p.adapter._raku == "/opt/bin/raku"


def test_adapter_path_accepted_as_path(monkeypatch, tmp_path):
    exe = tmp_path / ADAPTER_ID
    exe.write_text("#!/bin/sh\n")
    exe.chmod(0o755)
    monkeypatch.setenv("PATH", os.environ.get("PATH", ""))
    p = registry.resolve("raku", adapter=str(exe))
    assert p.adapter.id == ADAPTER_ID
    assert p.adapter.command() == [str(exe)]


def test_diagnose_missing_json_fast():
    hint = NimalaAdapter().diagnose_exit(
        "===SORRY!=== Error while compiling ...\nCould not find JSON::Fast in:\n"
    )
    assert hint is not None
    assert "zef install JSON::Fast" in hint


def test_diagnose_missing_dbiish():
    hint = NimalaAdapter().diagnose_exit("Could not find DBIish in:\n")
    assert hint is not None
    assert "zef install DBIish" in hint


def test_diagnose_unrecognized_stderr():
    assert NimalaAdapter().diagnose_exit("some other failure\n") is None
