// ============================================================
// clean_specs.mjs - one-off spec cleaning pass over src/data/products.js
//
// Policy (user rule): fix only what can be repaired deterministically from the
// extracted text; DROP rows that cannot be repaired. Never invent a value.
//
// The PDF text layer mangled two things systematically:
//   * the degree sign "℃" came out as "I"        -> "0~45I(work)"
//   * words got splinters inserted              -> "MH z", "k bps", "stora ge"
// It also pulled table-header fragments into keys ("Audio: S LC-AAC Bit-rate")
// and produced some label-less keys ("F", "M", "50").
//
// Pipeline: splinter join -> temperature/environment rebuild -> key cleanup ->
//           junk-row drop -> validation re-scan.
// Writes src/data/products.js back in the generated format plus a JSON log.
// Idempotent (a second run changes nothing). DRY_RUN=1 prints without writing.
// Usage: node scripts/clean_specs.mjs
// ============================================================
import { readFileSync, writeFileSync } from 'fs';

const FILE = new URL('../src/data/products.js', import.meta.url).pathname;
const DRY = !!process.env.DRY_RUN;
const text = readFileSync(FILE, 'utf8');
const { PRODUCTS } = await import(FILE + '?v=' + Date.now());

const log = { tempFix: [], tempDrop: [], splinter: [], keyFix: [], rowDrop: [], remaining: [] };

// ---------- A. splinter join (keys and values) ----------
const caseFix = (m, c, rest) => (c === c.toUpperCase() ? c.toUpperCase() + rest : c.toLowerCase() + rest);
const SPLINTERS = [
  [/([Ss])t\s*o?\s*r\s*a?\s*g\s*e\b/g, (m, c) => (c === 'S' ? 'Storage' : 'storage')],
  [/\b([Oo])pera\s*tion\b/g, (m, c, o) => (c === 'O' ? 'Operation' : 'operation')],
  [/\b([Oo])perat\s+ion\b/g, (m, c, o) => (c === 'O' ? 'Operation' : 'operation')],
  [/\b([Ww])ork\s+ing\b/g, (m, c) => (c === 'W' ? 'Working' : 'working')],
  [/\b([Tt])ransmissi\s+on\b/g, (m, c) => (c === 'T' ? 'Transmission' : 'transmission')],
  [/\b([Tt])uner\s+Opti\s+on\b/g, (m, c) => (c === 'T' ? 'Tuner Option' : 'tuner option')],
  [/(?<![A-Za-z])([Mm])\s*s\s*ps\b/g, (m, c) => (c === 'M' ? 'Msps' : 'msps')],
  [/(?<![A-Za-z])([Mm])sp\s+s\b/g, (m, c) => (c === 'M' ? 'Msps' : 'msps')],
  [/\bHDM\s+I\b/g, 'HDMI'],
  [/\bHD\s+MI\b/g, 'HDMI'],
  [/(?<![A-Za-z])([Mm])H\s+z\b/g, (m, c) => (c === 'M' ? 'MHz' : 'mhz')],
  [/(?<![A-Za-z])([KkMmGg])\s+bps\b/g, (m, c) => c + 'bps'],
  [/(?<![A-Za-z])([KkMmGg])\s*sps\b/g, (m, c) => c + 'sps'],
  [/\bf\s+or\b/g, 'for'],
  [/\bca\s+rd\b/g, 'card'],
  [/\bremot\s+e\b/g, 'remote'],
  [/\boutpu\s+t\b/g, 'output'],
  [/\bp\s+er\b/g, 'per'],
  [/\bHardward\b/g, 'Hardware'],
  [/\b8\s*APS\s*K\b/g, '8APSK'],
  [/\b16\s*APS\s*K\b/g, '16APSK'],
  [/\b32\s*APS\s*K\b/g, '32APSK'],
  [/\b8\s*P\s*S?K\b/g, '8PSK'],
  [/\b([0-9]{1,2})\s*AP\s*S\s*K\b/g, '$1APSK'],
  [/\b(\d)\.\s+(\d)/g, '$1.$2'], // "0. 5" -> "0.5"
  [/(?<=[~～])(\d)\s+(\d)/g, '$1$2'], // "0.5~4 5 Msps" -> "0.5~45 Msps"
];
const deSplinter = (s0) => {
  let s = String(s0);
  for (const [re, rep] of SPLINTERS) s = s.replace(re, rep);
  return s.replace(/\s{2,}/g, ' ').trim();
};

