"""Read all raw/normalized movie CSV rows without changing the dataset."""
import csv
import re
import unicodedata
from pathlib import Path
from common import sha256


def inspect_movies(path):
    path = Path(path)
    ids, issues, rows = set(), [], 0
    missing_year = no_genres = 0
    with path.open(encoding='utf-8', errors='strict', newline='') as f:
        reader = csv.DictReader(f, strict=True)
        if reader.fieldnames not in [['movieId', 'title', 'genres'], ['movieId', 'title', 'genres', 'releaseYear']]:
            raise ValueError('Unexpected movie CSV header')
        normalized = 'releaseYear' in reader.fieldnames
        for row in reader:
            rows += 1
            location = f'{path}:{reader.line_num}'
            errors = []
            if None in row or any(v is None for v in row.values()):
                errors.append('Malformed CSV field count')
            else:
                try:
                    mid = int(row['movieId'])
                    if not 1 <= mid <= 2**63-1:
                        raise ValueError('movieId outside positive signed long range')
                    if mid in ids:
                        errors.append('duplicate movieId')
                    ids.add(mid)
                except ValueError as exc:
                    errors.append(str(exc))
                for key in ['title', 'genres']:
                    if not row[key].strip():
                        errors.append('missing ' + key)
                    if '\ufffd' in row[key] or '\x00' in row[key]:
                        errors.append('invalid content ' + key)
                no_genres += row['genres'] == '(no genres listed)'
                if normalized:
                    year = row['releaseYear']
                    missing_year += not bool(year)
                    match = re.search(r'\((\d{4})\)\s*$', row['title'])
                    expected = int(match.group(1)) if match and 1870 <= int(match.group(1)) <= 2100 else None
                    try:
                        actual = int(year) if year else None
                        if actual != expected:
                            errors.append('releaseYear does not match documented title rule')
                    except ValueError:
                        errors.append('invalid releaseYear')
                    if row['title'] != unicodedata.normalize('NFC', row['title'].strip()):
                        errors.append('title not normalized')
            if errors:
                issues.append({'location': location, 'movieId': row.get('movieId'), 'errors': errors})
    result = {'path': str(path), 'sha256': sha256(path), 'bytes': path.stat().st_size,
              'rows': rows, 'unique_movie_ids': len(ids), 'error_rows': len(issues),
              'issues_sample': issues[:20], 'releaseYear_null_allowed': missing_year,
              'no_genres_listed': no_genres, 'status': 'PASS' if rows and not issues else 'FAIL'}
    return ids, result
