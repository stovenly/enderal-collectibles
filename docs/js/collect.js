// Decides which collectibles a parsed save has taken; shared by the page and tools/check-saves.js.
import { SaveError } from './ess.js';

// Keys match the `plugin` fields build_data.py writes into collectibles.json.
const PLUGINS = { skyrim: 'skyrim.esm', fs: 'enderal - forgotten stories.esm' };
const DISABLED = 0x800, DELETED = 0x20;
const PICKED_UP = 0x400;
const DISABLE_ON_TAKE = new Set(['symbol', 'mystic', 'iceclaw']);

export const EDITION_NAMES = { le: 'Enderal (Classic)', se: 'Enderal Special Edition' };

export function formIds(save) {
  const plugins = save.plugins.map(p => p.toLowerCase());
  const index = Object.fromEntries(Object.entries(PLUGINS).map(([k, name]) => [k, plugins.indexOf(name)]));
  if (index.fs < 0) throw new SaveError("This save doesn't use Enderal - Forgotten Stories.esm, so it doesn't look like an Enderal save.");
  return (plugin, local) => ((index[plugin] << 24) | local) >>> 0;
}

async function taken(save, fid, item) {
  if (item.holder) return -(await save.inventoryChange(fid(item.holderPlugin, item.holder), fid(item.itemPlugin, item.item))) >= item.nth;
  const f = await save.refFlags(fid(item.plugin, item.ref));
  if (!f) return false;
  if (DISABLE_ON_TAKE.has(item.kind)) return f.formFlags !== null && (f.formFlags & DISABLED) !== 0;
  return (f.changeFlags & PICKED_UP) !== 0 || (f.formFlags !== null && (f.formFlags & DELETED) !== 0);
}

export async function collected(save, data) {
  const fid = formIds(save);
  const flags = await Promise.all(data.items.map(i => taken(save, fid, i)));
  return new Set(data.items.filter((_, n) => flags[n]).map(i => i.id));
}

// The game's own running totals, keyed by kind; absent where the save never set the global.
export function counters(save, data) {
  const fid = formIds(save);
  const out = {};
  for (const [kind, c] of Object.entries(data.counters)) {
    const v = save.globals.get(fid(c.plugin, c.id));
    if (v != null) out[kind] = Math.round(v);
  }
  return out;
}
