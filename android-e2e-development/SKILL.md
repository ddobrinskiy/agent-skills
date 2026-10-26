---
name: android-e2e-development
description: >
  Use when building or debugging an Android app and proving real end-to-end
  behavior on an emulator or physical device — build, install the exact APK,
  exercise the actual user journey, and record honest evidence. Also covers
  running regressions in an isolated, agent-owned emulator (explicit adb
  server/serial, resource limits, signing keys, camera scenes, IME checks)
  and the instrumentation-test traps that produce false passes.
---

# Android E2E Development

A practical workflow for developing Android applications and proving behavior across the build, installation, device UI, backend, and external dependencies. Apply it to the project's own stack and conventions; do not assume a successful build or install proves the feature works.

## When to Use

- Implementing or debugging an Android app feature that must work on an emulator or physical device.
- Verifying a change through the actual app and any required service/API.
- Running regression or instrumentation suites in an emulator you own, possibly alongside other agents on a shared host.
- Establishing a repeatable local Android development and device-test loop.

Do not use as a substitute for repository-specific instructions, security review, or a device owner's approval for destructive or account-sensitive actions.

## Prerequisites

- Read the repository's `AGENTS.md`, `README`, build files, and existing test guidance before changing code.
- Identify the app module, application ID, build variant, minimum/target SDK, required runtime services, test framework, and existing device/emulator conventions.
- Confirm Android SDK/JDK/build-tool requirements and install only missing prerequisites through the project's documented method.
- Confirm the intended emulator/device with `adb devices -l`; when more than one target is connected, select it explicitly with `adb -s <serial>` on every device command.
- Keep credentials in the project's approved secret mechanism. Never paste secrets into source, command output, logs, screenshots, or test reports.

## Development Loop

1. **Establish baseline.** Check the working tree, current branch, and relevant tests. Run the smallest existing build/test command for the affected module and record failures that predate the change.
2. **Trace the user journey.** Map the requested behavior from UI action through app state, network/service calls, persistence, and visible result. Identify observable success and failure signals at each boundary.
3. **Choose the right test level.** Add unit tests for deterministic logic, instrumented/UI tests for Android framework behavior, and E2E checks for critical integrated journeys. Keep test data isolated and clean up only data created by the test.
4. **Write RED first.** For a bug fix, write a test that reproduces it and observe it fail before touching production code; then run the focused test GREEN, then the existing suites.
5. **Make one coherent change.** Follow existing architecture and style. For multiple independent UI changes that need human device feedback, build and install after each change rather than deferring all feedback to the end.
6. **Build and test.** Run focused tests first, then the relevant debug build and static checks. Treat a fast build as potentially incremental: inspect task output and artifact modification time to ensure changed code was compiled.
7. **Install the exact artifact.** Install the intended variant on the selected device. Do not treat the installer reporting success as proof that the intended APK is running. Pull the installed base APK and compare its SHA-256 with the deliverable.
8. **Exercise the real flow.** Perform the actual user action on the emulator/device; verify the resulting UI, app state, and required backend/service effect. For UI work, capture and inspect a screenshot. Collect bounded, relevant logcat output only when it helps explain a failure.
9. **Check regressions and cleanup.** Re-run relevant tests after merges or rebases, inspect the final diff, and verify no test fixtures, temporary secrets, or unrelated files were included.

## Useful Commands

Adapt paths, variants, and target serial to the project:

```sh
# Discover devices and emulators
adb devices -l

# Build and test (examples; use tasks available in the project)
./gradlew testDebugUnitTest
./gradlew connectedDebugAndroidTest
./gradlew assembleDebug

# Install to one explicit target
adb -s <serial> install -r <path-to-debug-apk>

# Resolve and pull the APK currently installed for a package, then compare hashes
adb -s <serial> shell pm path <application-id>
adb -s <serial> pull <base-apk-path-from-pm> installed.apk
sha256sum installed.apk <path-to-debug-apk>

# Capture a device screenshot for visual inspection
adb -s <serial> exec-out screencap -p > <artifact-path>/screen.png

# Capture bounded logs around one reproduction
adb -s <serial> logcat -d -t 2000
```

