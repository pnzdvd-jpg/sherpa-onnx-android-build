import hashlib
import json
import pathlib
import tempfile
import unittest
from verify import verified_onnx_notices

class OnnxLicenseTests(unittest.TestCase):
    def test_valid_evidence_and_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            binary = root / 'jni/arm64-v8a/libonnxruntime.so'
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b'fixture')
            evidence = root / 'evidence'
            evidence.mkdir()
            hashes = {}
            for name in ('LICENSE', 'ThirdPartyNotices.txt'):
                p = evidence / name
                p.write_text('fixture notice')
                hashes[name] = hashlib.sha256(p.read_bytes()).hexdigest()
            (evidence / 'provenance.json').write_text(json.dumps({'version':'1.28.2','arm64_library_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'notice_sha256':hashes}))
            self.assertEqual(len(verified_onnx_notices(root, evidence)), 3)
            (evidence / 'LICENSE').write_text('modified')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                verified_onnx_notices(root, evidence)
            binary.write_bytes(b'unknown version')
            with self.assertRaisesRegex(ValueError, 'binary does not match'):
                verified_onnx_notices(root, evidence)

if __name__ == '__main__':
    unittest.main()
