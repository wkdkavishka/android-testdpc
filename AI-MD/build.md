# Building this fork

**Last verified:** 2026-09-11
**Source:** `WORKSPACE`, `BUILD`, `.bazelversion`, `setupcompat.BUILD`, `setupdesign.BUILD`

## Upstream v9.0.12 does not build as shipped

Three things in `WORKSPACE` are stale relative to the source at the same tag, and a fourth
is missing. All four are fixed locally. Reverting any of them re-breaks the build.

```bash
export ANDROID_HOME=/mnt/Storage/Android/Sdk
bazel build testdpc          # -> bazel-bin/testdpc.apk
```

## The four fixes, and how each failure looks

| Fix | Failure it prevents |
|---|---|
| `.bazelversion` = `6.5.0` | Bazel 8 has no native `android_binary`; Bazel 7 needs migration flags |
| `api_level` 34 → 35 | `could not resolve field VANILLA_ICE_CREAM` in `EsimControlFragment` |
| `androidx.core:core` 1.6.0 → 1.9.0 | `cannot find symbol: variable RECEIVER_EXPORTED` in `EsimControlFragment` |
| Third `ed` patch on setupcompat | `Missing 'name' key attribute on element provider` |

**The manifest patch needs the most explaining.** `setupcompat`'s
`partnerconfig/AndroidManifest.xml` declares `<provider android:authorities=…>` inside a
`<queries>` block. That is valid modern Android, where `<queries><provider>` is matched by
authority and carries no `android:name`. The manifest merger bundled with Bazel 6.5
predates it and applies the ordinary `<provider>` rule, which demands `android:name`.

The patch deletes that one line during fetch, using the same `ed` mechanism upstream
already uses on two Java files in the same archive. It is only a package-visibility hint,
and TestDPC declares `QUERY_ALL_PACKAGES`, so nothing changes at runtime.

`--android_manifest_merger=legacy` looks like a cleaner fix and is not one. Bazel throws
`UnsupportedOperationException` from `AndroidSemantics.maybeDoLegacyManifestMerging`; the
legacy merger is not implemented.

## Why Bazel, and why not Gradle

The `setupdesign` and `setupcompat` dependencies are fetched from `android.googlesource.com`
as `+archive` tarballs of AOSP source and built from that source, with `ed` patches applied
in flight. They are not published Maven artifacts. A Gradle port would have to vendor both
as modules, so the effort is real and the payoff is only familiarity.

`ed` must be on the PATH for the build to work. It is a build dependency, which is unusual
enough to be worth saying out loud.

## Things that are not problems

**Host Java version does not matter.** Bazel downloads its own JDK toolchain. Java 25 on the
host builds this fine, despite the project being far older.

**`android_sdk_repository` picks the newest installed build-tools** and did not object to
37.0.0. If a future SDK update does break it, pin `build_tools_version` beside `api_level`.

**`targetSdkVersion` stays 34** in the manifest. Only the compile SDK moved to 35. These are
different things and the target is deliberate.

## Output

`bazel build` prints three artifacts. `bazel-bin/testdpc.apk` is the one to install;
`testdpc_unsigned.apk` and `testdpc_deploy.jar` are intermediates.

It is signed with **Bazel's built-in debug key**, `CN=Android Debug, O=Android, C=US`. That
key is fixed inside Bazel, so it is stable across rebuilds, but it is not ours and should
not be what ships. See `AI-MD/deployment.md` for why the signing key decides whether the
phone needs re-enrolling.

`bazel-bin` and friends are symlinks into `~/.cache/bazel/`, which holds well over a
gigabyte after a full build. They are gitignored and safe to delete; `bazel clean --expunge`
also discards the downloaded dependencies and forces a slow refetch.