`connectedDebugAndroidTest` requires a compatible connected target; it is not a substitute for exercising flows that depend on real accounts, services, hardware, or production-like configuration.

## Isolated Emulator Regressions

When you run an emulator yourself — especially on a shared host or next to other agents — own it completely and leave nothing behind.

- **Address only your targets.** Use the assigned adb server port (`adb -P <port>` or `ANDROID_ADB_SERVER_PORT`) and emulator serial on every command. Never kill a shared adb server or touch a physical device assigned to someone else.
- **Clone, don't mutate.** Copy an existing AVD into task-owned scratch before changing its settings (e.g. `show_ime_with_hard_keyboard`), so the shared AVD stays untouched.
- **Pass environment explicitly.** Give background emulator commands `ANDROID_SDK_ROOT`, `ANDROID_AVD_HOME`, etc. directly; exports in a foreground shell often do not reach background processes.
- **Respect resource limits.** Emulator renderer and camera threads can exhaust a pids-limited container. Run instrumentation in short batches, stop the emulator between batches when limits are hit, and build with the emulator stopped after resource exhaustion. Never raise host limits to compensate.
- **Split heavy suites.** Give scripts a case filter so independent cases (e.g. two barcode formats, two handler flows) run in fresh short emulator sessions. Keep an interrupted combined log as a failure; prove the remaining cases with separate output instead of inferring success.
- **Shut down before handing back.** Stop the emulator and confirm the assigned adb device list is empty; leaked renderer threads can starve unrelated tools on the host.
- **Keep the app's signing identity.** The debug key that signed the installed app may live in the isolated SDK/AVD home, not `~/.android/debug.keystore`. Pass the verified key explicitly (Gradle `android.injected.signing.*` properties) instead of uninstalling user packages to get around a signature mismatch.
- **Re-verify after cold boot.** AVD persistence can be unreliable: check that the app, test, and fixture APKs are still installed after each cold boot and reinstall the exact artifacts. A missing instrumentation package is not a regression.
- **Bridge local services deliberately.** Use `adb -s <serial> reverse` to expose host loopback services to the device and `adb forward` to an owned port for Chrome DevTools; remove them when done.

## Instrumentation Test Traps

These produce false passes or hangs; design tests to rule them out.

- **Give suppression tests a positive control.** After asserting that something is dismissed or not shown, trigger a different valid input and assert the expected UI *does* appear. Otherwise a stuck paused or modal state passes the test.
- **Clear stale foreground tasks.** Force-stop external fixtures/handlers before launching the activity under test; another app on top of the task can make `getActivity()`/`startActivitySync()` wait forever.
- **Check the inherited scene.** Verify starting state before a focused run. A leftover dialog or an input auto-decoded from a previous scene can break the first assertion; record that as test contamination, not as an app defect or a pass.
- **Wait for the result, not for idle.** `waitForIdleSync()` can return before Choreographer- or layout-posted callbacks (e.g. `AdapterView`/Spinner selection). Poll for the resulting selection or persisted value with a bound, and keep a separate real-tap test so polling cannot hide an unreachable control.
- **Launch for real.** Test external intent resolution by actually starting the intent (e.g. `ACTION_VIEW` + `CATEGORY_BROWSABLE`); `PackageManager` queries are visibility-filtered and can disagree with real launches. Don't add production `<queries>` declarations just to satisfy a test fixture.
- **Keep test hooks out of production.** Test-only URI schemes, flags, or preferences belong in explicit test opt-ins, never in shipped defaults.
- **Count events by identity.** To prove a tap emits exactly one command/broadcast, compare unique record IDs from `dumpsys activity broadcasts` history before and after the tap, not repeated action strings. That proves delivery only, not the downstream effect.
- **Set touch mode for screenshots.** Call `setActivityInitialTouchMode(true)` before `getActivity()` when capturing touch-facing UI; keyboard focus highlights can invert apparent selection cues.
- **Label simulated flows honestly.** An intercepted chooser or manually simulated lifecycle is not a real external round trip; report them separately.

