#!/usr/bin/env bash
set -euo pipefail
# Standalone upstream build, never writes to frontend or its Maven repository.
destination=${1:?Pass a NEW temporary build directory}
if [[ -e "$destination" ]]; then echo 'Refusing to reuse an existing directory' >&2; exit 1; fi
mkdir -p "$destination/source" "$destination/result"
destination=$(cd "$destination" && pwd)
source_dir="$destination/source"
curl --fail --location --retry 3 \
  https://github.com/k2-fsa/sherpa-onnx/archive/refs/tags/v1.13.8.tar.gz \
  --output "$destination/source.tar.gz"
echo "b0374cc56dbc186d442ae73d5de743bb092470b640c4c50ce7b029044c0c4fa8  $destination/source.tar.gz" | sha256sum --check
tar -xzf "$destination/source.tar.gz" --strip-components=1 -C "$source_dir"
printf '%s\n' 'sherpa-onnx v1.13.8 / commit 11afbd009a7f8c08f4bcf2fc1b265d0df4670fbf' > "$destination/result/provenance.txt"
java -version 2>> "$destination/result/provenance.txt"
cmake --version >> "$destination/result/provenance.txt"
ninja --version >> "$destination/result/provenance.txt"
cat "$ANDROID_NDK/source.properties" >> "$destination/result/provenance.txt"

# Equivalent to upstream Android flags, with unused TTS/diarization explicitly OFF.
# CMake FetchContent downloads use upstream URL_HASH pins, including ONNX Runtime.
cmake -S "$source_dir" -B "$destination/native" -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE="$ANDROID_NDK/build/cmake/android.toolchain.cmake" \
  -DCMAKE_BUILD_TYPE=Release -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-24 \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DANDROID_STL=c++_static -DBUILD_SHARED_LIBS=ON \
  -DCMAKE_SHARED_LINKER_FLAGS='-Wl,-z,max-page-size=16384' \
  -DSHERPA_ONNX_ENABLE_TTS=OFF \
  -DSHERPA_ONNX_ENABLE_SPEAKER_DIARIZATION=OFF \
  -DSHERPA_ONNX_ENABLE_JNI=ON -DSHERPA_ONNX_ENABLE_C_API=OFF \
  -DSHERPA_ONNX_ENABLE_BINARY=OFF -DSHERPA_ONNX_BUILD_C_API_EXAMPLES=OFF \
  -DSHERPA_ONNX_ENABLE_PYTHON=OFF -DSHERPA_ONNX_ENABLE_TESTS=OFF \
  -DSHERPA_ONNX_ENABLE_PORTAUDIO=OFF -DSHERPA_ONNX_ENABLE_WEBSOCKET=OFF \
  -DSHERPA_ONNX_USE_PRE_INSTALLED_ONNXRUNTIME_IF_AVAILABLE=OFF
cmake --build "$destination/native" --target sherpa-onnx-jni --parallel 2

# Use upstream Gradle wrapper and Kotlin bindings; remove optional TTS Java APIs
# from the AAR source set as well. No modifications to the upstream C++ algorithm.
python3 "$(dirname "$0")/package.py" "$destination"
packaging="$source_dir/android/SherpaOnnxAar"
(cd "$packaging" && bash ./gradlew --no-daemon :sherpa_onnx:assembleRelease)
cp "$packaging/sherpa_onnx/build/outputs/aar/sherpa_onnx-release.aar" \
  "$destination/result/sherpa-onnx-1.13.8-no-tts-arm64.aar"
cp "$destination/native/CMakeCache.txt" "$destination/result/CMakeCache.txt"
