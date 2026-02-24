# swproj2eq implementation spec

## scope

- [ ] turnkey `quickstart` flow: user picks `.swproj`, tool sets up camilla passthrough
- [ ] `advanced` flow for power users (export-only, no routing changes)
- [ ] guarantee rollback + no destructive config changes

## product goals

- [ ] 1 command, working audio correction in <5 min
- [ ] zero edits to user's existing audio configs unless explicit opt-in
- [ ] reversible in 1 command
- [ ] pipewire-first linux support

## non-goals (mvp)

- [ ] no full GUI app
- [ ] no replacing user's full audio stack
- [ ] no system-wide `/etc` writes (user-level only)

## user modes

- [ ] `quickstart` (default): guided, minimal choices, safe defaults
- [ ] `advanced`: export artifacts only + optional service/config generation
- [ ] `doctor`: inspect current setup + suggest fixes
- [ ] `rollback`: restore previous default sink + disable swproj2eq runtime
- [ ] `uninstall`: remove all swproj2eq-managed files/services

## cli spec

- [ ] `swproj2eq quickstart --profile <file.swproj> [--set-default] [--yes]`
- [ ] `swproj2eq export --profile <file.swproj> --outdir <dir>`
- [ ] `swproj2eq enable [--profile-id <id>] [--set-default]`
- [ ] `swproj2eq disable`
- [ ] `swproj2eq rollback`
- [ ] `swproj2eq uninstall [--purge-profiles]`
- [ ] `swproj2eq status`
- [ ] `swproj2eq doctor`

## safety rules (hard requirements)

- [ ] never overwrite non-swproj2eq files
- [ ] never edit `/etc` in mvp
- [ ] namespace all artifacts under:
  - [ ] `~/.local/share/swproj2eq/`
  - [ ] `~/.config/swproj2eq/`
  - [ ] `~/.config/systemd/user/swproj2eq-*.service`
  - [ ] `~/.config/pipewire/*swproj2eq*`
- [ ] do not set default sink unless `--set-default` or explicit confirm
- [ ] persist prior default sink before any change
- [ ] one-command rollback always available

## runtime architecture (mvp)

```
Apps -> [swproj2eq_in] -> CamillaDSP (EQ + delay) -> [hardware sink]
```

- [ ] app audio -> virtual sink (`swproj2eq_in`)
- [ ] camilla capture = `swproj2eq_in.monitor`
- [ ] camilla playback = user's previous default hardware sink
- [ ] optional default sink switch to `swproj2eq_in`
- [ ] camilla runs as user systemd service

## implementation phases

### phase 1: core refactor

- [ ] split parser/export code into importable module + cli wrapper
- [ ] keep existing exports (camilla/pipewire/easyeffects/csv/eq apo)
- [ ] add profile id/hash + metadata manifest

### phase 2: env detection

- [ ] detect pipewire + `pactl` availability
- [ ] detect current default sink
- [ ] detect active camilla/easyeffects to avoid conflicts
- [ ] detect sample rate/channels from current sink

### phase 3: asset generation

- [ ] generate camilla IR wavs + `camilladsp.yml`
- [ ] inject detected playback target + channels
- [ ] add preamp headroom + channel delay from profile
- [ ] save under profile dir:
  - [ ] `profiles/<id>/camilla/*`
  - [ ] `profiles/<id>/manifest.json`

### phase 4: audio routing setup

- [ ] create swproj2eq virtual sink config (user-level pipewire/pulse compat)
- [ ] create/enable `swproj2eq-camilla.service`
- [ ] start service and verify sink appears
- [ ] optional: set default sink to `swproj2eq_in`

### phase 5: state + rollback

- [ ] write state file `~/.local/state/swproj2eq/state.json`
- [ ] record: previous default sink, active profile id, created files, service state
- [ ] implement `rollback` robustly even after partial failure

### phase 6: doctor + diagnostics

- [ ] `status`: show active chain, profile, default sink
- [ ] `doctor`: check service health, sink availability, routing, sample-rate mismatch
- [ ] clear next-step remediation messages

### phase 7: docs

- [ ] quickstart docs (2 min setup)
- [ ] conflict docs (easyeffects/camilla coexistence)
- [ ] rollback/uninstall docs
- [ ] "what we change" explicit list

## data + file layout

```
~/.local/share/swproj2eq/profiles/<profile-id>/...
~/.config/swproj2eq/config.toml
~/.local/state/swproj2eq/state.json
~/.config/systemd/user/swproj2eq-camilla.service
~/.config/pipewire/**/swproj2eq*.conf
```

## conflict handling

- [ ] if easyeffects active on output: warn + continue only with `--yes`
- [ ] if another camilla instance active: abort by default, explain fix
- [ ] if default sink unavailable after reboot: auto-fallback + notify
- [ ] if service fails start: auto-rollback default sink when changed

## acceptance criteria (mvp)

- [ ] fresh pipewire user can run `quickstart` and hear corrected audio
- [ ] `rollback` restores exact previous default sink
- [ ] no non-swproj2eq user files modified
- [ ] reboot persistence works when enabled
- [ ] `uninstall` leaves system clean

## test plan

- [ ] unit: `.swproj` parsing, IR generation, config rendering
- [ ] unit: state machine (enable/disable/rollback edge cases)
- [ ] integration: mocked `pactl/systemctl` command outputs
- [ ] manual matrix:
  - [ ] ubuntu (pipewire)
  - [ ] fedora
  - [ ] arch
- [ ] failure tests:
  - [ ] missing sink
  - [ ] service crash
  - [ ] bad `.swproj`

## versioning

- [ ] `v0.2.0`: parser/export stable (current)
- [ ] `v0.3.0`: quickstart + rollback mvp
- [ ] `v0.4.0`: doctor + hardened conflict handling

## open decisions (defaults chosen)

- [x] default behavior: auto-switch default sink? **no**, require `--set-default`
- [x] if easyeffects running, proceed? **warn + stop unless `--yes`**
- [x] keep both quickstart + advanced? **yes**, default quickstart, preserve advanced