## Emulator Hardware and Visual Checks

- **Camera scenes are cached.** The emulator's image-file virtual camera may keep the old image while the camera stays open. After replacing the source image, close and reopen the camera (force-stop/start for E2E) before reading results. Measure a known circle or square in the frame to catch non-uniform scaling.
- **Use purpose-built scenes.** Use a blank scene for tests that must not decode anything and a deliberate barcode scene for real decode tests.
- **Prove the soft keyboard is really there.** Viewport shrinking alone is not evidence. Check `dumpsys input_method` and a full native screencap; record `visualViewport` height/offset, focus, and element bounds, and subtract toolbar overlap when judging usable height. An element can be geometrically "visible" yet fully hidden in the native screenshot.
- **Match references pixel for pixel.** For screenshot-matched UI, sample the reference palette, capture the final installed APK, crop without scaling at identical dimensions, and inspect both images side by side (give reviewers both). Check custom-drawn controls for stretched drawables and keep platform accessibility/interaction intact.
- **Keep evidence immutable.** Preserve earlier screenshots and logs; put final-run artifacts under a distinct prefix and recapture after a fix rather than describing an unrendered change.
- **Separate browser matrices.** Stop the emulator before running a desktop browser responsive matrix on the same constrained host. If the harness was wrong, mark those results superseded rather than filing app defects.

## End-to-End Evidence

For each requested journey, record:

- Device/emulator model or API level and the exact build variant tested.
- The user action performed and the observable result.
- Whether external services were real, local, mocked, or unavailable.
- Relevant test/build result and any remaining limitation.
- For visual changes, a screenshot inspected at the actual device resolution.

Distinguish clearly between **compiled**, **automated test passed**, **installed**, **observed on device**, and **confirmed by the user**. Do not upgrade one evidence level into another. A green CI job does not prove a feature works on a physical device; a successful HTTP response does not prove the UI handled it correctly; emulator camera decoding does not prove physical optics; a delivered command does not prove an authenticated service state.

## Failure Diagnosis

1. Reproduce one failure at a time with the same app version, device, and configuration.
2. Locate the earliest failing boundary: test/build, install/package, UI/input, app state, network, backend, or third-party service.
3. Collect the minimum evidence needed: focused test output, targeted logcat window, app/network diagnostics, and the screen state. Redact secrets and personal data before retaining or sharing artifacts.
4. Fix the root cause at the failing layer; avoid changing unrelated permissions, transport, service configuration, or device settings to mask the symptom.
5. Repeat the original scenario and a relevant regression test. Report unresolved cases as inconclusive or blocked, not as passes. When the owner asked for bounded verification, don't loop restarts hoping for a green run.

## Pitfalls

- A successful build proves compilation, not runtime behavior.
- `adb install` success and package metadata alone do not prove the intended binary is active; compare artifact hashes or verify a unique changed behavior.
- A screenshot proves a rendered state, not touchability, persistence, backend completion, or later lifecycle behavior; test those separately where required.
- An empty or tag-filtered logcat capture is inconclusive. Capture a bounded window around a controlled reproduction before narrowing filters.
- Emulators differ from physical hardware in audio, camera, Bluetooth, sensors, keyboard/IME, network routing, and vendor behavior. Use the real device when those are part of acceptance.
- Merges and rebases can combine individually green changes into a failing app. Rebuild, reinstall, and re-test the integrated result.
- Do not clear app data, uninstall user apps, alter account state, or trigger paid/irreversible backend actions unless explicitly within scope and authorized.

## Completion Criteria

The requested behavior is complete only when the relevant automated checks pass, the intended build is installed on the selected target, the critical user journey has been exercised at the appropriate integration level, UI results have been inspected when relevant, any emulator you started is stopped, and limitations are stated accurately. If a required device, credential, service, or user action is unavailable, report the precise blocker and stop short of claiming full E2E verification.
