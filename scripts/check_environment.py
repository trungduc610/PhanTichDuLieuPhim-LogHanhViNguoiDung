"""Record actual environment and tool exit codes without installing software."""
import json
import platform
import shutil
import subprocess
import sys
from common import utcnow, write_json

result = {'checked_at_utc': utcnow(), 'os': platform.platform(), 'python': sys.version,
          'python_executable': sys.executable, 'tools': {}}
for args in [['java', '-version'], ['docker', 'version'], ['docker', 'compose', 'version'], ['wsl', '--status'], ['git', '--version']]:
    key = ' '.join(args)
    if not shutil.which(args[0]):
        result['tools'][key] = {'available': False, 'reason': 'not found in PATH'}
        continue
    try:
        proc = subprocess.run(args, capture_output=True, timeout=20)
        content = proc.stdout + proc.stderr
        encoding = 'utf-16-le' if b'\x00' in content else 'utf-8'
        result['tools'][key] = {'available': proc.returncode == 0, 'exit_code': proc.returncode,
                               'output': content.decode(encoding, errors='replace')}
    except Exception as exc:
        result['tools'][key] = {'available': False, 'reason': str(exc)}
write_json('evidence/environment.json', result)
print(json.dumps(result, ensure_ascii=False, indent=2))
