# Drip 💧

A tiny dancing water friend for your Omarchy bar.

A theme-aware Omarchy bar widget with a smiling water droplet. Click it for today's local Codex user-turn count, illustrative water estimate, a 250 mL glass gauge, and controls to adjust the assumption. Each detected turn makes the little drop perk up. While local Codex agent turns are active, it does a little sway-and-bob dance in the bar and popup, stopping when turns finish or are aborted. Reduced-motion settings disable the dance. Abandoned activity expires after five minutes without session-log updates. The bar and popup explicitly label water totals as estimates.

Default: **0.32 mL per prompt**, rounded from the 0.000085 US gallons per average ChatGPT query stated in [The Gentle Singularity](https://blog.samaltman.com/the-gentle-singularity), June 2025. This is a configurable illustrative assumption, not measured consumption or a validated Codex/model-specific footprint. Long reasoning, tool use, hardware, geography, and accounting boundaries can materially change actual consumption. Changing the assumption recalculates today's estimate.

Counts `event_msg/task_started` records whose `turn_attribution.turn_trigger` is `user`, deduplicated by turn ID. Excludes background approval turns and agent turns. Counts across local Codex conversations, including resumed old conversations; not browser ChatGPT, other devices, or all possible message-steering formats. It depends on the local Codex session log format and polls every three seconds. Dates follow the local timezone. Existing local prompts from today are included at first launch.

Only event IDs, timestamps, byte offsets, and the selected assumption are saved in `~/.local/state/drip/state.json`. No prompt text is stored, and no network requests are made. Old log contents are scanned once; later reads consume appended bytes. The plugin runs only while enabled in the bar; no separate daemon is installed.

## Build and install

Requires Qt 6 Core, qmake6, make, C++17, Python 3 for tests, and Omarchy's Quickshell bar.

```bash
git clone https://github.com/teufelziege/drip.git
cd drip
./bin/install
```

To build and test without installing:

```bash
./bin/build
python3 tests/test_counter.py
```

The installer backs up your bar configuration and adds Drip beside the clock. On upgrades, run `omarchy restart shell` after installation if the previous widget is still cached.

Installed as a user-owned shell plugin at `~/.config/omarchy/plugins/tlindsey.drip`. The CLI is inside that directory as `drip`; running it outputs JSON. `drip --rate 0.32` changes the assumption. `--sessions DIR --state FILE` allow isolated testing. Read errors surface in the popup; invalid state is never overwritten.

Click the bar widget to toggle its popup. Click outside to dismiss. Theme colors and reduced-motion preferences follow Omarchy automatically.

Remove with `omarchy plugin disable tlindsey.drip` and remove the user plugin directory if desired. Bar configuration is backed up during installation.

## License

MIT — see [LICENSE](LICENSE).
