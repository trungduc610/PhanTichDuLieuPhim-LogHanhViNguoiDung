import { readFile } from 'node:fs/promises';
export const selectedRun = JSON.parse(await readFile(new URL('../data-source.json',import.meta.url),'utf8')).runId;
export const selectedSource = (name = '') => new URL(`../../evidence/week2-tv2/${selectedRun}/dashboard/${name}`,import.meta.url);
export const copiedSource = new URL(`../public/data/${selectedRun}/`,import.meta.url);
