"""Download immutable local snapshot; preserve source ZIP and license README."""
import argparse
import json
import shutil
import ssl
import urllib.request
import zipfile
from pathlib import Path
from common import sha256, utcnow, write_json

URL = 'https://files.grouplens.org/datasets/movielens/ml-latest-small.zip'


def download(raw, ca_file=None):
    raw = Path(raw)
    raw.mkdir(parents=True, exist_ok=True)
    archive = raw / 'ml-latest-small.zip'
    manifest = raw / 'download_manifest.json'
    if manifest.exists():
        saved = json.loads(manifest.read_text(encoding='utf-8'))
        if not archive.exists() or sha256(archive) != saved['sha256']:
            raise ValueError('Existing snapshot checksum mismatch; use a NEW raw directory')
        for name, digest in saved['files_sha256'].items():
            if sha256(raw / name) != digest:
                raise ValueError('Raw file modified: ' + name)
        print(json.dumps(saved, ensure_ascii=False, indent=2))
        return saved
    if archive.exists() or (raw / 'ml-latest-small').exists():
        raise FileExistsError('Incomplete/untracked raw snapshot; choose a new --raw directory')
    part = raw / 'download.zip.part'
    if part.exists():
        raise FileExistsError(part)
    context = ssl.create_default_context(cafile=ca_file)
    with urllib.request.urlopen(URL, context=context, timeout=120) as response, part.open('xb') as out:
        shutil.copyfileobj(response, out)
    with zipfile.ZipFile(part) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP CRC check failed')
        expected = {f'ml-latest-small/{x}' for x in ['README.txt', 'movies.csv', 'ratings.csv', 'tags.csv', 'links.csv']}
        if not expected.issubset(z.namelist()):
            raise ValueError('Unexpected ZIP contents')
        # Extract ONLY explicit files: never trust archive path traversal.
        for name in sorted(expected):
            target = raw / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(name) as source, target.open('xb') as out:
                shutil.copyfileobj(source, out)
    part.rename(archive)
    result = {'dataset': 'MovieLens latest-small', 'source_url': 'https://grouplens.org/datasets/movielens/latest/',
              'download_url': URL, 'downloaded_at_utc': utcnow(), 'tls_verified': True,
              'sha256': sha256(archive), 'archive_bytes': archive.stat().st_size,
              'license_file': 'ml-latest-small/README.txt',
              'files_sha256': {n: sha256(raw / n) for n in sorted(expected)}}
    write_json(manifest, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw', default='data/raw')
    p.add_argument('--ca-file', help='Optional trusted PEM CA bundle; TLS verification stays enabled')
    a = p.parse_args()
    download(a.raw, a.ca_file)
