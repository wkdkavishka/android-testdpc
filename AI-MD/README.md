# AI-MD — subsystem reference

Detail that does not belong in every request. The hub,
`.github/copilot-instructions.md`, carries the architecture map and links here.

| Doc | Covers |
|---|---|
| `build.md` | Bazel setup, the four local build fixes and what each failure looks like |
| `kiosk-and-lock-task.md` | How the kiosk shell starts, the exit row, the policies it applies |
| `adb-shell-commands.md` | TestDPC's dumpsys CLI, and where it contradicts the parent runbook |
| `deployment.md` | Signing, device-owner enrolment, what survives a swap |

Each file carries a `Last verified` date. The check warns once one passes 90 days; that is
a prompt to re-read the code, not to bump the date.

Not here: the device procedure itself. That lives in `DEVICE-LOCKDOWN.md` in the parent
folder, outside this repo, and stays the authority on the handset.
