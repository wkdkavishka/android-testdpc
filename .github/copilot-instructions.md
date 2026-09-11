# TestDPC — CBA device-owner fork

Guidance for Copilot and Claude Code. This is the hub: architecture, commands and
conventions live here. Detail lives in `AI-MD/`, linked from each section.

## What this repo is, and what it is not

A vendored clone of Google's **TestDPC** at tag `v9.0.12`, carrying local build fixes and
(planned) a password gate on kiosk exit. It is not a product of ours. Upstream is
`github.com/googlesamples/android-testdpc`, Apache 2.0.

The checkout sits at **detached HEAD on `v9.0.12`**, so local work is not on a branch and
is easy to lose. Branch before editing anything.

TestDPC is the device policy controller for a locked-down Samsung Galaxy A07 that must run
exactly five apps. The device procedure, the package triage and the rollback steps live in
`DEVICE-LOCKDOWN.md` in the **parent** folder, outside this repo. That runbook is the
authority on the device; this hub is the authority on the code.

> The docs in this repo describe our fork, not Google's sample. Keep them out of any pull
> request aimed upstream.

## Commands

```bash
export ANDROID_HOME=/mnt/Storage/Android/Sdk    # required, Bazel fails without it
bazel build testdpc                             # -> bazel-bin/testdpc.apk
bazel build testdpc_debug                       # adds AndroidManifestDebug.xml overlay
bazel clean                                     # outputs only; --expunge also drops deps
```

Bazel is pinned to **6.5.0** by `.bazelversion` and run through bazelisk. Newer Bazel
removed the native `android_binary` rule this project depends on, so the pin is load
bearing. Host Java is irrelevant; Bazel brings its own JDK.

There is **no Gradle build**, and writing one is not worth it: `setupdesign` and
`setupcompat` arrive as AOSP source tarballs patched with `ed`, not as Maven artifacts.

Tests exist under `src/test/` but the `android_local_test` targets in `BUILD` are
commented out upstream, so there is no working test command. Do not invent one.

The build outputs are symlinks into `~/.cache/bazel/`, already gitignored. Copy an APK you
intend to keep out of `bazel-bin/`; it is overwritten on every build.

→ Build internals, the three local patches and their failure signatures: `AI-MD/build.md`

## Architecture

Policy reaches Android through **two front ends that share one back end**. Knowing both
exist saves re-implementing a feature that is already there.

| Front end | Entry point | Declared in |
|---|---|---|
| Preference UI | `PolicyManagementFragment` | `src/main/res/xml/device_policy_header.xml` |
| adb shell | `DeviceAdminService.dump()` → `ShellCommand` | built in `ShellCommand.run()` |

Both call **`DevicePolicyManagerGateway`** (`DevicePolicyManagerGatewayImpl`), a wrapper
over `DevicePolicyManager` that takes success and error callbacks instead of throwing.
Prefer it for new policy calls.

The exception is `policy/locktask/KioskModeActivity`, which calls `DevicePolicyManager`
directly. That is the existing style inside that file; match it there rather than
converting it.

### The preference UI

`PolicyManagementFragment` is a single 4850-line fragment. Rows are declared in
`device_policy_header.xml` and dispatched by **key string** through `onPreferenceClick`
and `onPreferenceChange`. Adding a row means touching both files plus `strings.xml`.

Rows gate themselves through `testdpc:admin` and `testdpc:minSdkVersion` attributes, read
by `common/preference/DpcPreferenceHelper` and the `Dpc*Preference` subclasses. Use them
instead of hand-written enable or disable logic, and copy the constraints from the
neighbouring row.

The `search/` package indexes these screens, so a new preference becomes searchable with
no extra work.

### Kiosk mode and lock task

`KioskModeActivity` is the kiosk shell. It is **disabled in the manifest** and enabled at
runtime by `PolicyManagementFragment.startKioskMode()`, which also makes it the persistent
preferred HOME activity.

