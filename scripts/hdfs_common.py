"""Week 2 evidence helpers: exclusive reports and exact subprocess records."""
import json
import os
import subprocess
import uuid
from pathlib import Path
from common import utcnow

ROOT = Path(__file__).resolve().parents[1]

def new_json(path, value):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(value,f,ensure_ascii=False,indent=2)
        f.write('\n')

class Ledger:
    def __init__(self,evidence,env=None):
        self.folder=Path(evidence)/'commands'
        self.folder.mkdir(parents=True,exist_ok=True)
        self.env=os.environ.copy()
        self.env.update(env or {})
        self.env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')

    def start(self,argv,label):
        folder=self.folder/(label+'-'+uuid.uuid4().hex[:8])
        folder.mkdir()
        record={'argv':argv,'cwd':str(ROOT),'started_at_utc':utcnow(),
            'environment':{key:self.env.get(key) for key in ['HDFS_RUN_ID','HDFS_HADOOP_IMAGE','HADOOP_USER_NAME','DOCKER_CONTEXT']},
            'stdout':str(folder/'stdout.txt'),'stderr':str(folder/'stderr.txt')}
        new_json(folder/'started.json',record)
        return folder,record

    def command(self,argv,label,check=True):
        folder,record=self.start(argv,label)
        with (folder/'stdout.txt').open('xb') as out,(folder/'stderr.txt').open('xb') as err:
            result=subprocess.run(argv,cwd=ROOT,env=self.env,stdout=out,stderr=err)
        record.update(exit_code=result.returncode,finished_at_utc=utcnow())
        new_json(folder/'finished.json',record)
        if check and result.returncode:
            raise RuntimeError(f'{label} exit {result.returncode}; see {folder}')
        return result.returncode,(folder/'stdout.txt').read_text(encoding='utf-8',errors='replace'),folder

def compose(project):
    return ['docker','compose','-f','compose.hdfs.yaml','-p',project]


def snapshot_namespaces(source):
    """Scope checks to the selected raw snapshot, including old source manifests."""
    from urllib.parse import urlsplit
    from pathlib import PurePosixPath
    if source['status'] != 'PASS' or source['authority'] != 'hdfs://namenode:9000':
        raise ValueError('Requires a PASS HDFS source manifest')
    paths = []
    for key in ['movies_uri', 'logs_uri']:
        parsed = urlsplit(source[key])
        if parsed.scheme != 'hdfs' or parsed.netloc != 'namenode:9000' or parsed.query or parsed.fragment:
            raise ValueError('Requires actual HDFS URIs')
        if '..' in PurePosixPath(parsed.path).parts or str(PurePosixPath(parsed.path)) != parsed.path:
            raise ValueError('Invalid snapshot path')
        paths.append(parsed.path)
    movies, logs = paths
    movie_root = str(PurePosixPath(movies).parent)
    if not movies.endswith('/movies.csv') or not movie_root.startswith('/movie-log/raw/movies/'):
        raise ValueError('Invalid movies snapshot namespace')
    if logs != '/movie-log/raw/user_logs/' + source['flume_run_id'] + '/' + source['hdfs_run_id']:
        raise ValueError('Logs URI does not match the selected run IDs')
    roots = [movie_root, logs]
    if 'raw_namespaces' in source and source['raw_namespaces'] != roots:
        raise ValueError('Manifest namespace declarations disagree')
    destinations = []
    for item in source['files']:
        if item['kind'] not in ['movies', 'logs']:
            raise ValueError('Unknown source file kind')
        parent = movie_root if item['kind'] == 'movies' else logs
        path = item['hdfs_path']
        if not path.startswith(parent + '/') or '..' in PurePosixPath(path).parts or str(PurePosixPath(path)) != path:
            raise ValueError('Source destination is outside its raw snapshot')
        destinations.append(path)
    if len(set(destinations)) != len(destinations) or movies not in destinations:
        raise ValueError('Duplicate destinations or missing movie file')
    return roots


def snapshot_file_diff(source, listed):
    roots = snapshot_namespaces(source)
    expected = {item['hdfs_path'] for item in source['files']}
    actual = {path for path in listed if any(path.startswith(parent + '/') for parent in roots)}
    return sorted(expected - actual), sorted(actual - expected)
