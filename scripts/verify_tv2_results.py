"""Independently reconcile small Spark exports and lineage; never fits ML."""
import argparse
import csv
import json
import math
from pathlib import Path
from common import sha256, utcnow
from hdfs_common import ROOT, new_json


def verify(run_id, report):
    folder = ROOT / 'evidence/week2-tv2' / run_id
    load = lambda name: json.loads((folder / name).read_text(encoding='utf-8'))
    status, pipeline, context = load('run_status.json'), load('pipeline_summary.json'), load('run_context.json')
    checks = {'runner_pass': status['status'] == 'PASS', 'pipeline_pass': pipeline['status'] == 'PASS',
              'no_local_fallback': pipeline['local_fallback'] is False,
              'model_reloaded_assignments_match': pipeline['model_reload_assignments_match'] is True,
              'code_hashes_match': all(sha256(ROOT/name) == expected for name,expected in context['code_hashes'].items())}
    manifest = load('output_manifest.json')
    checks['output_read_back_counts'] = all(row['rows'] == row['read_back_rows'] for row in manifest['artifacts'])
    source = load('source_manifest.json')
    source_hash = sha256(folder/'source_manifest.json')
    checks['source_manifest_hash'] = source_hash == context['source_manifest_sha256'] == pipeline['source_manifest_sha256']
    expected = {source['authority']+row['hdfs_path']:(row['bytes'],row['sha256']) for row in source['files']}
    snapshots = [load(name) for name in ['raw-before.json','raw-after.json']]
    checks['raw_unchanged_matches_source'] = all(snapshot['status'] == 'PASS' and
        {row['uri']:(row['bytes'],row['sha256']) for row in snapshot['files']} == expected for snapshot in snapshots)
    data = {};counts = {};csv_ok = True
    for path in sorted((folder/'dashboard').glob('*.json')):
        rows = json.loads(path.read_text(encoding='utf-8'));data[path.stem] = rows;counts[path.stem] = len(rows)
        proof = manifest['dashboard_files'][path.name]
        checks['hash_'+path.name] = sha256(path) == proof['sha256'] and path.stat().st_size == proof['bytes']
        with path.with_suffix('.csv').open(encoding='utf-8',newline='') as stream: other = list(csv.DictReader(stream))
        csv_ok &= len(rows) == len(other)
        for left,right in zip(rows,other):
            for key,value in left.items():
                actual = right[key]
                if isinstance(value,(list,dict)): good = json.loads(actual) == value
                elif isinstance(value,(int,float)) and not isinstance(value,bool): good = math.isclose(float(actual),value,rel_tol=1e-12,abs_tol=1e-8)
                else: good = actual == str(value)
                csv_ok &= good
    checks['local_csv_json_values_and_counts_match'] = csv_ok
    users = data['kmeans_assignments'];features = data['kmeans_user_features']
    actions = {row['action']:row['count'] for row in data['stats_action_distribution']}
    hourly = data['stats_hourly_activity']
    checks['statistics_counts_reconcile'] = sum(actions.values()) == pipeline['clean_events'] == sum(row['eventCount'] for row in hourly) == sum(row['eventCount'] for row in users)
    checks['play_totals_reconcile'] = actions['play'] == sum(row['playCount'] for row in hourly) == sum(row['playCount'] for row in users)
    checks['feature_assignment_users_unique_match'] = len(users) == len(features) == len({row['userId'] for row in users}) == pipeline['user_count']
    feature_map = {row['userId']:row for row in features}
    checks['assignments_preserve_features'] = all({key:value for key,value in row.items() if key != 'cluster'} == feature_map[row['userId']] for row in users)
    total_duration = sum(row['totalWatchDuration'] for row in users)
    checks['watch_duration_reconcile'] = all(math.isclose(row['count']*row['mean'],total_duration,rel_tol=1e-12,abs_tol=1e-5) for row in data['stats_watch_duration_summary'])
    metadata = load('model_metadata.json');search = data['kmeans_k_search']
    best = max(search,key=lambda row:(row['silhouette'],-row['k']))
    checks['best_k_measured_max'] = metadata['best_k'] == best['k'] and metadata['silhouette'] == best['silhouette'] and {row['k'] for row in search} == {2,3,4,5,6}
    checks['no_identifier_features'] = not {'userId','movieId'} & set(metadata['feature_columns'])
    mapping = {'playCount':'avgPlayCount','completeCount':'avgCompleteCount','totalWatchDuration':'avgTotalWatchDuration',
      'avgWatchDuration':'avgWatchDuration','distinctMovies':'avgDistinctMovies','distinctGenres':'avgDistinctGenres',
      'sessionCount':'avgSessionCount','completionRate':'avgCompletionRate','activeDays':'avgActiveDays','eventCount':'avgEventCount'}
    profiles_ok = sizes_ok = True
    for profile in data['kmeans_cluster_profiles']:
        members = [row for row in users if row['cluster'] == profile['cluster']]
        sizes_ok &= len(members) == profile['userCount'] == best['cluster_sizes'][profile['cluster']]
        profiles_ok &= bool(members) and all(math.isclose(sum(row[key] for row in members)/len(members),profile[out],rel_tol=1e-12,abs_tol=1e-8) for key,out in mapping.items())
    checks['assignment_cluster_sizes_match'] = sizes_ok
    checks['all_ten_profile_means_reconcile'] = profiles_ok
    combined = data['stats_user_movie_time']
    checks['seven_analysis_groups_present'] = all('stats_'+name in data for name in ['top_movies_by_play','top_genres','daily_active_users','hourly_activity','action_distribution','watch_duration_summary','user_movie_time'])
    checks['combined_hours_ranks'] = len(combined) == 72 and all(sorted(row['rank'] for row in combined if row['hour'] == hour) == [1,2,3] for hour in range(24))
    checks['daily_counts_in_range'] = all(0 <= row['activeUsers'] <= len(users) for row in data['stats_daily_active_users'])
    result = {'status':'PASS' if all(checks.values()) else 'FAIL','run_id':run_id,'checked_at_utc':utcnow(),
      'checks':checks,'local_csv_json_counts':counts,'raw_files':len(expected),'raw_bytes':sum(row[0] for row in expected.values()),
      'events':pipeline['clean_events'],'users':len(users),'sessions':sum(row['sessionCount'] for row in users),
      'total_watch_seconds':total_duration,'best_k':best['k'],'silhouette':best['silhouette'],'cluster_sizes':best['cluster_sizes'],
      'verifier_sha256':sha256(Path(__file__))}
    new_json(report,result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--report',required=True)
    args = parser.parse_args()
    result = verify(args.run_id,args.report)
    print(json.dumps(result,ensure_ascii=True,indent=2))
    raise SystemExit(0 if result['status'] == 'PASS' else 1)
