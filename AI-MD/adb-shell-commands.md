# Driving TestDPC over adb

**Last verified:** 2026-09-11
**Source:** `src/main/java/com/afwsamples/testdpc/ShellCommand.java`,
`src/main/java/com/afwsamples/testdpc/DeviceAdminService.java`,
`src/main/java/com/afwsamples/testdpc/util/flags/Flags.java`

> **Read from the source, not yet run against the handset.** No device was attached when
> this was written. Confirm with `help` before relying on any of it.

## TestDPC exposes a CLI through dumpsys

`DeviceAdminService.dump()` hands its arguments straight to `ShellCommand`, so the whole
policy surface is drivable from a laptop. Upstream documents the form in the `ShellCommand`
class javadoc:

```bash
adb shell dumpsys activity --user 0 service com.afwsamples.testdpc help
```

`help` lists every command with its description, generated from the same `Flags`
definitions that parse the arguments, so it cannot drift from what is implemented.

The service is `exported="true"` behind `BIND_DEVICE_ADMIN` and enabled only on Android O
and later, via `android:enabled="@bool/is_o_or_later"`.

## This contradicts the parent runbook, and the runbook is wrong

`DEVICE-LOCKDOWN.md` says of its Part 2: *"None of this can be done over adb… It all gets
tapped into TestDPC on the phone."* That is true of the `dpm` tool, which is what it was
written against. It is not true of TestDPC itself.

All three of the sections it describes as manual have commands:

| Runbook section | Command |
|---|---|
| 2.2 lock task packages | `set-lock-task-packages <pkg>…` |
| 2.3 lock task features | `set-lock-task-features <int flags>` |
| 2.4 user restrictions | `set-user-restriction <name> <true\|false>` |

Read-backs exist for each, so a configuration can be verified rather than eyeballed:
`get-lock-task-packages`, `get-lock-task-features`, `list-user-restrictions`,
`is-lock-task-permitted`.

This turns re-enrolling the phone from a long UI session into a script, which matters
because changing this app forces a re-enrollment every time.

Note `set-lock-task-features` takes the **integer flag value**, not names. The checkbox
labels in the UI map to `DevicePolicyManager.LOCK_TASK_FEATURE_*` constants, which have to
be OR-ed together by hand.

## The device owner can remove itself over adb

```bash
adb shell dumpsys activity --user 0 service com.afwsamples.testdpc clear-device-owner
```

`clear-device-owner` calls `DevicePolicyManager.clearDeviceOwnerApp()` through the gateway.
`remove-active-admin` is the matching call for the admin component.

Two consequences, and the second is easy to miss:

- **The runbook's "You cannot undo this over adb" is wrong.** It is true of
  `dpm remove-active-admin`, which refuses a non-test admin, and false of asking TestDPC to
  stand down. That works on the stock Google-signed build installed today.
- **This is also a hole in the lockdown.** Anyone with an authorised USB host can clear the
  device owner. The password gate does not change that, and neither does anything else
  short of `DISALLOW_DEBUGGING_FEATURES`.

## What this does not cover

There is no command to start or stop kiosk mode. `KioskModeActivity` is reached only
through `PolicyManagementFragment.startKioskMode()`, so starting the kiosk stays a UI step
even though everything it depends on can be scripted.

Commands run on a binder thread and report through a `PrintWriter`. Some post work to a
handler and return before it finishes, so a read-back is worth more than a silent success.
