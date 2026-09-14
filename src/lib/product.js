// ============================================================
// lib/product.js - shared derivations over products.js
// Used by the catalogue index (/products/), the product detail template and the homepage finder.
// Everything here is computed from the imported data at build time; nothing is hard-coded.
// ============================================================

export const short = (s, n) => String(s || '').replace(/\s+/g, ' ').trim().slice(0, n);

// ---------- images (three tiers) ----------
export const thumbOf = (img) => (img || '').replace(/\.(jpg|jpeg|png)$/i, '-thumb.webp');
export const medOf = (img) => (img || '').replace(/\.(jpg|jpeg|png)$/i, '-med.webp');

// ---------- model number ----------
// "FUQ4339KN V2 Network Encoder 48 HDMI" -> FUQ4339KN
export const modelOf = (p) => {
  const parts = String(p.name || '').trim().split(/\s+/);
  const first = parts[0] || '';
  const second = parts[1] || '';
  const m = first.length >= 3 ? first : `${first} ${second}`.trim();
  return m.replace(/[,;]$/, '');
};

// model family used for "more from this range" (FUQ4339KN -> FUQ4)
export const familyOf = (model) => String(model || '').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 4);

// ---------- card-face spec teasers ----------
const SPEC_PRIORITY = ['input', 'output', 'channel', 'capacity', 'resolution', 'frequency', 'standard', 'interface', 'format', 'rate', 'modulation', 'encoding'];

export const teasersOf = (p, limit = 2) =>
  Object.entries(p.specs || {})
    .filter(([k, v]) => v && String(k).length <= 28 && String(v).length <= 58)
    .map(([k, v]) => {
      const lk = k.toLowerCase();
      const rank = SPEC_PRIORITY.findIndex((s) => lk.includes(s));
      return { k: short(k.replace(/\s*[:]\s*$/, ''), 20), v: short(v, 34), rank: rank === -1 ? 99 : rank };
    })
    .sort((a, b) => a.rank - b.rank)
    .slice(0, limit);

// ---------- hero highlights: the specs buyers scan first ----------
const KEY_SPEC_RULES = [
  { re: /^Resolution$/i, score: 100 },
  { re: /Encoding|Video.*Format/i, score: 90, exclude: /^Audio/ },
  { re: /^Bit[- ]?rate/i, score: 85 },
  { re: /^Input/i, score: 80 },
  { re: /^Output/i, score: 80 },
  { re: /^Modulation|Constellation/i, score: 75 },
  { re: /^Channels?$/i, score: 70 },
  { re: /^Interface/i, score: 60 },
  { re: /^Power/i, score: 55 },
  { re: /^Audio:/i, score: 40 },
  { re: /^Standard$/i, score: 35 },
];

export const specScore = (k) => {
  let best = 0;
  for (const rule of KEY_SPEC_RULES) {
    if (rule.exclude && rule.exclude.test(k)) continue;
    if (rule.re.test(k)) best = Math.max(best, rule.score);
  }
  return best;
};

export const highlightsOf = (p, limit = 4) =>
  Object.entries(p.specs || {})
    .filter(([k, v]) => v && String(v).trim() && specScore(k) > 0)
    .sort((a, b) => specScore(b[0]) - specScore(a[0]))
    .slice(0, limit)
    .map(([k, v]) => {
      let val = String(v).split(',')[0].split(';')[0].trim();
      if (val.length > 30) val = val.slice(0, 29) + '…';
      const isAudio = /^Audio:/i.test(k);
      return { key: isAudio ? 'Audio ' + k.replace(/^Audio:\s*/i, '') : k, value: val };
    });

// ---------- per-model FAQ, generated only from specs that really exist ----------
export const faqFor = (p) => {
  const model = modelOf(p);
  const entries = Object.entries(p.specs || {}).filter(([k, v]) => v && String(v).trim());
  const pick = (re, exclude) => entries.find(([k, v]) => re.test(k) && (!exclude || !exclude.test(k)));
  const qas = [];
  const inputs = pick(/^Inputs?$|^Input/i);
  if (inputs) qas.push({ q: `What inputs does the ${model} accept?`, a: `${inputs[0]}: ${inputs[1]}` });
  const outputs = pick(/^Outputs?$|^Output/i);
  if (outputs) qas.push({ q: `What are the outputs of the ${model}?`, a: `${outputs[0]}: ${outputs[1]}` });
  const res = pick(/^Resolution$/i);
  if (res) qas.push({ q: `Which video resolutions does it support?`, a: `Supported resolutions: ${res[1]}` });
  const enc = pick(/Encoding|Video.*Format/i, /^Audio/);
  if (enc) qas.push({ q: `Which encoding formats does the ${model} support?`, a: `${enc[0]}: ${enc[1]}` });
  const power = pick(/^Power/i);
  if (power) qas.push({ q: `What power supply does it need?`, a: `${power[0]}: ${power[1]}` });
  if (p.source_pdf) {
    qas.push({ q: `Is the ${model} datasheet available?`, a: `Yes - the full ${model} datasheet (PDF) can be downloaded from this page.` });
  }
  // keep the list short and non-repetitive, and drop answers that only repeat the question
  const seen = new Set();
  return qas
    .filter((x) => {
      const key = x.a.toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(0, 5);
};

// ---------- related models: same category first, same model family preferred ----------
export const relatedFor = (products, product, model, limit = 4) => {
  const fam = familyOf(model);
  const others = products.filter((p) => p.slug !== product.slug);
  const rank = (p) => {
    const pm = modelOf(p);
    let score = 0;
    if (p.category === product.category) score += 100;
    if (familyOf(pm) === fam) score += 50;
    return score;
  };
  return others
    .filter((p) => rank(p) > 0)
    .sort((a, b) => rank(b) - rank(a) || a.name.localeCompare(b.name, 'en'))
    .slice(0, limit);
};

// ---------- typical use (category-level, real per category) ----------
export const CATEGORY_USE = {
  encoder: 'Streaming and broadcast headends that need to turn HDMI or SDI sources into IP streams — IPTV platforms, hotel in-room TV, live event contribution, cable and DTT distribution.',
  'encoder-modulator': 'Headends that feed a coax RF network directly from HDMI or SDI sources — hotels, hospitals, campuses and small cable systems.',
  modulator: 'Channel generation for DVB-T/C, ISDB-T, ATSC or QAM networks — local TV distribution, hospitality TV, and re-multiplexed regional line-ups.',
  'ip-gateway': 'Interfacing between IP and ASI/RF legs of a headend — multicast to ASI conversion, IP backbones, and satellite or terrestrial feeds.',
  'ird-decoder': 'Receiving, descrambling, decoding and transcoding satellite or IP feeds — turn-around, monitoring and contribution links.',
  multiplexer: 'Building the MPTS/SPTS line-up and CAS/EPG handling — transport-stream muxing, scrambling and EIT processing.',
  transmitter: 'Terrestrial and FM transmission — DVB-T coverage for regional networks and FM stereo broadcast from 10 W to 10 kW.',
  software: 'Server-side headend services — EPG generation, IPTV middleware and subscriber/ads management platforms.',
  other: 'Supporting headend hardware — capture, processing, analysis and interfacing devices used alongside the encoder and modulator line.',
};
