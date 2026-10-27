#!/usr/bin/env python3
"""Build a personal UI fork using the matching signed Zen release's Gecko binaries.

No C++/Rust engine rebuild is necessary for these JavaScript/CSS changes.
The full upstream source checkout and native UI build registration are retained.
"""
from pathlib import Path
import argparse, configparser, json, plistlib, shutil, struct, subprocess, tempfile, zipfile, zlib

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--base', type=Path, default=Path('/Applications/Zen.app'))
parser.add_argument('--output', type=Path, default=Path.home()/'Applications/Zen Custom.app')
args = parser.parse_args()
base, output = args.base.resolve(), args.output.resolve()
assert base != output, 'The custom app must have its own path'
assert (base/'Contents/MacOS/zen').is_file(), 'Zen base app missing'
release = configparser.ConfigParser()
release.read(base/'Contents/Resources/application.ini')

def run(command, **kwargs):
    return subprocess.run([str(x) for x in command], check=True, **kwargs)

def unpack_omnijar(archive, destination):
    # Mozilla's optimized ZIP stores its central directory at byte 4 instead of
    # the end. Read the directory's explicit offsets; validate every entry's CRC.
    data = archive.read_bytes()
    position = data.find(zipfile.stringCentralDir)
    assert position >= 0, 'Missing ZIP central directory'
    count = 0
    while data[position:position + 4] == zipfile.stringCentralDir:
        fields = struct.unpack(zipfile.structCentralDir, data[position:position + zipfile.sizeCentralDir])
        start = position + zipfile.sizeCentralDir
        name_length = fields[zipfile._CD_FILENAME_LENGTH]
        name = data[start:start + name_length].decode('utf-8')
        position = start + name_length + fields[zipfile._CD_EXTRA_FIELD_LENGTH] + fields[zipfile._CD_COMMENT_LENGTH]
        output_file = destination/name
        assert output_file.resolve().is_relative_to(destination.resolve()), 'Unsafe archive path'
        offset = fields[zipfile._CD_LOCAL_HEADER_OFFSET]
        assert data[offset:offset + 4] == zipfile.stringFileHeader
        header = struct.unpack(zipfile.structFileHeader, data[offset:offset + zipfile.sizeFileHeader])
        offset += zipfile.sizeFileHeader + header[zipfile._FH_FILENAME_LENGTH] + header[zipfile._FH_EXTRA_FIELD_LENGTH]
        raw = data[offset:offset + fields[zipfile._CD_COMPRESSED_SIZE]]
        compression = fields[zipfile._CD_COMPRESS_TYPE]
        assert compression in (0, 8), f'Unsupported compression {compression}'
        payload = raw if compression == 0 else zlib.decompress(raw, -15)
        assert len(payload) == fields[zipfile._CD_UNCOMPRESSED_SIZE]
        assert zlib.crc32(payload) == fields[zipfile._CD_CRC], f'Bad CRC: {name}'
        if name.endswith('/'):
            output_file.mkdir(parents=True, exist_ok=True)
        else:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_bytes(payload)
        count += 1
    assert count > 100, 'Unexpectedly incomplete Zen archive'
    print(f'Validated {count} browser resources', flush=True)

with tempfile.TemporaryDirectory(prefix='zen-custom-build-') as scratch:
    scratch = Path(scratch)
    app = scratch/'Zen Custom.app'
    run(['ditto', base, app])
    resources = app/'Contents/Resources'
    archive = resources/'browser/omni.ja'
    unpacked = scratch/'browser'
    unpacked.mkdir()
    unpack_omnijar(archive, unpacked)
    content = unpacked/'chrome/browser/content/browser'
    assert (content/'ZenPreloadedScripts.js').is_file(), 'Zen resource layout changed'
    feature = ROOT/'src/zen/custom'
    shutil.copytree(feature, content/'zen-custom')
    preload = content/'ZenPreloadedScripts.js'
    original = preload.read_text()
    # Patch the installed release's loader, preserving all other upstream changes.
    addition = (ROOT/'src/zen/common/ZenPreloadedScripts.js').read_text().split('// Personal features')[1]
    preload.write_text(original + '\n// Personal features' + addition)
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for file in sorted(unpacked.rglob('*')):
            if file.is_file(): z.write(file, file.relative_to(unpacked))
    with zipfile.ZipFile(archive) as z: assert z.testzip() is None
    info_path = app/'Contents/Info.plist'
    info = plistlib.loads(info_path.read_bytes())
    version = info['CFBundleShortVersionString']
    info.update(CFBundleName='Zen Custom', CFBundleDisplayName='Zen Custom',
        CFBundleIdentifier='local.isaac.zen-custom', CFBundleExecutable='zen-custom',
        CFBundleGetInfoString=f'Zen Custom 0.1 — based on Zen {version}')
    info_path.write_bytes(plistlib.dumps(info))
    macos = app/'Contents/MacOS'
    for source, binary in [('Launcher.swift', 'zen-custom'), ('Hotkeys.swift', 'ZenCustomHotkeys')]:
        run(['xcrun', 'swiftc', '-swift-version', '5', '-O', ROOT/'custom/macos'/source, '-o', macos/binary])
    # Stock updates would replace this fork. Rebuild from an updated base app.
    distribution = resources/'distribution'
    distribution.mkdir(exist_ok=True)
    (distribution/'policies.json').write_text(json.dumps({'policies': {'DisableAppUpdate': True}}))
    (resources/'ZenCustomVersion.json').write_text(json.dumps({
        'custom_version': '0.1', 'zen_version': version,
        'upstream_source': release['App']['SourceStamp'],
        'custom_source': run(['git', '-C', ROOT, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip(),
        'little_zen_source': 'https://github.com/wahyuabrory/little-zen/tree/f1ed4b1109ae7ac8fac58b3dec6652a4bee556da',
        'build_method': 'UI source overlay on upstream Gecko binaries'
    }, indent=2))
    shutil.copy(ROOT/'LICENSE', resources/'ZenCustom-MPL-2.0.txt')
    entitlements = scratch/'entitlements.plist'
    entitlements.write_bytes(plistlib.dumps({'com.apple.security.cs.allow-jit': True,
        'com.apple.security.cs.disable-library-validation': True,
        'com.apple.security.device.audio-input': True,
        'com.apple.security.device.camera': True}))
    for attribute in ['com.apple.FinderInfo', 'com.apple.ResourceFork']:
        subprocess.run(['xattr', '-dr', attribute, str(app)], capture_output=True)
    run(['codesign', '--force', '--sign', '-', macos/'ZenCustomHotkeys'])
    run(['codesign', '--force', '--sign', '-', '--options', 'runtime', '--entitlements', entitlements, macos/'zen'])
    run(['codesign', '--force', '--sign', '-', '--options', 'runtime', '--entitlements', entitlements, app])
    run(['codesign', '--verify', '--deep', '--strict', app])
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        # Only replace artifacts created by this builder, never an unrelated app.
        assert (output/'Contents/Resources/ZenCustomVersion.json').exists(), 'Unrecognized output app'
        previous = output.with_name('Zen Custom.previous.app')
        if previous.exists():
            assert (previous/'Contents/Resources/ZenCustomVersion.json').exists()
            shutil.rmtree(previous)
        output.rename(previous)
    shutil.move(str(app), str(output))
    print(f'Built {output} from Zen {version}')
