import struct
import unittest

from verify import check_cache, check_elf, check_symbols


def elf(machine=183, alignment=16384, offset=0, vaddr=0):
    data = bytearray(120)
    data[:6] = b'\x7fELF\x02\x01'
    struct.pack_into('<H', data, 18, machine)
    struct.pack_into('<Q', data, 32, 64)
    struct.pack_into('<HH', data, 54, 56, 1)
    struct.pack_into('<IIQQQQQQ', data, 64, 1, 5, offset, vaddr, 0, 0, 0, alignment)
    return data


class VerificationTests(unittest.TestCase):
    def test_arm64_16k(self):
        self.assertEqual(check_elf(elf()), [16384])

    def test_wrong_abi_rejected(self):
        with self.assertRaises(ValueError):
            check_elf(elf(machine=62))

    def test_4k_rejected(self):
        with self.assertRaises(ValueError):
            check_elf(elf(alignment=4096))

    def test_incongruent_segments_rejected(self):
        with self.assertRaises(ValueError):
            check_elf(elf(offset=100))

    def test_tts_definitions_and_undefined_references_rejected(self):
        for name in ('000 T Java_com_k2fsa_sherpa_onnx_OfflineTts_generate', ' U espeak_Initialize', ' T piper_phonemize'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                check_symbols(name)

    def test_speaker_is_not_espeak(self):
        check_symbols('000 T SpeakerEmbeddingExtractor')

    def test_required_flags(self):
        check_cache('SHERPA_ONNX_ENABLE_TTS:BOOL=OFF\nSHERPA_ONNX_ENABLE_SPEAKER_DIARIZATION:BOOL=OFF\nSHERPA_ONNX_ENABLE_JNI:BOOL=ON\nANDROID_ABI:STRING=arm64-v8a\n')

    def test_missing_or_enabled_tts_rejected(self):
        for text in ('', 'SHERPA_ONNX_ENABLE_TTS:BOOL=ON'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                check_cache(text)


if __name__ == '__main__':
    unittest.main()
