"""Strict UTF-8 / CSV validation, separate normalized metadata and QA report."""
import argparse
import csv
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from common import sha256, utcnow, write_json


def prepare(source, output, report):
    source, output = Path(source), Path(output)
    if output.exists():
        raise FileExistsError('Use a new --output; normalized data will not be overwritten')
    counts = Counter()
    rows, seen, issues = [], set(), []
    with source.open(encoding='utf-8', errors='strict', newline='') as f:
        reader = csv.DictReader(f, strict=True)
        if reader.fieldnames != ['movieId', 'title', 'genres']:
            raise ValueError('Unexpected CSV header')
        for line, row in enumerate(reader, 2):
            counts['input_rows'] += 1
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f'Malformed CSV row {line}')
            if any('\ufffd' in v or '\x00' in v for v in row.values()):
                raise ValueError(f'Encoding replacement/NUL character on row {line}')
            try:
                mid = int(row['movieId'])
                assert mid > 0
            except (ValueError, AssertionError):
                raise ValueError(f'Invalid movieId on row {line}')
            if mid in seen:
                counts['duplicate_movie_ids'] += 1
                issues.append({'line': line, 'movieId': mid, 'issue': 'duplicate_movieId'})
            seen.add(mid)
            title = unicodedata.normalize('NFC', row['title'].strip())
            genres = '|'.join(dict.fromkeys(g.strip() for g in row['genres'].split('|') if g.strip()))
            counts['missing_title'] += not bool(title)
            counts['missing_genres'] += not bool(genres)
            counts['no_genres_listed'] += genres == '(no genres listed)'
            match = re.search(r'\((\d{4})\)\s*$', title)
            year = int(match.group(1)) if match else None
            # Fixed, documented range makes cleaning reproducible across dates.
            if year is not None and not 1870 <= year <= 2100:
                year = None
            if year is None:
                counts['missing_or_unparsed_release_year'] += 1
                issues.append({'line': line, 'movieId': mid, 'issue': 'releaseYear_unavailable', 'title': title})
            counts['normalized_rows_changed'] += title != row['title'] or genres != row['genres'] or str(mid) != row['movieId']
            rows.append({'movieId': mid, 'title': title, 'genres': genres, 'releaseYear': year if year is not None else ''})
    stats = {k: counts[k] for k in ['input_rows', 'duplicate_movie_ids', 'missing_title', 'missing_genres', 'no_genres_listed', 'missing_or_unparsed_release_year', 'normalized_rows_changed']}
    stats.update({'source': str(source), 'source_sha256': sha256(source), 'checked_at_utc': utcnow(),
                  'utf8_decode_errors': 0, 'csv_format_errors': 0, 'issues': issues,
                  'related_csv_rows': {}})
    for name in ['ratings', 'tags', 'links']:
        sibling = source.with_name(name + '.csv')
        if sibling.exists():
            with sibling.open(encoding='utf-8', newline='') as f:
                stats['related_csv_rows'][name] = sum(1 for _ in csv.DictReader(f, strict=True))
    if not rows or counts['duplicate_movie_ids'] or counts['missing_title']:
        stats['status'] = 'FAIL'
        write_json(report, stats)
        raise ValueError('Fatal data quality errors; inspect QA report')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['movieId', 'title', 'genres', 'releaseYear'], lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    stats.update({'status': 'PASS', 'output_rows': len(rows), 'output_sha256': sha256(output)})
    write_json(report, stats)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return stats


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', default='data/raw/ml-latest-small/movies.csv')
    p.add_argument('--output', default='data/processed/movies.csv')
    p.add_argument('--report', default='evidence/dataset_quality.json')
    a = p.parse_args()
    prepare(a.source, a.output, a.report)
