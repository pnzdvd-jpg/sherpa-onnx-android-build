# Android ARM64 sherpa-onnx 1.13.8 without TTS

Standalone build tools. No application source, assets, models or credentials are required.
Reuses upstream sherpa-onnx v1.13.8; downloads are verified against fixed checksums.
TTS and speaker diarization are disabled. JNI and KWS remain enabled.
Other speech functionality may remain: this is not a strictly KWS-only core.

## Execution
Only workflow_dispatch is enabled; authorized defaults to false.
The job is skipped for private repositories. Uses the standard ubuntu-24.04 runner,
Temurin JDK 17, Android NDK 28.1.13356709 and CMake 3.22.1 with Ninja.
No paid service, cache, package publication or application build is configured.
Artifacts are retained for one day. Confirm storage allowance and a budget blocking
billable usage before dispatch. Public standard runner minutes are free.
https://docs.github.com/en/billing/concepts/product-billing/github-actions

After explicit owner approval, publish this directory on main, then manually run
Prepare sherpa 1.13.8 Android ARM64 without TTS with authorized=true.
Publication does not trigger a build.

## Validation
python -B -m unittest discover -s tools/sherpa-no-tts -p "test_*.py"

The build verifies ARM64 ELF, 16 KB load alignment, KWS JNI exports, absence of
TTS/eSpeak symbols and compilation units, native dependencies and license evidence.
Output includes a candidate AAR, reports, dependency notices and SHA-256 inventory.
The actual dependency licenses still require review before redistribution.
No replacement of any existing application dependency is performed.
No successful remote build or Android device testing has yet been established.

## Redistribution
The helper code is supplied for publication by its owner. It contains build and
inspection logic, not upstream binaries. Downloaded upstream components retain
their own licenses; notices are collected by verify.py. Bit-for-bit reproducibility
has not been demonstrated because runner images and Maven dependencies may vary.
