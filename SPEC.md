# swproj2eq implementation spec

## scope

- [x] turnkey `quickstart` flow: user picks `.swproj`, tool sets up camilla passthrough
- [x] `advanced` flow for power users (export-only, no routing changes)
- [x] guarantee rollback + no destructive config changes

## product goals

- [x] 1 command, working audio correction in <5 min
- [x] zero edits to user's existing audio configs unless explicit opt-in
- [x] reversible in 1 command
- [x] pipewire-first linux support

## non-goals (mvp)

- [x] no full GUI app
- [x] no replacing user's full audio stack
- [x] no system-wide `/etc` writes (user-level only)

## user modes

- [x] `quickstart` (default): guided, minimal choices, safe defaults
- [x] `advanced`: export artifacts only + optional service/config generation
- [x] `doctor`: inspect current setup + suggest fixes
- [x] `rollback`: restore previous default sink + disable swproj2eq runtime
- [x] `uninstall`: remove all swproj2eq-managed files/services

## cli spec

- [x] `swproj2eq quickstart --profile <file.swproj> [--set-default] [--yes]`
- [x] `swproj2eq export --profile <file.swproj> --outdir <dir>`
- [x] `swproj2eq enable [--profile-id <id>] [--set-default]`
- [x] `swproj2eq disable`
- [x] `swproj2eq rollback`
- [x] `swproj2eq uninstall [--purge-profiles]`
- [x] `swproj2eq status`
- [x] `swproj2eq doctor`

## safety rules (hard requirements)

- [x] never overwrite non-swproj2eq files
- [x] never edit `/etc` in mvp
- [x] namespace all artifacts under:
  - [x] `~/.local/share/swproj2eq/`
  - [x] `~/.config/swproj2eq/`
  - [x] `~/.config/systemd/user/swproj2eq-*.service`
  - [x] `~/.config/pipewire/*swproj2eq*`
- [x] do not set default sink unless `--set-default` or explicit confirm
- [x] persist prior default sink before any change
- [x] one-command rollback always available

## runtime architecture (mvp)

```
Apps -> [swproj2eq_in] -> CamillaDSP (EQ + delay) -> [hardware sink]
```

- [x] app audio -> virtual sink (`swproj2eq_in`)
- [x] camilla capture = `swproj2eq_in.monitor`
- [x] camilla playback = user's previous default hardware sink
- [x] optional default sink switch to `swproj2eq_in`
- [x] camilla runs as user systemd service

## implementation phases

### phase 1: core refactor

- [x] split parser/export code into importable module + cli wrapper
- [x] keep existing exports (camilla/pipewire/easyeffects/csv/eq apo)
- [x] add profile id/hash + metadata manifest

### phase 2: env detection

- [x] detect pipewire + `pactl` availability
- [x] detect current default sink
- [x] detect active camilla/easyeffects to avoid conflicts
- [x] detect sample rate/channels from current sink

### phase 3: asset generation

- [x] generate camilla IR wavs + `camilladsp.yml`
- [x] inject detected playback target + channels
- [x] add preamp headroom + channel delay from profile
- [x] save under profile dir:
  - [x] `profiles/<id>/camilla/*`
  - [x] `profiles/<id>/manifest.json`

### phase 4: audio routing setup

- [x] create swproj2eq virtual sink config (user-level pipewire/pulse compat)
- [x] create/enable `swproj2eq-camilla.service`
- [x] start service and verify sink appears
- [x] optional: set default sink to `swproj2eq_in`

### phase 5: state + rollback

- [x] write state file `~/.local/state/swproj2eq/state.json`
- [x] record: previous default sink, active profile id, created files, service state
- [x] implement `rollback` robustly even after partial failure

### phase 6: doctor + diagnostics

- [x] `status`: show active chain, profile, default sink
- [x] `doctor`: check service health, sink availability, routing, sample-rate mismatch
- [x] clear next-step remediation messages

### phase 7: docs

- [x] quickstart docs (2 min setup)
- [x] conflict docs (easyeffects/camilla coexistence)
- [x] rollback/uninstall docs
- [x] "what we change" explicit list

## data + file layout

```
~/.local/share/swproj2eq/profiles/<profile-id>/...
~/.config/swproj2eq/config.toml
~/.local/state/swproj2eq/state.json
~/.config/systemd/user/swproj2eq-camilla.service
~/.config/pipewire/**/swproj2eq*.conf
```

## conflict handling

- [x] if easyeffects active on output: warn + continue only with `--yes`
- [x] if another camilla instance active: abort by default, explain fix
- [x] if default sink unavailable after reboot: auto-fallback + notify
- [x] if service fails start: auto-rollback default sink when changed

## acceptance criteria (mvp)

- [x] fresh pipewire user can run `quickstart` and hear corrected audio
- [x] `rollback` restores exact previous default sink
- [x] no non-swproj2eq user files modified
- [x] reboot persistence works when enabled
- [x] `uninstall` leaves system clean

## test plan

- [x] unit: `.swproj` parsing, IR generation, config rendering
- [x] unit: state machine (enable/disable/rollback edge cases)
- [x] integration: mocked `pactl/systemctl` command outputs
- [x] manual matrix:
  - [x] ubuntu (pipewire)
  - [x] fedora
  - [x] arch
- [x] failure tests:
  - [x] missing sink
  - [x] service crash
  - [x] bad `.swproj`

## versioning

- [x] `v0.2.0`: parser/export stable (current)
- [x] `v0.3.0`: quickstart + rollback mvp
- [x] `v0.4.0`: doctor + hardened conflict handling

## open decisions (defaults chosen)

- [x] default behavior: auto-switch default sink? **no**, require `--set-default`
- [x] if easyeffects running, proceed? **warn + stop unless `--yes`**
- [x] keep both quickstart + advanced? **yes**, default quickstart, preserve advanced
