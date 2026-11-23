# Raku

Raku (formerly Perl 6) is debugged through
[Nimala](https://raku.land/zef:kliklamala/Nimala::Raku-LSP), a Raku LSP and
DAP implementation that drives MoarVM's native remote debugging protocol.
tdb launches the `nimala-raku-dap` server over stdio; no separate proxy or
plugin is needed.

## Requirements

- Rakudo (`raku`) on PATH. Rakudo 2026.09 is what Nimala is tested against.
- `nimala-raku-dap` on PATH, from the Nimala::Raku-LSP distribution
  (1.0.2 or newer; the DAP server arrived in 1.0.0):

```bash
zef install Nimala::Raku-LSP
export PATH="$HOME/.raku/bin:$PATH"    # where zef puts the binaries
```

If the server lives somewhere else, name it in `config.json`:

```json
{
  "adapters": {"nimala-raku-dap": "/opt/nimala/bin/nimala-raku-dap"}
}
```

or pass `--adapter /opt/nimala/bin/nimala-raku-dap` for one run. A checkout's
`bin/nimala-raku-dap` works as an adapter path too; tdb runs it through the
`raku` interpreter when it has no executable bit. `adapters.raku` names a
specific interpreter when the `raku` on PATH is not the one you want.

## Usage

```bash
tdb script.raku                 # launch, stop at the first line
tdb -k 12 script.raku           # break at line 12
tdb -k 12 --if '$n > 3' script.raku
tdb --run script.raku           # run immediately, debug on demand
tdb --terminal script.raku      # program I/O in its own terminal window
```

`--eval` works for non-interactive checks, using Nimala's bounded Raku
expression syntax:

```bash
tdb -e 12 '$total' script.raku
```

## What is supported

- Line breakpoints, including conditions, hit counts, and log points
- Function breakpoints by routine name
- Exception breakpoints: uncaught (default) or all
- Continue, pause, step over, step in, step out, and run to cursor
- Call stacks and thread selection
- Variables: locals, object attributes, positionals, and associatives, with
  lazy expansion
- Evaluate console, with a bounded expression grammar (variables, attribute,
  key and index access, comparisons; no arbitrary method calls or mutation)
- Program output in the Console View
- `--run` and `--terminal`

Not supported yet:

- **Attach.** Nimala's DAP server implements launch only, so `-r` and `-a`
  are rejected for Raku.
- **Console View stdin** without `--terminal`. Nimala connects a launched
  debuggee's stdin to `/dev/null`; under `--terminal` the program gets the
  terminal's own input.
- Statement-granularity stepping. Raku steps at line granularity.

Nimala is a new project; if a session fails before any stop, run
`tdb --info` to confirm that `raku` and `nimala-raku-dap` resolve to the
versions you expect, and see the adapter's stderr in tdb's log
(`tdb --info` prints the log path).
