"""Prepare only the downloaded upstream standalone AAR project."""
import pathlib
import shutil
import sys


def main(work):
    source = work / 'source'
    module = source / 'android/SherpaOnnxAar/sherpa_onnx'
    api_source = module / 'src/main/java'
    # Keep upstream's default src/main/java for both AGP and Kotlin 1.7.20.
    # Do not copy bindings into a second root: Kotlin retains its default roots
    # even when only AndroidSourceSet.java is redirected.
    for kotlin in api_source.rglob('*.kt'):
        if kotlin.name in {'Tts.kt', 'OfflineSpeakerDiarization.kt'}:
            kotlin.unlink()
    wrapper = source / 'android/SherpaOnnxAar/gradle/wrapper/gradle-wrapper.properties'
    with wrapper.open('a', encoding='utf-8') as out:
        out.write('\ndistributionSha256Sum=9631d53cf3e74bfa726893aee1f8994fee4e060c401335946dba2156f440f24c\n')
    # No AndroidX/UI dependencies are needed by these plain Android Kotlin APIs.
    # Reuse pinned upstream plugins + Gradle, not the Sailing Setup project.
    (module / 'build.gradle.kts').write_text('''plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.jetbrains.kotlin.android)
}
android {
    namespace = "com.k2fsa.sherpa.onnx"
    compileSdk = 34
    defaultConfig { minSdk = 24 }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }
    kotlinOptions { jvmTarget = "1.8" }
    buildTypes.getByName("release") { isMinifyEnabled = false }
}
''', encoding='utf-8')
    target = module / 'src/main/jniLibs/arm64-v8a'
    target.mkdir(parents=True, exist_ok=True)
    for name in ('libsherpa-onnx-jni.so', 'libonnxruntime.so'):
        candidates = list((work / 'native').rglob(name))
        if name == 'libonnxruntime.so':
            candidates = [p for p in candidates if 'arm64-v8a' in p.parts]
        if len(candidates) != 1:
            raise RuntimeError(f'{name}: expected one build output, got {candidates}')
        shutil.copyfile(candidates[0], target / name)
    shutil.copyfile(source / 'LICENSE', work / 'result/sherpa-onnx-LICENSE')
    # Preserve this packaging adaptation for reproducibility/review.
    shutil.copyfile(module / 'build.gradle.kts', work / 'result/packaging.gradle.kts')


if __name__ == '__main__':
    main(pathlib.Path(sys.argv[1]).resolve())
