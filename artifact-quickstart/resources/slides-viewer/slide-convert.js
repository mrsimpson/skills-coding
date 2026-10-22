"use strict";
// Gemeinsame Umwandlung: Folien-HTML -> bereinigtes DOM mit Standardelementen.
const ICONS = {
  Check: '<path d="M4 12.5l5 5L20 6.5"/>',
  CheckCircle: '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l3 3 5-6"/>',
  Warning: '<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v.5"/>',
  Star: '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
  Lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 018 0v3"/>',
  Key: '<circle cx="8" cy="12" r="4"/><path d="M12 12h9M18 12v4M21 12v3"/>',
  Search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/>',
  Settings: '<circle cx="12" cy="12" r="3.2"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1"/>',
  Home: '<path d="M3 11l9-8 9 8M5.5 9.5V21h13V9.5M10 21v-6h4v6"/>',
  Clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
  Cloud: '<path d="M7 18a4.5 4.5 0 01-.6-8.96A6 6 0 0118 10a4 4 0 010 8z"/>',
  Code: '<path d="M8 7l-5 5 5 5M16 7l5 5-5 5M14 4l-4 16"/>',
  Database: '<ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
  Globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>',
  Link: '<path d="M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1 1M14 10a4 4 0 00-5.7 0l-3 3a4 4 0 005.7 5.7l1-1"/>',
  Play: '<path d="M7 4l13 8-13 8z"/>',
  PaperPlane: '<path d="M21 3L3 10.5l7 3 3 7zM10 13.5L21 3"/>',
  Users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6M16 4.7a3.5 3.5 0 010 6.6M18 14.3c2.2.7 3.5 2.7 3.5 5.7"/>',
  ThumbsUp: '<path d="M7 11v10H3V11zM7 11l4-8c1.7 0 2.5 1.2 2 3l-.7 3H19a2 2 0 012 2.3l-1.2 7A2 2 0 0117.8 21H7"/>',
  Tool: '<path d="M14.5 6.5a4 4 0 005 5L12 19a2.1 2.1 0 01-3-3zM9 9L3.5 3.5"/>',
  Wrench: '<path d="M15 4a5 5 0 00-4.6 6.9L3.5 17.8a2 2 0 003 3l6.9-6.9A5 5 0 0020 9l-3.2 3.2-3-3L17 6A5 5 0 0015 4z"/>',
  Lightbulb: '<path d="M9 18h6M10 21h4M12 3a6 6 0 00-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0012 3z"/>',
  Lightning: '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
  Book: '<path d="M4 4.5A2.5 2.5 0 016.5 2H20v17H6.5A2.5 2.5 0 004 21.5zM4 21.5A2.5 2.5 0 016.5 19H20"/>',
  Chart: '<path d="M4 20V4M4 20h16M8 16v-4M12 16V8M16 16v-6"/>',
  Chat: '<path d="M21 12a8 8 0 01-11.6 7.1L3 21l1.9-5.4A8 8 0 1121 12z"/>',
  Activity: '<path d="M2 12h4l3-8 5 16 3-8h5"/>',
  GraduationCap: '<path d="M2 9l10-5 10 5-10 5zM6 11.5V16c0 1.5 2.7 3 6 3s6-1.5 6-3v-4.5M22 9v6"/>',
  Trust: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/>',
  Verified: '<path d="M12 2l2.4 2 3.1-.2 1 3 2.7 1.6-1 3 1 3-2.7 1.6-1 3-3.1-.2L12 22l-2.4-2-3.1.2-1-3L2.8 15.6l1-3-1-3L5.5 8l1-3 3.1.2z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>'
};

function svgEl(doc, tag, attrs) {
  const e = doc.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(attrs || {})) e.setAttribute(k, v);
  return e;
}
function carry(from, to) {
  for (const a of from.attributes) if (a.name === 'id' || a.name.startsWith('data-')) to.setAttribute(a.name, a.value);
  return to;
}
function num(v) { const n = parseFloat(v); return Number.isFinite(n) ? n : 0; }