// ---------- B. temperature / environment rows ----------
const TEMP_KEY = /environ|temp/i;
const canonicalLabel = (w) => {
  if (/^stor/i.test(w)) return 'storage';
  if (/^operat/i.test(w)) return 'operation';
  if (/^work/i.test(w)) return 'work';
  return null;
};
function rebuildTemp(raw) {
  let s = deSplinter(raw);
  // "-2 0~80" -> "-20~80" (digit split by a space right before the tilde)
  s = s.replace(/(-\s*\d)\s+(\d)(?=\s*[~～])/g, '$1$2');
  // mark the ℃-as-I tokens together with their label
  s = s.replace(/I{1,2}\s*\(?\s*([A-Za-z]+)\s*\)?/g, (m, w) => (canonicalLabel(w) ? `|@${canonicalLabel(w)}|` : m));
  s = s.replace(/\s*I{1,2}\s*/g, ' , '); // leftover bare I's are separators
  s = s.replace(/[;,]/g, ' , ').replace(/(?:\s*,\s*)+/g, ' , ').trim();

  const out = [];
  for (const part of s.split(' , ')) {
    const m = part.match(/(-?\s*\+?\d+(?:\.\d+)?)\s*[~～]\s*(\+?-?\d+(?:\.\d+)?)\s*(?:\|@(\w+)\|)?/);
    if (!m) continue;
    const lo = m[1].replace(/\s+/g, '');
    const hi = m[2].replace(/\s+/g, '');
    out.push(`${lo}~${hi}\u2103${m[3] ? ` (${m[3]})` : ''}`);
  }
  if (!out.length) return null;
  return out.join(', ');
}

// ---------- C. key cleanup ----------
const JUNK_KEYS = new Set(['F', 'M', 'R', 'E', 'S', 'U', 'W', 'T', 'V', 'SD', 'No', 'dB', 'Hz', '30', '50', '80', '100']);
const KEY_RENAMES = new Map([
  ['Input: Input', 'Input'],
  ['Input: Input S E', 'Input'],
  ['Input S E', 'Input'],
  ['Input U S E', 'Input'],
  ['Input: Input U', 'Input'],
  ['DVB-C M', 'DVB-C'],
  ['DVB-S2 M', 'DVB-S2'],
  ['Hoop M', 'Hoop'],
  ['Tuner M', 'Tuner'],
  ['IPTV Storage ServerIOcea nStor S2200T M', 'IPTV Storage Server'],
  ['IPTV ServerI Dell730 M', 'IPTV Server Dell730'],
  ['IPTV ServerI Dell730', 'IPTV Server Dell730'],
]);
function cleanKey(k0) {
  let k = deSplinter(k0);
  k = k.replace(/(?:\s+[A-Z])+$/, ''); // trailing stray letters: "Input S E"
  k = k.replace(/:\s*[A-Z]\s+(?=[A-Z0-9])/g, ': '); // "Audio: S LC-AAC Bit-rate"
  k = k.replace(/^[A-Z]\s+(?=[A-Z0-9])/, ''); // leading stray letter
  k = k.replace(/\s{2,}/g, ' ').replace(/\s*:$/, '').trim();
  for (let i = 0; i < 3; i++) {
    const m = k.match(/^(.+?):\s*(.+)$/);
    if (!m) break;
    const head = m[1].trim();
    const tail = m[2].trim();
    if (tail === head || tail.startsWith(head + ' ') || tail === head.replace(/\s*\w+$/, '')) {
      k = tail === head ? head : tail;
      continue;
    }
    break;
  }
  k = k.replace(/^IPTV Storage Server.*$/, 'IPTV Storage Server');
  if (KEY_RENAMES.has(k)) k = KEY_RENAMES.get(k);
  return k;
}

