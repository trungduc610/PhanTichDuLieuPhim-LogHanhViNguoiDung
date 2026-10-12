"""Accept Apache SHA512 formats; fail closed if checksum is absent/ambiguous."""
import hashlib
import re
import sys
from pathlib import Path

digests = re.findall(r'(?<![0-9a-fA-F])[0-9a-fA-F]{128}(?![0-9a-fA-F])', Path(sys.argv[2]).read_text())
if len(digests) != 1:
    raise SystemExit('Expected exactly one SHA512 digest from Apache')
h = hashlib.sha512()
with open(sys.argv[1], 'rb') as f:
    for block in iter(lambda: f.read(1024 * 1024), b''):
        h.update(block)
if h.hexdigest().lower() != digests[0].lower():
    raise SystemExit('Archive SHA512 MISMATCH')
print('Apache Flume archive SHA512 verified:', h.hexdigest())
