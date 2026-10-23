# CogniFit iOS warning cleanup

The fork's `main` branch starts at Apache's **8.1.3** tag, the version used
by CFApp when this cleanup was prepared. Upstream development stays on `master`. It leaves Android, JavaScript, version numbers and app dependencies
unchanged. CFApp adoption is separate from merging these plugin changes; no app
dependency is changed by this fork PR.

## Changes and provenance

Backported from Apache's master branch:

- `8c956e6` / #659: use owned strings for file reads instead of the deprecated
  `CDVPluginResult.associatedObject` lifetime workaround.
- `6f9f745` / #658: modern percent encoding/decoding. Adjusted here to also retain
  `?` in whole URIs to retain the original query encoding behavior. Path-only encoding still escapes `?`.
- `928555e` / #657: remove the incompatible mutable-settings dictionary type.
  Adapted to retain guarded `CDVViewController` access: the upstream refactor
  assumes a property type that older Cordova headers do not provide. The
  unused settings type alias is omitted.

Additional local changes:

- MIME lookup using UniformTypeIdentifiers on iOS 14 or later, retaining
  the original MIME fallbacks and using ARC ownership for returned strings.
- Availability-checked MobileCoreServices fallback for iOS 11–13, with a weak
  framework link so introducing UniformTypeIdentifiers does not raise the OS floor.
- Prefer Cordova's current umbrella header when available and replace its
  deprecated OS-version macro with the native availability check.
- Remove the AssetsLibrary implementation, public constants, native URL handling,
  filesystem registration and framework dependency entirely.

**Intentional compatibility break (approved 2026-10-23):** this fork does not
support native `assets-library://` URLs or the `cdvfile://localhost/assets-library/`
filesystem root at any deployment target. CFApp uses the File plugin for app-owned
storage and does not use this photo-library bridge. There is no AssetsLibrary
warning suppression or replacement Photos dependency. The only production
suppression left is the availability-checked MIME fallback for iOS 11–13.

## Validation

On macOS with Xcode installed:

```sh
npm ci --ignore-scripts
npm test
CORDOVA_HEADERS=/absolute/path/to/cordova-ios/CordovaLib/include sh tests/ios-warning-compile.sh
python3 tests/ios-warning-regressions.py
```

The compiler check builds both implementation files with warnings as errors
at simulator deployment targets 11, 17 and 26. It needs an SDK that supports iOS 26
and was checked with Cordova iOS 6.2.0, 7.1.1 and 8.0.1 headers, as well
as CFApp's installed Cordova iOS 8 fork. This is compilation of
the plugin sources, not a full app link or device test. Cordova headers are
treated as external system headers so their own deprecated declarations do not
mask warnings in the plugin sources.

The native regression harness runs actual extracted source methods with Apple's
Foundation and type registry on the Mac. It checks URI encoding against the old
API for printable ASCII, existing escapes, Unicode and queries; rejection of legacy native photo URLs;
local filesystem URL round trips; MIME lookup; and unknown or missing files. Its
legacy calls are test oracles only. It needs access to the system type registry,
which may require running outside a restricted process sandbox.

Not checked: runtime behavior on iOS 11–13, device
file operations, or the full Cordova plugin integration suite. Before app
adoption, install the fork in an isolated app checkout and run that suite plus a
real-device app-storage file smoke test. Pin a reviewed commit only after the current
release is complete and adoption is explicitly requested.

## CI

The fork PR runs lint plus native compilation and behavior regressions with
Cordova iOS 6.2.0, 7.1.1 and 8.0.1 headers on a current macOS runner. These replace
the inherited iOS workflow, which referenced retired runners/Xcode combinations
and allowed test failures. The checks fail the PR on errors.

The inherited Android and Chrome runtime suites remain available manually and
run automatically for their platform sources, shared JavaScript, integration-test
sources and package changes. They do not run for an iOS-only native cleanup.
Changes to plugin.xml alone require manually running those suites if they affect
Android/browser configuration. They have not been run for this iOS-only change.

## Later upstream contribution

Do not resubmit fixes that Apache already merged. Prepare a focused contribution
for the new MIME lookup changes and/or the whole-URI query regression against
Apache master, following CONTRIBUTING.md and Apache's contribution rules. The
availability guards retain older iOS support; they do not guarantee acceptance.
The AssetsLibrary removal is a deliberate CogniFit fork divergence and should
remain separate from a compatibility-preserving upstream warning cleanup.
