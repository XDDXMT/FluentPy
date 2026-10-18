"""Check the exact release manifest; --upload explicitly publishes to PyPI."""
from __future__ import annotations

import argparse
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import time
import tomllib
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAME = 'fluentpy-qt'
UPLOAD_URL = 'https://upload.pypi.org/legacy/'


def checked_artifacts(directory):
    manifest = json.loads((directory / 'release.json').read_text(encoding='utf-8'))
    if manifest.get('name') != NAME or not manifest.get('files'):
        raise ValueError('Invalid release project or empty manifest')
    artifacts = []
    for filename, digest in manifest['files'].items():
        path = directory / filename
        if Path(filename).name != filename or '/' in filename or '\\' in filename or path.is_symlink():
            raise ValueError('Release filenames must be local ordinary files')
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f'Release changed after preparation: {filename}')
        if filename.endswith('.whl'):
            with zipfile.ZipFile(path) as archive:
                metadata = [n for n in archive.namelist() if n.endswith('.dist-info/METADATA')]
                if len(metadata) != 1:
                    raise ValueError('Expected one wheel metadata file')
                content = archive.read(metadata[0])
        elif filename.endswith('.tar.gz'):
            with tarfile.open(path) as archive:
                metadata = [m for m in archive.getmembers() if len(Path(m.name).parts) == 2 and m.name.endswith('/PKG-INFO')]
                if len(metadata) != 1:
                    raise ValueError('Expected one source metadata file')
                content = archive.extractfile(metadata[0]).read()
        else:
            raise ValueError('Only reviewed wheel and source distributions can be uploaded')
        info = BytesParser().parsebytes(content)
        if info['Name'] != NAME or info['Version'] != manifest['version']:
            raise ValueError(f'Unexpected project or version in {filename}')
        artifacts.append(path)
    return manifest, artifacts


def remote_files(version):
    try:
        request = Request(f'https://pypi.org/pypi/{NAME}/{version}/json',
                          headers={'Cache-Control': 'no-cache', 'User-Agent': 'fluentpy-qt-release-verifier'})
        with urlopen(request, timeout=30) as response:
            data = json.load(response)
    except HTTPError as error:
        if error.code == 404:
            return {}
        raise
    return {item['filename']: item['digests']['sha256'] for item in data['urls']}


def pending_artifacts(manifest, artifacts, published):
    pending = []
    for path in artifacts:
        digest = manifest['files'][path.name]
        if path.name in published and published[path.name] != digest:
            raise ValueError(f'PyPI already contains a different file: {path.name}')
        if path.name not in published:
            pending.append(path)
    return pending


def wait_for_publication(manifest, artifacts, delays=(0, 1, 2, 3, 5, 8, 8)):
    """The public JSON index can lag behind successful upload responses."""
    for delay in delays:
        if delay:
            print(f'Waiting {delay}s for the public PyPI index...', flush=True)
            time.sleep(delay)
        if not pending_artifacts(manifest, artifacts, remote_files(manifest['version'])):
            return True
    return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--upload', action='store_true', help='Publish the reviewed files to the real PyPI')
    mode.add_argument('--verify-published', action='store_true', help='Verify public hashes without uploading or requesting a token')
    args = parser.parse_args(argv)
    version = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    directory = ROOT / 'dist' / 'pypi' / version
    manifest, artifacts = checked_artifacts(directory)
    if manifest['version'] != version:
        raise ValueError('Release manifest does not match the project version')
    print(f"Project: {manifest['name']} {manifest['version']}", flush=True)
    for path in artifacts:
        print(f'  {path.name} ({path.stat().st_size:,} bytes)', flush=True)
    subprocess.run([sys.executable, '-m', 'twine', 'check', '--strict', *map(str, artifacts)], check=True)
    if args.verify_published:
        if not wait_for_publication(manifest, artifacts):
            raise RuntimeError('The public index is not fully synchronized yet. Retry --verify-published; no upload is needed.')
        print(f'Verified on PyPI: https://pypi.org/project/{NAME}/{version}/', flush=True)
        return
    if not args.upload:
        print('Checks passed. Nothing uploaded. Use --upload to publish.', flush=True)
        return
    pending = pending_artifacts(manifest, artifacts, remote_files(version))
    if pending:
        print(f'Destination: {UPLOAD_URL}', flush=True)
        print('Paste your PyPI API token at the hidden token/password prompt. Do not send it in chat.', flush=True)
        env = os.environ.copy()
        for key in ('TWINE_PASSWORD', 'TWINE_USERNAME', 'TWINE_REPOSITORY', 'TWINE_REPOSITORY_URL', 'TWINE_NON_INTERACTIVE'):
            env.pop(key, None)
        env['PYTHON_KEYRING_BACKEND'] = 'keyring.backends.null.Keyring'
        # Do not read or modify the user's .pypirc or save their token.
        staging = ROOT / 'build'
        staging.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='pypi-config-', dir=staging) as temporary:
            config = Path(temporary) / 'empty.ini'
            config.write_text('', encoding='utf-8')
            subprocess.run([sys.executable, '-m', 'twine', 'upload', '--repository-url', UPLOAD_URL,
                '--config-file', str(config), '--username', '__token__', *map(str, pending)], env=env, check=True)
    if not wait_for_publication(manifest, artifacts):
        raise RuntimeError('Upload completed, but the public index is still synchronizing. Retry --verify-published without a token.')
    print(f'Verified on PyPI: https://pypi.org/project/{NAME}/{version}/', flush=True)


if __name__ == '__main__':
    main()