// ---------- D. run ----------
let before = 0;
let after = 0;
for (const p of PRODUCTS) {
  const next = {};
  for (const [k0, v0] of Object.entries(p.specs || {})) {
    before++;
    const raw = String(v0);

    if (TEMP_KEY.test(k0)) {
      const fixed = rebuildTemp(raw);
      if (fixed) {
        if (fixed !== raw) log.tempFix.push({ slug: p.slug, from: raw, to: fixed });
        next[k0] = fixed;
        after++;
      } else {
        log.tempDrop.push({ slug: p.slug, key: k0, value: raw });
      }
      continue;
    }

    const key = cleanKey(k0);
    if (key !== k0) log.keyFix.push({ slug: p.slug, from: k0, to: key });
    if (JUNK_KEYS.has(key.trim())) {
      log.rowDrop.push({ slug: p.slug, key: k0, value: raw, reason: 'label-less key' });
      continue;
    }
    const val = deSplinter(raw);
    if (val !== raw) log.splinter.push({ slug: p.slug, key, from: raw, to: val });

    // validation: a value that still looks like a mangled temperature row is not trustworthy
    const hasRange = /-?\d+(?:\.\d+)?\s*[~～]\s*-?\+?\d+/.test(val);
    const hasTempLabel = /\(\s*(working|work|storage|operation|operating)\s*\)|\b(storage)\b\s*[;,]|\bI\b/.test(val);
    if (hasRange && hasTempLabel && !/\u2103/.test(val)) {
      log.remaining.push({ slug: p.slug, key, value: val, reason: 'temperature-looking value without a unit' });
      continue;
    }
    if (Object.prototype.hasOwnProperty.call(next, key)) {
      if (next[key] === val) {
        log.rowDrop.push({ slug: p.slug, key: k0, value: raw, reason: 'duplicate of cleaned key with identical value' });
        continue;
      }
      // the cleaned name is taken by a different row: fall back to the original name,
      // and only if THAT is taken too, suffix it - never overwrite a row
      // pre-clean the fallback too (drop stray trailing letters, collapse "X: X") so the
      // kept row still reads properly, then only suffix if that name is taken as well
      let fallback = deSplinter(k0).replace(/(?:\s+[A-Z])+$/, '').replace(/^(.+?):\s*\1$/, '$1').replace(/\s*:$/, '').trim() || k0;
      let n = 2;
      const base = fallback;
      while (Object.prototype.hasOwnProperty.call(next, fallback)) fallback = `${base} (${n++})`;
      log.keyFix.push({ slug: p.slug, from: k0, to: `${fallback}  [cleaned name "${key}" was taken]` });
      next[fallback] = val;
    } else {
      next[key] = val;
    }
    after++;
  }
  p.specs = next;
}

// ---------- E. write ----------
const head = text.split('export const PRODUCTS = [')[0];
const body = PRODUCTS.map((p) => JSON.stringify(p, null, 2).split('\n').map((l) => '  ' + l).join('\n')).join(',\n');
if (DRY) {
  console.log('*** DRY RUN - products.js untouched ***');
  writeFileSync('/opt/data/specs-clean-log-dry.json', JSON.stringify(log, null, 2));
} else {
  writeFileSync(FILE, `${head}export const PRODUCTS = [\n${body},\n];\n`);
  writeFileSync('/opt/data/specs-clean-log.json', JSON.stringify(log, null, 2));
}

const dropped = log.tempDrop.length + log.rowDrop.length + log.remaining.length;
console.log('规格条目: %d -> %d | 删除 %d | 修改 %d', before, after, dropped, log.tempFix.length + log.splinter.length + log.keyFix.length);
console.log('  温度行重建 %d | 温度行无法重建删除 %d | 词内插空格修复 %d | 键名修复 %d | 无标签键删除 %d | 复检不通过删除 %d',
  log.tempFix.length, log.tempDrop.length, log.splinter.length, log.keyFix.length, log.rowDrop.length, log.remaining.length);
if (log.remaining.length) {
  console.log('\n复检不通过（删除）:');
  log.remaining.forEach((d) => console.log('  -', d.slug, '::', d.key, '=', d.value.slice(0, 70)));
}
console.log('\n温度行修复（去重形态）:');
const seen = new Map();
log.tempFix.forEach((d) => seen.set(d.from + ' => ' + d.to, (seen.get(d.from + ' => ' + d.to) || 0) + 1));
[...seen.entries()].sort((a, b) => b[1] - a[1]).forEach(([k, n]) => console.log(`  x${String(n).padStart(3)}  ${k}`));
console.log('\n键名修复（去重）:');
[...new Set(log.keyFix.map((d) => `${d.from}  ->  ${d.to}`))].forEach((k) => console.log('  ' + k));
console.log('\n无标签键删除:');
log.rowDrop.forEach((d) => console.log(`  - ${d.slug} :: ${d.key} = ${String(d.value).slice(0, 60)}`));
