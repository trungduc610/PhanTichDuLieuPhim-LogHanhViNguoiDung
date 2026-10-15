import { readFile } from 'node:fs/promises';
const selection = JSON.parse(await readFile(new URL('../data-source.json',import.meta.url),'utf8'));
export const selectedRun = selection.runId;
export const selectedSource = (name = '') => new URL(`../../${selection.evidenceRoot ?? 'evidence/week2-tv2'}/${selectedRun}/dashboard/${name}`,import.meta.url);
export const copiedSource = new URL(`../public/data/${selectedRun}/`,import.meta.url);
