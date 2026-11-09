#!/usr/bin/env python3
"""Generate casks only after verifying the published macOS artifacts. Requires macOS."""
import argparse
import hashlib
import json
import plistlib
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.request import urlopen

REPOSITORY = "mycelium-build/datalith-app"
ROOT = Path(__file__).resolve().parents[1]
TAG = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-rc\.(0|[1-9][0-9]*))?")
TEAM = "RJF38225T9"


def version_key(tag):
    match = TAG.fullmatch(tag)
    if not match:
        raise ValueError(f"Invalid release tag: {tag}")
    return tuple(int(n) if n is not None else -1 for n in match.groups())


def channel_of(tag):
    return "preview" if version_key(tag)[3] >= 0 else "stable"


def latest(releases, channel):
    candidates = [r for r in releases if TAG.fullmatch(r['tag_name'])
                  and not r['draft'] and channel_of(r['tag_name']) == channel
                  and r['prerelease'] == (channel == 'preview')]
    if not candidates:
        raise ValueError(f"No published {channel} release")
    return max(candidates, key=lambda r: version_key(r['tag_name']))


def assets_for(release):
    tag = release['tag_name']
    stem = 'Datalith.Preview' if channel_of(tag) == 'preview' else 'Datalith'
    result = {}
    for arch in ('aarch64', 'x64'):
        name = f"{stem}_{tag[1:]}_{arch}.dmg"
        matches = [a for a in release['assets'] if a['name'] == name]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one {name}")
        asset = matches[0]
        expected = f"https://github.com/{REPOSITORY}/releases/download/{tag}/{name}"
        if asset['browser_download_url'] != expected:
            raise ValueError(f"Unexpected download URL: {asset['browser_download_url']}")
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', asset.get('digest') or ''):
            raise ValueError(f"Missing GitHub SHA-256 for {name}")
        result[arch] = asset
    return result


def run(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT).strip()


def verify_dmg(path, version, channel, arch):
    product = 'Datalith Preview' if channel == 'preview' else 'Datalith'
    identifier = 'build.mycelium.datalith' + ('-preview' if channel == 'preview' else '')
    run('codesign', '--verify', '--strict', str(path))
    run('xcrun', 'stapler', 'validate', str(path))
    run('spctl', '--assess', '--type', 'open', '--context', 'context:primary-signature', str(path))
    with tempfile.TemporaryDirectory(prefix='datalith-mount-') as directory:
        # Older published DMGs include a license prompt.
        subprocess.run(['hdiutil', 'attach', '-readonly', '-nobrowse', '-mountpoint', directory, str(path)],
                       input='Y\n', text=True, check=True, stdout=subprocess.DEVNULL)
        try:
            mount = Path(directory)
            apps = list(mount.glob('*.app'))
            if [app.name for app in apps] != [product + '.app']:
                raise ValueError(f"Unexpected app bundles: {apps}")
            app = apps[0]
            info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
            if info['CFBundleIdentifier'] != identifier or info['CFBundleShortVersionString'] != version:
                raise ValueError(f"Bundle identity/version mismatch: {info}")
            run('codesign', '--verify', '--deep', '--strict', str(app))
            signature = run('codesign', '-dv', '--verbose=4', str(app))
            if f'TeamIdentifier={TEAM}' not in signature or 'runtime' not in signature:
                raise ValueError('Unexpected signing team or missing hardened runtime')
            run('xcrun', 'stapler', 'validate', str(app))
            run('spctl', '--assess', '--type', 'execute', str(app))
            binary = app / 'Contents/MacOS' / info['CFBundleExecutable']
            expected_arch = 'arm64' if arch == 'aarch64' else 'x86_64'
            if run('lipo', '-archs', str(binary)) != expected_arch:
                raise ValueError('Unexpected executable architecture')
            commands = run('otool', '-l', str(binary))
            minimum = re.search(r'\bminos (\d+(?:\.\d+)+)', commands)
            if not minimum:
                minimum = re.search(r'cmd LC_VERSION_MIN_MACOSX\s+cmdsize \d+\s+version (\d+(?:\.\d+)+)', commands)
            if not minimum:
                raise ValueError('Cannot determine minimum macOS version')
            print(json.dumps({'asset': path.name, 'identifier': identifier, 'version': version,
                              'build': info['CFBundleVersion'], 'arch': expected_arch,
                              'minimum_macos': minimum[1], 'team': TEAM}), flush=True)
            return minimum[1]
        finally:
            subprocess.run(['hdiutil', 'detach', directory], check=True, stdout=subprocess.DEVNULL)


def render(version, channel, hashes):
    preview = channel == 'preview'
    token = 'datalith@preview' if preview else 'datalith'
    product = 'Datalith Preview' if preview else 'Datalith'
    stem = product.replace(' ', '.')
    identifier = 'build.mycelium.datalith' + ('-preview' if preview else '')
    return f'''cask "{token}" do
  arch arm: "aarch64", intel: "x64"

  version "{version}"
  sha256 arm:   "{hashes['aarch64']}",
         intel: "{hashes['x64']}"

  url "https://github.com/{REPOSITORY}/releases/download/v#{{version}}/{stem}_#{{version}}_#{{arch}}.dmg"
  name "{product}"
  desc "Local-first knowledge workspace"
  homepage "https://datalith.work/"

  livecheck do
    url "https://updates.datalith.work/{channel}"
    strategy :json do |json|
      json["version"] if json["version"] != "0.0.0"
    end
  end

  auto_updates true
  depends_on :macos

  app "{product}.app"

  uninstall quit: "{identifier}"
end
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', help='Release notification; refresh the highest published version in its channel')
    parser.add_argument('--cache', type=Path, default=Path(tempfile.gettempdir()) / 'datalith-homebrew-validation')
    args = parser.parse_args()
    channels = [channel_of(args.tag)] if args.tag else ['stable', 'preview']
    pages = json.loads(run('gh', 'api', '--paginate', '--slurp', f'repos/{REPOSITORY}/releases?per_page=100'))
    releases = [release for page in pages for release in page]
    if args.tag and not any(r['tag_name'] == args.tag and not r['draft']
                            and r['prerelease'] == (channels[0] == 'preview') for r in releases):
        raise ValueError('Notification must refer to a published release with matching channel')
    args.cache.mkdir(parents=True, exist_ok=True)
    pending = {}
    for channel in channels:
        release = latest(releases, channel)
        version = release['tag_name'][1:]
        destination = ROOT / 'Casks' / ('datalith@preview.rb' if channel == 'preview' else 'datalith.rb')
        if destination.exists():
            old = re.search(r'^  version "([^"]+)"', destination.read_text(), re.M)
            if old and version_key('v' + old[1]) > version_key(release['tag_name']):
                raise ValueError('Refusing to downgrade a cask; review removed releases manually')
        hashes = {}
        for arch, asset in assets_for(release).items():
            path = args.cache / asset['name']
            if not path.exists():
                with urlopen(asset['browser_download_url'], timeout=120) as response:
                    data = response.read()
                path.write_bytes(data)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if path.stat().st_size != asset['size'] or 'sha256:' + digest != asset['digest']:
                raise ValueError(f"Checksum/size mismatch for {path}; remove cached file before retrying")
            hashes[arch] = digest
            verify_dmg(path, version, channel, arch)
        pending[destination] = render(version, channel, hashes)
    # No cask changes until every requested artifact passes all checks.
    for destination, content in pending.items():
        destination.write_text(content)
        print(f'Updated {destination.name}', flush=True)


if __name__ == '__main__':
    main()
