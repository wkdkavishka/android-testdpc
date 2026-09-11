# Kiosk mode and lock task

**Last verified:** 2026-09-11
**Source:** `src/main/java/com/afwsamples/testdpc/policy/locktask/KioskModeActivity.java`,
`src/main/java/com/afwsamples/testdpc/policy/PolicyManagementFragment.java`,
`src/main/AndroidManifest.xml`

## The kiosk shell is an activity that is disabled until it is needed

`KioskModeActivity` is declared `android:enabled="false"` with an
`intent-filter` for `category.HOME`. Nothing can launch it until the app switches it on.

`PolicyManagementFragment.startKioskMode()` does three things in order, and all three
matter:

1. `setComponentEnabledSetting(…, COMPONENT_ENABLED_STATE_ENABLED)` to wake the component
2. `addPersistentPreferredActivity(…, Util.getHomeIntentFilter(), …)` to seize HOME
3. launches a HOME intent carrying `LOCKED_APP_PACKAGE_LIST`

`KioskModeActivity.onStart()` then calls `startLockTask()` if the activity manager reports
`LOCK_TASK_MODE_NONE`. The package list arrives as an intent extra on first start and is
persisted to the `kiosk_preference_file` shared preferences, so a reboot restores the grid
without re-applying policy.

## The exit row always exists, and cannot be configured away

In `onCreate`, TestDPC removes its own package from the list and appends it again:

```java
mKioskPackages.remove(getPackageName());
mKioskPackages.add(getPackageName());
```

The adapter renders that last row with the label `R.string.stop_kiosk_mode` rather than the
app name, and tapping it calls `onBackdoorClicked()`. Upstream calls this the back door in
its own comments.

So no choice in the kiosk app picker removes the exit. **This is the hole the password gate
closes**, and it is why the parent runbook treats TestDPC as simultaneously the lockdown and
its own weakest point.

`onBackdoorClicked()` unwinds everything: `stopLockTask()`, restores the saved user
restrictions, clears the persistent preferred activity, disables the component again, then
opens `PolicyManagementActivity`.

**`stopLockTask()` is the first statement.** Any password check must sit in front of the
whole method. A gate that runs after it has already let the device out of lock task.

## Policies the kiosk applies on its own

Starting kiosk mode sets five user restrictions beyond whatever is already configured, and
restores their previous values on exit. They are listed in `KIOSK_USER_RESTRICTIONS`:
safe boot, factory reset, add user, mount physical media, adjust volume.

`saveCurrentConfiguration()` snapshots the prior values into the same preferences file
first, which is why exiting cleanly matters more than it looks. A kill that skips
`onBackdoorClicked()` leaves those five restrictions applied.

## Other routes into the policy UI, and why they are shut

`PolicyManagementActivity` is exported with a `LAUNCHER` intent filter, so it looks
reachable. Under lock task it is not: `KioskModeActivity` holds HOME, so there is no app
drawer, and the kiosk grid launches only allowlisted packages by their own launch intents.

Input methods are **not** gated by the lock task allowlist, so the keyboard keeps working
without being listed. Do not add one, and do not touch `setPermittedInputMethods` — a list
that excludes the active keyboard leaves the device with no way to type at all.

## The stronger fix, not taken

Moving `startLockTask()` and `category.HOME` into an app we control, and leaving TestDPC out
of the lock task allowlist entirely, makes TestDPC unreachable rather than merely
password-protected. The parent runbook recommends this. The password gate is the cheap
version, and the two are not mutually exclusive.