The detail that governs the current work: the activity **always appends TestDPC's own
package as the last row**, labelled *Stop kiosk mode*. It is the only tap-reachable way
out of lock task, and no configuration removes it.

→ The exit path, the password gate and why other escapes are closed:
`AI-MD/kiosk-and-lock-task.md`

### Driving policy over adb

Almost the whole policy surface is reachable without touching the screen, including lock
task packages, lock task features and user restrictions. This matters because the parent
runbook still describes those three as UI-only.

→ Invocation, the command list and the correction to the runbook:
`AI-MD/adb-shell-commands.md`

## Local deviations from upstream

Keep this list current. It is the diff a future reader needs to understand first, and
`git diff v9.0.12` is the check.

| Change | Why |
|---|---|
| `.bazelversion` = `6.5.0` | Upstream pins nothing; newer Bazel dropped native Android rules |
| `WORKSPACE`: `api_level` 34 → 35 | `EsimControlFragment` uses `VERSION_CODES.VANILLA_ICE_CREAM` |
| `WORKSPACE`: `androidx.core:core` 1.6.0 → 1.9.0 | `EsimControlFragment` uses `ContextCompat.RECEIVER_EXPORTED` |
| `WORKSPACE`: third `ed` patch on setupcompat | Bazel 6.5's manifest merger rejects `<queries><provider>` |

Upstream `v9.0.12` does not build as shipped. Do not "clean up" these four by reverting
them to upstream values.

## Conventions

**Match the file you are in.** `KioskModeActivity` uses anonymous inner classes, not
lambdas, and platform widgets rather than androidx. The app theme extends
`android:Theme.Material.Light.DarkActionBar`, a platform theme, so
`android.app.AlertDialog` is correct there and `androidx.appcompat` is not.

**Formatting is google-java-format**, 2-space indent, 100 columns. Upstream style.

**API level guards** go through `Util.SDK_INT` and `@TargetApi`, never a raw
`Build.VERSION.SDK_INT` comparison. `minSdkVersion` is 21 and the code still honours it.

**Never commit a signing keystore or an APK** into this repo.

## Working on the device

Changing this app means re-enrolling the phone, because our build is signed with a
different key from the Google-signed APK installed today, and a device owner cannot be
uninstalled. Read `AI-MD/deployment.md` before touching the handset. Do not run `adb`
against the phone casually; it is the only control channel once the lockdown is on.

## Documentation rules

One rule per section, stated in the first line, then why, then history. History last so it
can be skimmed and later trimmed without touching the rule. A fact lives in one file;
everything else links to it.

| Rule | Limit |
|---|---|
| The hub | ≤ 25 KB **of prose** — raw bytes only warn |
| Any one `AI-MD/` file | ≤ 10 KB **of prose** — over that, split it by topic |
| Every-request context | ≤ 40 KB across `~/.claude/CLAUDE.md`, `CLAUDE.md`, `CLAUDE.local.md`, this hub and `AGENTS.md` |
| Any one line | ≤ 600 characters |
| Section shape | one rule per section, stated in the **first line** |
| Duplication | a fact lives in one file; everything else links to it |

Reference tables and fenced code count toward no budget. A table row carries far more per
token than a paragraph, and splitting a lookup table across files makes it worse. Raw size
still warns, because it is what actually loads.

### Three triggers, kept separate

| Work | When | Cost |
|---|---|---|
| **Mechanical checks** | every commit touching the docs | a few hundred ms |
| **Updating a doc** | when you change the area it covers | proportionate |
| **Full re-verification against the code** | `/doc-check` by name, or when a `Last verified` date passes 90 days | occasional, done properly |

```bash
python3 .claude/skills/doc-check/check.py
```

Re-verification is deliberately off the per-commit path. It means reading the code, which
cannot be automated, and a rule nobody can follow discredits the rules beside it. A doc
openly marked stale is more useful than one hastily updated.
