# Getting a build onto the phone

**Last verified:** 2026-09-11
**Source:** `src/main/AndroidManifest.xml`, `BUILD`, and the parent `DEVICE-LOCKDOWN.md`

## The signing key decides whether the phone must be re-enrolled

The APK installed today is signed by Google, `CN=testdpc, O=Google Inc.`, SHA-256
`8090f663…`. Any build of ours carries a different key, and Android refuses to replace an
installed package with one signed differently.

A device owner also cannot be uninstalled: `pm uninstall` returns
`DELETE_FAILED_DEVICE_POLICY_MANAGER`, and `pm disable-user` refuses because holding the
role makes the package protected.

So the first swap is unavoidably: clear the device owner, uninstall, install ours, enrol
again, reconfigure. Enrolment needs **zero accounts on the device**, which is what made the
original `dpm set-device-owner` work, and is worth re-checking before starting.

What survives the swap and what does not is the part people get wrong:

| State | Survives? |
|---|---|
| Disabled packages, Doze exemptions, runtime grants | **Yes** — PackageManager state, independent of the DPC |
| Lock task list, lock task features, user restrictions, kiosk | **No** — device-owner policy, cleared with the owner |

## Use one keystore, from the first build onward

Bazel signs with its own fixed debug key unless told otherwise. That key is stable, but it
is not ours, and the key chosen for the first install is the key every later update must
match.

Sign every build with a keystore we control, so a later rebuild is an in-place
`adb install -r` that keeps device owner and every policy. Getting this wrong costs a
second full re-enrollment.

```bash
BT=/mnt/Storage/Android/Sdk/build-tools/36.1.0
$BT/zipalign -f 4 bazel-bin/testdpc.apk testdpc-kiosk.apk
$BT/apksigner sign --ks <keystore> testdpc-kiosk.apk
$BT/apksigner verify --print-certs testdpc-kiosk.apk
```

Never commit the keystore or the signed APK to this repo.

## testOnly is a convenience, not the escape hatch

`android:testOnly="true"` makes `dpm remove-active-admin` work over adb. It is worth
setting while iterating, and removing for the final build; dropping it later is an in-place
update, not another re-enrollment, provided the keystore did not change. A testOnly APK
installs with `adb install -t`.

It is **less necessary than it first appears**, because TestDPC can already be told to
stand down over adb with `clear-device-owner`, on any build including the Google-signed one.
See `AI-MD/adb-shell-commands.md`.

## Before locking anything down

Authorise a USB cable and confirm it, because wireless adb does not survive the lockdown
and the *Allow USB debugging?* prompt cannot be tapped once lock task hides it.

```bash
adb devices -l          # the device must appear WITHOUT an ip:port
```

The parent `DEVICE-LOCKDOWN.md` is the authority on the rest: which packages to allowlist,
which features to enable, the eight verification steps, and rollback. Do not restate any of
it here.
