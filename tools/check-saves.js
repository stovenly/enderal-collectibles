// Parses every save in both editions' Saves folders and fails if any kind disagrees with the game's own counter.
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { parseSave } from '../docs/js/ess.js';
import { collected, counters, EDITION_NAMES } from '../docs/js/collect.js';

const GAMES = join(homedir(), 'Documents', 'My Games');
const DIRS = process.argv.length > 2 ? process.argv.slice(2) : ['Enderal', 'Enderal Special Edition'].map(d => join(GAMES, d, 'Saves'));
const data = JSON.parse(readFileSync(new URL('../docs/data/collectibles.json', import.meta.url), 'utf8'));
const kinds = [...new Set(data.items.map(i => i.kind))];

let saves = 0;
for (const dir of DIRS.filter(existsSync)) {
  for (const f of readdirSync(dir).filter(f => f.endsWith('.ess'))) {
    const s = parseSave(new Uint8Array(readFileSync(join(dir, f))));
    const got = await collected(s, data);
    const game = counters(s, data);
    const carried = data.items.filter(i => i.holder && got.has(i.id)).map(i => i.id);
    const line = kinds.map(k => {
      const n = data.items.filter(i => i.kind === k && !i.holder && got.has(i.id)).length;
      return `${k} ${n}/${game[k] ?? '-'}`;
    });
    const bad = kinds.filter(k => game[k] != null && game[k] !== data.items.filter(i => i.kind === k && !i.holder && got.has(i.id)).length);
    console.log(`${EDITION_NAMES[s.header.edition].padEnd(24)} ${f.slice(0, 48).padEnd(48)} L${String(s.header.level).padEnd(3)} ${line.join('  ')}${carried.length ? `  carried: ${carried}` : ''}${bad.length ? `  MISMATCH ${bad}` : ''}`);
    if (bad.length) process.exitCode = 1;
    saves++;
  }
}
console.log(`${saves} saves checked${process.exitCode ? ', with mismatches' : ', all match the game counters'}`);
