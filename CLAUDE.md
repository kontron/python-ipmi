# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Setup and the lint commands are in the README ("Running from the source tree"); use the tool versions pinned in `.github/workflows/lint.yml`.

```shell
pytest tests/test_sel.py::test_sel_entry_str     # a single test
pytest tests/test_ipmitool.py -k sdr             # tests matching a name
ruff check . && mypy && codespell                # the CI lint checks, configured in ruff.toml and setup.cfg
sphinx-build -W --keep-going -b html docs/source docs/_build/html   # docs, warnings are errors
```

## Things the CI checks that are easy to miss

- **mypy** runs with `disallow_untyped_defs`: every function needs annotations. Use `isinstance()` checks rather than `hasattr()` so mypy can narrow types; `pyipmi.sdr.SdrCommon` has none of the sensor record fields.
- **Docstrings** (Google convention) are required in the documented modules listed in the `per-file-ignores` of `ruff.toml` (`bmc`, `sdr`, `sel`, `sensor`, ..., `interfaces/*`). The other modules are only checked for docstring format.
- **Man page**: `man/pyipmi.1` is generated from the argparse definition of `pyipmi/ipmitool.py`. After changing commands or options, regenerate it with `bin/build_manpage.sh` (needs `argparse-manpage`, the version pinned in `lint.yml`) and commit it; CI fails if it is out of date.

## Commit style

The subject is `<module>: <imperative summary>`, e.g. `sel: decode the SEL entries to human readable strings` or `ipmitool: ...`. The body explains what was wrong or missing and why the change fixes it, wrapped at about 72 columns. Every commit needs a `Signed-off-by` line (`git commit -s`); CI checks the DCO.

## Architecture

- **`pyipmi.Ipmi`** (`pyipmi/__init__.py`) is the connection object. The IPMI commands are not defined there: `Ipmi` inherits them from the command-group classes of the modules (`bmc.Bmc`, `sdr.Sdr`, `sel.Sel`, `sensor.Sensor`, `picmg.Picmg`, ...), which all derive from `mixin.IpmiMixin`. `IpmiMixin` declares, under `TYPE_CHECKING` only, the `Ipmi` methods and cross-group commands the mixins use. When a mixin calls a new method of another group, add a stub there.
- **Messages** (`pyipmi/msgs/*.py`): each request/response is a `Message` subclass named `<Name>Req`/`<Name>Rsp`, registered with `@register_message_class`. It declares `__netfn__`/`__cmdid__` (and `__group_extension__` for PICMG/VITA/DCMI) and a `__fields__` tuple of field descriptors from `msgs/message.py` (`UnsignedInt`, `Bitfield`, `CompletionCode`, `RemainingBytes`, ...). Encoding and decoding are driven entirely by `__fields__`. The command groups send messages by name with `send_message_by_name('GetSelInfo', ...)`. `docs/commands.rst` is the table printed by `python3 bin/supported_cmds.py rst`; update it when adding messages.
- **Interfaces** (`pyipmi/interfaces/`) are the transports (`rmcp`, `rmcpplus`, `ipmitool`, `ipmidev`, `ipmbdev`, `aardvark`, `openipmblink`, `mock`), created by name with `create_interface()`. The connection's `Target` and its `Routing` hops describe bridging to controllers behind the BMC.
- **Decoded records** (`SdrCommon.from_data()`, `SelEntry`, `FruInventory`) are created from raw bytes, independent of a connection. Name tables and `*_to_string()` helpers live in the library modules (`sensor.py`: sensor types, event offsets; `sdr.py`: record types, entities, units), not in the CLI.
- **`pyipmi/ipmitool.py`** is the `pyipmi` CLI (installed also as `ipmitool.py`, its former name). Commands are registered through `_CommandGroups` in `build_parser()` as `cmd_<group>_<command>(ipmi, args)` functions. The global `-v/--verbose` sets the log level, so a subcommand option must never use the dest `verbose` (or any other global option's dest): argparse subparser defaults silently overwrite the global value. Detailed output (`sdr show`, `sel list -d`) prints the raw value in hex before the decoded value, e.g. `[0x01] Temperature`.

## Tests

- `tests/ipmi_helper.create_ipmi(rsp_data)` builds an `Ipmi` whose interface answers with canned encoded responses, either one for every request or a dict keyed by message name without the `Req`/`Rsp` suffix (a list value is returned in order). The sent requests are recorded in `ipmi.requests` as `(name, encoded bytes)`, so tests can assert on the exact wire data.
- CLI tests call the `cmd_*` functions directly with a `MagicMock` connection and an `argparse.Namespace`, and check the output with `capsys`.
- Sample FRU and HPM binaries are in `tests/fru_bin/` and `tests/hpm_bin/`.
