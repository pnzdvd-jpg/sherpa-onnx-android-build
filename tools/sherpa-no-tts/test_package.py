import importlib.util
import pathlib
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("aar_package", pathlib.Path(__file__).with_name("package.py"))
packaging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packaging)


class PackagingTests(unittest.TestCase):
    def test_single_source_root_and_filtered_apis(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = pathlib.Path(temporary)
            module = work / "source/android/SherpaOnnxAar/sherpa_onnx"
            api = module / "src/main/java/com/k2fsa/sherpa/onnx"
            api.mkdir(parents=True)
            retained = {
                "KeywordSpotter.kt": "class KeywordSpotter { external fun decode() }",
                "OnlineRecognizer.kt": "class OnlineModelConfig",
                "OnlineStream.kt": "class OnlineStream",
                "WaveReader.kt": "class WaveReader",
            }
            for name, text in {**retained, "Tts.kt": "class OfflineTts", "OfflineSpeakerDiarization.kt": "class OfflineSpeakerDiarization"}.items():
                (api / name).write_text(text)
            wrapper = module.parent / "gradle/wrapper/gradle-wrapper.properties"
            wrapper.parent.mkdir(parents=True)
            wrapper.write_text("distributionUrl=pinned-upstream\n")
            (work / "source/LICENSE").write_text("upstream license")
            (work / "result").mkdir()
            for path in ("native/lib/libsherpa-onnx-jni.so", "native/_deps/onnxruntime-src/jni/arm64-v8a/libonnxruntime.so"):
                target = work / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"test fixture")
            packaging.main(work)
            self.assertEqual({p.name for p in api.glob("*.kt")}, set(retained))
            for name, text in retained.items():
                self.assertEqual((api / name).read_text(), text)
            self.assertFalse((module / "src/no-tts").exists())
            gradle = (module / "build.gradle.kts").read_text()
            self.assertNotIn("setSrcDirs", gradle)
            self.assertNotIn("src/no-tts", gradle)
            self.assertIn("libs.plugins.jetbrains.kotlin.android", gradle)
            self.assertNotIn("dependencies {", gradle)
            self.assertEqual({p.name for p in (module / "src/main/jniLibs/arm64-v8a").glob("*.so")}, {"libsherpa-onnx-jni.so", "libonnxruntime.so"})


if __name__ == "__main__":
    unittest.main()