function convertConnector(doc, el, idx) {
  const st = el.style;
  const color = st.getPropertyValue('color') || '#888';
  const stroke = num(st.getPropertyValue('border-width')) || 2;
  const dashed = /dashed/.test(st.getPropertyValue('border-style'));
  const dotted = /dotted/.test(st.getPropertyValue('border-style'));
  const x1 = num(el.getAttribute('x1')), y1 = num(el.getAttribute('y1'));
  const x2 = num(el.getAttribute('x2')), y2 = num(el.getAttribute('y2'));
  const route = el.getAttribute('route') || 'straight';
  let d;
  if (route === 'hv') d = `M${x1} ${y1}L${x2} ${y1}L${x2} ${y2}`;
  else if (route === 'vh') d = `M${x1} ${y1}L${x1} ${y2}L${x2} ${y2}`;
  else if (route === 'elbow') {
    if (Math.abs(x2 - x1) >= Math.abs(y2 - y1)) { const mx = (x1 + x2) / 2; d = `M${x1} ${y1}L${mx} ${y1}L${mx} ${y2}L${x2} ${y2}`; }
    else { const my = (y1 + y2) / 2; d = `M${x1} ${y1}L${x1} ${my}L${x2} ${my}L${x2} ${y2}`; }
  } else d = `M${x1} ${y1}L${x2} ${y2}`;
  const head = el.getAttribute('head') || 'end';
  const hs = el.getAttribute('head-start') || (head === 'both' ? 'filled' : 'none');
  const he = el.getAttribute('head-end') || (head === 'none' ? 'none' : 'filled');
  const svg = svgEl(doc, 'svg', { width: 1, height: 1, style: 'position:absolute;left:0;top:0;overflow:visible' });
  const defs = svgEl(doc, 'defs');
  const size = stroke * 4;
  const mk = (id, kind) => {
    const m = svgEl(doc, 'marker', { id, markerUnits: 'userSpaceOnUse', markerWidth: size, markerHeight: size, refX: size * 0.9, refY: size / 2, orient: 'auto-start-reverse', overflow: 'visible' });
    m.appendChild(kind === 'open'
      ? svgEl(doc, 'path', { d: `M0 0L${size} ${size / 2}L0 ${size}`, fill: 'none', stroke: color, 'stroke-width': stroke, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' })
      : svgEl(doc, 'path', { d: `M0 0L${size} ${size / 2}L0 ${size}z`, fill: color }));
    defs.appendChild(m);
  };
  const path = svgEl(doc, 'path', { d, fill: 'none', stroke: color, 'stroke-width': stroke, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' });
  if (dashed) path.setAttribute('stroke-dasharray', `${stroke * 4} ${stroke * 3}`);
  if (dotted) path.setAttribute('stroke-dasharray', `0 ${stroke * 2.2}`);
  if (hs !== 'none') { mk('ms' + idx, hs); path.setAttribute('marker-start', `url(#ms${idx})`); }
  if (he !== 'none') { mk('me' + idx, he); path.setAttribute('marker-end', `url(#me${idx})`); }
  svg.append(defs, path);
  return svg;
}

const SHAPE_CLIP = {
  diamond: 'polygon(50% 0,100% 50%,50% 100%,0 50%)',
  'arrow-right': 'polygon(0 30%,60% 30%,60% 0,100% 50%,60% 100%,60% 70%,0 70%)',
  'arrow-left': 'polygon(100% 30%,40% 30%,40% 0,0 50%,40% 100%,40% 70%,100% 70%)',
  'arrow-up': 'polygon(30% 100%,30% 40%,0 40%,50% 0,100% 40%,70% 40%,70% 100%)',
  'arrow-down': 'polygon(30% 0,70% 0,70% 60%,100% 60%,50% 100%,0 60%,30% 60%)'
};

function prepareSlide(html, key) {
  const doc = new DOMParser().parseFromString('<body>' + html + '</body>', 'text/html');
  const sec = doc.body.querySelector('section');
  if (!sec) return { sec: null, notes: '', embeds: false };
  let notes = '';
  const aside = sec.querySelector(':scope > aside');
  if (aside) { notes = aside.textContent.trim(); aside.remove(); }
  // Aktive und externe Inhalte entfernen: der Viewer führt nie Folien-Code aus.
  sec.querySelectorAll('script,iframe,object,embed,link,base,meta,style,form').forEach((n) => n.remove());
  let embeds = false, n = 0;
  sec.querySelectorAll('*').forEach((el) => {
    for (const a of [...el.attributes]) {
      if (/^on/i.test(a.name) || (/^(href|src|xlink:href)$/i.test(a.name) && /^\s*javascript:/i.test(a.value))) el.removeAttribute(a.name);
    }
  });
  sec.querySelectorAll('x-shape').forEach((el) => {
    const d = doc.createElement('div');
    d.setAttribute('style', el.getAttribute('style') || '');
    const kind = el.getAttribute('kind') || 'rect';
    if (kind === 'ellipse') d.style.borderRadius = '50%';
    else if (kind === 'rounded') d.style.borderRadius = '24px';
    else if (kind === 'line') { if (!d.style.height) d.style.height = d.style.borderWidth || '2px'; }
    else if (SHAPE_CLIP[kind]) d.style.clipPath = SHAPE_CLIP[kind];
    el.replaceWith(carry(el, d));
  });
  sec.querySelectorAll('x-icon').forEach((el) => {
    const name = el.getAttribute('name') || '';
    const svg = svgEl(doc, 'svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.7, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', role: 'img', 'aria-label': name });
    svg.innerHTML = ICONS[name] || '<rect x="4" y="4" width="16" height="16" rx="3"/>';
    const st = el.getAttribute('style') || '';
    svg.setAttribute('style', 'display:block;width:48px;height:48px;' + st);
    el.replaceWith(carry(el, svg));
  });
  sec.querySelectorAll('x-connector').forEach((el) => {
    if (el.hasAttribute('x1')) { el.replaceWith(carry(el, convertConnector(doc, el, key + '_' + (n++)))); return; }
    const d = doc.createElement('div');
    d.setAttribute('style', 'width:96px;height:0;border-top:2px solid ' + (el.style.color || '#888') + ';' + (el.getAttribute('style') || ''));
    el.replaceWith(carry(el, d));
  });
  sec.querySelectorAll('x-embed').forEach((el) => {
    embeds = true;
    const f = doc.createElement('iframe');
    f.setAttribute('sandbox', 'allow-scripts');
    f.setAttribute('srcdoc', el.innerHTML);
    f.setAttribute('style', 'border:0;background:transparent;' + (el.getAttribute('style') || ''));
    el.replaceWith(carry(el, f));
  });
  return { sec, notes, embeds };
}

function fontHead(faces) {
  let head = '';
  for (const f of Object.values(faces || {})) {
    if (f.href && /^https:\/\/fonts\.googleapis\.com\/css2\?/.test(f.href)) head += `<link rel="stylesheet" href="${f.href.replace(/"/g, '&quot;')}">`;
    else if (f.src && /^(project\/|\/_blob\/)/.test(f.src)) head += `<style>@font-face{font-family:"${String(f.family).replace(/[^\w \-]/g, '')}";src:url("${f.src}")}</style>`;
  }
  return head;
}

// Tokens anwenden und Deck laden (gleich für beide Viewer).
function applyTokens(t) {
  const r = document.documentElement.style;
  for (const [k, v] of Object.entries(t.color)) r.setProperty('--c-' + k, v);
  for (const [k, v] of Object.entries(t.font)) r.setProperty('--f-' + k, v);
  for (const [k, v] of Object.entries(t.size)) r.setProperty('--s-' + k, v);
}
async function getJSON(url) { const r = await fetch(url); if (!r.ok) throw new Error(url + ': ' + r.status); return r.json(); }
async function getText(url) { const r = await fetch(url); if (!r.ok) throw new Error(url + ': ' + r.status); return r.text(); }
async function loadDeck(state) {
  const q = new URLSearchParams(location.search);
  const base = (q.get('deck') || 'project').replace(/\/$/, '');
  if (window.__TOKENS__) applyTokens(window.__TOKENS__); else applyTokens(await getJSON(q.get('tokens') || 'tokens.json'));
  if (window.__DECK__) {
    state.deck = window.__DECK__.deck; state.slides = window.__DECK__.slides;
  } else {
    state.deck = await getJSON(base + '/deck.json');
    await Promise.all([...new Set(state.deck.order || [])].map(async (id) => { state.slides[id] = await getText(base + '/slides/' + id + '.html'); }));
  }
  state.order = (state.deck.order || []).filter((id) => id in state.slides);
}
