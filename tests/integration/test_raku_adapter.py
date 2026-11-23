"""Nimala Raku adapter: launch, breakpoint, variables, evaluate, exit.

Skipped unless a Rakudo installation and nimala-raku-dap are available.
Set TDB_NIMALA_DAP to a checkout's bin/nimala-raku-dap to run it without
installing Nimala.
"""

import pytest

from tests.integration.perl_adapter_harness import AdapterClient
from tests.integration.raku_adapter_harness import FIXTURES, nimala_command

COMMAND = nimala_command()

pytestmark = pytest.mark.skipif(
    COMMAND is None, reason="needs raku and nimala-raku-dap (Nimala::Raku-LSP)"
)


async def _start() -> AdapterClient:
    client = AdapterClient()
    await client.start(cmd=COMMAND)
    resp = await client.request(
        "initialize",
        {
            "adapterID": "raku",
            "linesStartAt1": True,
            "columnsStartAt1": True,
            "pathFormat": "path",
            "supportsRunInTerminalRequest": False,
        },
    )
    assert resp["success"] is True, resp
    await client.wait_event("initialized")
    return client


async def test_launch_breakpoint_inspect_evaluate_and_exit():
    client = await _start()
    try:
        program = str(FIXTURES / "hello.raku")
        launch = client.send(
            "launch",
            {
                "type": "raku",
                "request": "launch",
                "program": program,
                "args": [],
                "cwd": str(FIXTURES),
                "stopOnEntry": False,
                "console": "internalConsole",
            },
        )
        await client.request(
            "setBreakpoints",
            {
                "source": {"path": program},
                "breakpoints": [{"line": 7}],
            },
        )
        await client.request("configurationDone")
        assert (await launch)["success"] is True

        stopped = await client.wait_event("stopped", timeout=60)
        assert stopped["body"]["reason"] == "breakpoint"
        thread = stopped["body"]["threadId"]

        stack = await client.request("stackTrace", {"threadId": thread})
        top = stack["body"]["stackFrames"][0]
        assert top["source"]["path"] == program
        assert top["line"] == 7

        scopes = await client.request("scopes", {"frameId": top["id"]})
        locals_ref = scopes["body"]["scopes"][0]["variablesReference"]
        variables = await client.request(
            "variables", {"variablesReference": locals_ref}
        )
        total = next(v for v in variables["body"]["variables"] if v["name"] == "$total")
        assert total["value"] == "15"

        evaluated = await client.request(
            "evaluate",
            {"expression": "$total", "frameId": top["id"], "context": "watch"},
        )
        assert evaluated["success"] is True, evaluated
        assert "15" in evaluated["body"]["result"]

        await client.request("continue", {"threadId": thread})
        exited = await client.wait_event("exited", timeout=60)
        assert exited["body"]["exitCode"] == 0
        await client.wait_event("terminated")
    finally:
        await client.stop()


async def test_stop_on_entry_lands_in_user_code():
    client = await _start()
    try:
        program = str(FIXTURES / "hello.raku")
        launch = client.send(
            "launch",
            {
                "type": "raku",
                "request": "launch",
                "program": program,
                "args": [],
                "cwd": str(FIXTURES),
                "stopOnEntry": True,
                "console": "internalConsole",
            },
        )
        await client.request("configurationDone")
        assert (await launch)["success"] is True

        stopped = await client.wait_event("stopped", timeout=60)
        assert stopped["body"]["reason"] == "entry"
        stack = await client.request(
            "stackTrace", {"threadId": stopped["body"]["threadId"]}
        )
        top = stack["body"]["stackFrames"][0]
        assert top["source"]["path"] == program
        assert top["line"] == 1
    finally:
        await client.stop()
