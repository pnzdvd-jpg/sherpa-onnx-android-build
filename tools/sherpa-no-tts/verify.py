"""Fail-closed technical checks. License inventory is evidence, not legal approval."""
import argparse
import hashlib
import io
import json
import pathlib
import re
import shutil
import struct
import subprocess
import zipfile

EXPECTED_LIBS = {'libonnxruntime.so', 'libsherpa-onnx-jni.so'}
FORBIDDEN = re.compile(r'espeak|piper[_-]phonem|offline[_-]tts|OfflineTts', re.I)


def check_elf(data):
    if data[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<H', data, 18)[0] != 183:
        raise ValueError('Expected ELF64 little-endian AArch64')
    offset = struct.unpack_from('<Q', data, 32)[0]
    size, count = struct.unpack_from('<HH', data, 54)
    if size < 56 or offset + size * count > len(data):
        raise ValueError('Invalid ELF program headers')
    loads = []
    for i in range(count):
        kind, flags, file_offset, vaddr, paddr, filesz, memsz, alignment = struct.unpack_from('<IIQQQQQQ', data, offset + i * size)
        if kind == 1:
            if alignment < 16384 or alignment & (alignment - 1) or file_offset % 16384 != vaddr % 16384:
                raise ValueError('PT_LOAD is not compatible with 16 KB pages')
            loads.append(alignment)
    if not loads:
        raise ValueError('Missing PT_LOAD')
    return loads


def check_symbols(symbols):
    if FORBIDDEN.search(symbols):
        raise ValueError('TTS/eSpeak/Piper symbol found')


def check_cache(cache):
    required = {'SHERPA_ONNX_ENABLE_TTS': 'OFF', 'SHERPA_ONNX_ENABLE_SPEAKER_DIARIZATION': 'OFF',
                'SHERPA_ONNX_ENABLE_JNI': 'ON', 'ANDROID_ABI': 'arm64-v8a'}
    for name, value in required.items():
        if not re.search(r'^' + name + r':[^=]+=' + value + r'$', cache, re.M):
            raise ValueError(f'Missing build setting: {name}={value}')


def main(work, llvm):
    result = work / 'result'
    aar = result / 'sherpa-onnx-1.13.8-no-tts-arm64.aar'
    check_cache((work / 'native/CMakeCache.txt').read_text())
    commands = json.loads((work / 'native/compile_commands.json').read_text())
    files = sorted({x['file'] for x in commands})
    for name in files:
        if FORBIDDEN.search(name):
            raise ValueError(f'Forbidden compilation unit: {name}')
    if not any(name.endswith('/keyword-spotter.cc') for name in files):
        raise ValueError('KWS compilation unit absent')
    (result / 'compiled-sources.json').write_text(json.dumps(files, indent=2) + '\n')
    report = {'technical_checks_passed': False, 'license_review_required': True, 'libraries': {}}
    with zipfile.ZipFile(aar) as archive:
        names = [n for n in archive.namelist() if n.endswith('.so')]
        expected = {'jni/arm64-v8a/' + n for n in EXPECTED_LIBS}
        if set(names) != expected or len(names) != len(expected):
            raise ValueError(f'Unexpected native libraries/ABIs: {names}')
        with zipfile.ZipFile(io.BytesIO(archive.read('classes.jar'))) as classes:
            cls = classes.namelist()
            if 'com/k2fsa/sherpa/onnx/KeywordSpotter.class' not in cls:
                raise ValueError('Kotlin KWS API missing')
            if any('OfflineTts' in n or '/TtsKt' in n for n in cls):
                raise ValueError('TTS Kotlin bindings still packaged')
        for name in names:
            data = archive.read(name)
            alignments = check_elf(data)
            binary = result / pathlib.Path(name).name
            binary.write_bytes(data)
            symbols = subprocess.check_output([str(llvm / 'llvm-nm'), '--demangle', '--dynamic', str(binary)], text=True)
            check_symbols(symbols)
            if binary.name == 'libsherpa-onnx-jni.so':
                for method in ('newFromAsset', 'createStream', 'decode', 'getResult', 'reset'):
                    pattern = r'\b[TW]\s+Java_com_k2fsa_sherpa_onnx_KeywordSpotter_' + method + r'\b'
                    if not re.search(pattern, symbols):
                        raise ValueError(f'KWS JNI export missing: {method}')
                # Hidden symbols may be stripped: additionally inspect literal diagnostics.
                if re.search(rb'espeak-ng|piper[_-]phonemize', data, re.I):
                    raise ValueError('Residual eSpeak/Piper binary content requires review')
            dynamic = subprocess.check_output([str(llvm / 'llvm-readelf'), '-d', str(binary)], text=True)
            needed = re.findall(r'\(NEEDED\).*?\[(.*?)\]', dynamic)
            allowed = EXPECTED_LIBS | {'libc.so', 'libm.so', 'libdl.so', 'liblog.so', 'libandroid.so', 'libz.so'}
            if set(needed) - allowed:
                raise ValueError(f'Undeclared native dependencies: {needed}')
            (result / (binary.name + '.symbols.txt')).write_text(symbols)
            (result / (binary.name + '.dynamic.txt')).write_text(dynamic)
            report['libraries'][binary.name] = {'sha256': hashlib.sha256(data).hexdigest(), 'load_alignments': alignments, 'needed': needed}

    # Inventory the actual downloaded dependency sources, not an assumed license list.
    roots = sorted((work / 'native/_deps').glob('*-src'))
    if not roots:
        raise ValueError('Dependency sources unavailable: cannot inventory licenses')
    license_inventory = []
    license_root = result / 'licenses'
    for root in roots:
        if FORBIDDEN.search(root.name):
            raise ValueError(f'Unexpected dependency: {root.name}')
        notices = [p for p in root.rglob('*') if p.is_file() and re.match(r'^(LICENSE|LICENCE|COPYING|NOTICE|COPYRIGHT|ThirdPartyNotices)([._-]|$)', p.name, re.I)]
        if not notices:
            raise ValueError(f'No license evidence for {root.name}; manual resolution required')
        for p in notices:
            dest = license_root / root.name / p.relative_to(root)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, dest)
        license_inventory.append({'dependency': root.name, 'notice_files': [str(p.relative_to(root)) for p in notices]})
    ndk = llvm.parents[4]
    ndk_notices = list(ndk.glob('NOTICE*'))
    if not ndk_notices:
        raise ValueError('NDK/libc++ notices unavailable')
    for p in ndk_notices:
        if p.is_file():
            dest = license_root / 'android-ndk' / p.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, dest)
    (result / 'license-inventory.json').write_text(json.dumps(license_inventory, indent=2) + '\n')
    report['technical_checks_passed'] = True
    (result / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    hashes = {str(p.relative_to(result)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(result.rglob('*')) if p.is_file() and p.name != 'SHA256SUMS.json'}
    (result / 'SHA256SUMS.json').write_text(json.dumps(hashes, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('work', type=pathlib.Path)
    parser.add_argument('--llvm-bin', required=True, type=pathlib.Path)
    args = parser.parse_args()
    main(args.work.resolve(), args.llvm_bin.resolve())
