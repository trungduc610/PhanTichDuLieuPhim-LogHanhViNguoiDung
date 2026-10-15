import { selectedSource, copiedSource } from './selectedSource.js';
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { prepareAnalysis } from '../src/services/overviewAnalysis.js';
import { buildCsv, movieRankingRows, overviewTables } from '../src/services/overviewExport.js';

const source = selectedSource('');
const read = async name => JSON.parse(await readFile(new URL(name, source), 'utf8'));
const actions = await read('stats_action_distribution.json');
const hours = await read('stats_hourly_activity.json');
const movies = await read('stats_top_movies_by_play.json');
const analysis = prepareAnalysis(actions, hours, movies, actions.reduce((sum, row) => sum + row.count, 0));

test('CSV và bảng chỉ chứa đúng 24 giờ, 5 hành động và Top 5 trên Tổng quan', () => {
  const datasets = { hourly: analysis.hourly, actions: analysis.actions, movies: movieRankingRows(analysis.topMovies) };
  const before = JSON.stringify(analysis);
  for (const [kind, rows] of Object.entries(datasets)) {
    const columns = overviewTables[kind].columns;
    const csv = buildCsv(columns, rows);
    assert.equal(csv.charCodeAt(0), 0xfeff);
    const lines = csv.slice(1).trimEnd().split('\r\n');
    assert.equal(lines.length, rows.length + 1);
    // Các giá trị thực tế được giữ nguyên, không làm tròn như nhãn giao diện.
    const decode = line => [...line.matchAll(/"((?:[^"]|"")*)"(?:,|$)/g)].map(match => match[1].replaceAll('""','"'));
    assert.deepEqual(decode(lines[0]), columns.map(column => column.label));
    assert.deepEqual(lines.slice(1).map(decode), rows.map(row => columns.map(column => String(row[column.key]))));
  }
  assert.equal(datasets.hourly.length,24);
  assert.equal(datasets.actions.length,5);
  assert.equal(datasets.movies.length,5);
  assert.deepEqual(datasets.movies.map(row => row.movieId),analysis.topMovies.map(row=>row.movieId));
  assert.equal(JSON.stringify(analysis),before);
});

test('CSV thoát dấu nháy, dấu phẩy, xuống dòng và trung hòa công thức bảng tính', () => {
  const column = [{ key:'title', label:'Tên phim' }];
  assert.equal(buildCsv(column,[{title:'A, "B"\nC'}]), '\uFEFF"Tên phim"\r\n"A, ""B""\nC"\r\n');
  for (const title of ['=1+1','  +1','-1','@SUM(A1)','\t=1']) {
    assert.ok(buildCsv(column,[{title}]).includes(`"'${title}"`));
  }
  assert.ok(buildCsv([{key:'value',label:'Số sự kiện'}],[{value:123}]).includes('"123"'));
});
