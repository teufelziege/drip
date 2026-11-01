# Installation & recovery

Drip is a **user-level Omarchy Quickshell bar plugin**, not a system service. These instructions assume a working Omarchy installation and local Codex session logs.

## Prerequisites

- Omarchy with the Quickshell bar and `omarchy` / `omarchy-shell` commands
- Qt 6 Core development package and `qmake6`
- `make` and a C++17 compiler (`g++`)
- Python 3 (standard library `unittest`; no pip packages needed for the tests)

Confirm the main commands are available:

```bash
command -v qmake6 make g++ python3 omarchy omarchy-shell
```

## 1. Get the source

```bash
git clone https://github.com/teufelziege/drip.git
cd drip
```

**While the reliability PR is still unmerged:** use `git clone --branch fix/reliability-pass https://github.com/teufelziege/drip.git` to get the tested branch.

## 2. Validate without installing (recommended)

```bash
./bin/build
python3 -m unittest discover -s tests -p 'test_*.py' -v
omarchy plugin validate plugin
```

A successful validator may produce **no output**; check `echo $?` immediately afterward. Exit code `0` indicates success.

Optional real-log check:

```bash
./build/drip
```

This reads `~/.codex/sessions` and creates/updates **only Drip's state** at `~/.local/state/drip/state.json`. It does not install or register the widget. Output is JSON; `prompts: 0` can be normal if there have been no qualifying local Codex user turns today. Codex logs often use UTC timestamps, but Drip counts by **local date**.

## 3. Back up and install

The installer creates its own timestamped configuration backup. For an additional, easy-to-find backup:

```bash
cp ~/.config/omarchy/shell.json ~/.config/omarchy/shell.json.pre-drip
./bin/install
```

The installer builds and tests the CLI, validates the plugin, stages the new plugin files, updates `~/.config/omarchy/shell.json`, and requests a plugin rescan. It registers `tlindsey.drip` under `bar.layout.centerBegin` unless already present elsewhere in a layout list.

Installed files live in:

```text
~/.config/omarchy/plugins/tlindsey.drip/
  BarWidget.qml
  Droplet.qml
  manifest.json
  i18n/
  drip
```

For an upgrade, the previous plugin directory is kept as `tlindsey.drip.previous`. A timestamped `shell.json.bak.drip.*` backup is also created. The installer attempts to restore the previous plugin and shell configuration if its staging/configuration swap fails, but **not every possible filesystem or post-install shell failure is covered**.

## 4. Restart and verify

```bash
omarchy restart shell
```

Look for the droplet in the bar. Click it to open the details panel and verify the prompt count and water estimate. To verify live detection, submit a prompt in local Codex and rerun `./build/drip` or wait for the widget's next refresh. The displayed number is an **estimate**, not measured consumption.

## Troubleshooting

**The widget does not appear:** check that the plugin directory exists and `tlindsey.drip` appears in `~/.config/omarchy/shell.json`; then restart the shell. To verify the validator:

```bash
omarchy plugin validate plugin
echo "validator exit code: $?"
```

**The widget shows `Drip !`:** run `~/.config/omarchy/plugins/tlindsey.drip/drip` in a terminal to see any error message. Check that `~/.codex/sessions` exists and that Drip's state directory is writable. Don't delete an invalid state file without making a backup first.

**The count is zero:** check for `*.jsonl` files under `~/.codex/sessions` and whether any qualifying user turns occurred **today in local time**. `unreadable: 0` does not prove logs exist.

**Upgrading:** pull the desired branch, rerun `./bin/install`, then `omarchy restart shell`. Installation runs the tests again.

## Manual removal / recovery

Before editing the configuration, **stop or restart the shell afterward** so it reloads the layout.

1. Make a backup of the current `~/.config/omarchy/shell.json`.
2. Edit `~/.config/omarchy/shell.json` and remove the object `{"id":"tlindsey.drip"}` from the appropriate `bar.layout` list. Keep valid JSON and preserve other entries.
3. Move or remove `~/.config/omarchy/plugins/tlindsey.drip`. If you want to retain the installed files, rename the directory instead of deleting it.
4. Run `omarchy restart shell`.

If you made the independent backup above and **have not made other shell configuration changes since then**, you can restore the whole previous configuration:

```bash
cp ~/.config/omarchy/shell.json.pre-drip ~/.config/omarchy/shell.json
omarchy restart shell
```

**Caution:** restoring a full backup discards any subsequent shell configuration changes. If you have changed the layout since installing Drip, remove only the Drip entry instead.

Drip's optional state file (`~/.local/state/drip/state.json`) is not part of the plugin installation. Remove it only if you also want to discard the saved estimate setting and counting cache.
