// Tests for the leaderboard widget logic in digest-app.js.
// Run with:  node --test vendor/ai-news-digest/
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const { PROVIDER_COLORS, resolveLbColumns, renderLbLinks, lbTooltip, sourceLinkHtml } = require('./digest-app.js');

// ── Extract the `const leaderboards = {…}` object literal from a template ──
function extractLeaderboards(html) {
  const marker = 'const leaderboards = ';
  const start = html.indexOf(marker);
  assert.ok(start >= 0, 'leaderboards marker not found');
  const objStart = start + marker.length;
  let depth = 0, inStr = false, quote = '', esc = false;
  for (let i = objStart; i < html.length; i++) {
    const ch = html[i];
    if (inStr) {
      if (esc) esc = false;
      else if (ch === '\\') esc = true;
      else if (ch === quote) inStr = false;
    } else if (ch === '"' || ch === "'" || ch === '`') { inStr = true; quote = ch; }
    else if (ch === '{') depth++;
    else if (ch === '}' && --depth === 0) return html.slice(objStart, i + 1);
  }
  throw new Error('unbalanced leaderboards object');
}

const templateHtml = fs.readFileSync(path.join(__dirname, 'template.html'), 'utf8');
const leaderboards = eval('(' + extractLeaderboards(templateHtml) + ')');

// ── resolveLbColumns: defaults per active tab + explicit overrides ──
test('resolveLbColumns defaults for aa', () => {
  assert.deepStrictEqual(resolveLbColumns({}, 'aa'), { providerCol: 2, scoreCol: 3, scoreMax: 60 });
});
test('resolveLbColumns defaults for open-weight', () => {
  assert.deepStrictEqual(resolveLbColumns({}, 'open'), { providerCol: 2, scoreCol: -1, scoreMax: 100 });
});
test('resolveLbColumns defaults for other tabs (vellum)', () => {
  assert.deepStrictEqual(resolveLbColumns({}, 'vellum'), { providerCol: 1, scoreCol: -1, scoreMax: 100 });
});
test('resolveLbColumns honours explicit overrides regardless of tab', () => {
  const lb = { providerCol: 2, scoreCol: 3, scoreMax: 1600 };
  assert.deepStrictEqual(resolveLbColumns(lb, 'arena_video'), lb);
  assert.deepStrictEqual(resolveLbColumns(lb, 'aa'), lb);
});
test('resolveLbColumns treats 0 as a valid override (not null)', () => {
  assert.deepStrictEqual(
    resolveLbColumns({ providerCol: 0, scoreCol: 0, scoreMax: 0 }, 'aa'),
    { providerCol: 0, scoreCol: 0, scoreMax: 0 }
  );
});

// ── lbTooltip: plain-language glossary for column headers ──
test('lbTooltip explains the T2I Elo metric (mentions preference votes)', () => {
  const tip = lbTooltip('Elo');
  assert.ok(tip.length > 0, 'Elo must have a tooltip');
  assert.match(tip, /preference|head-to-head/i);
});
test('lbTooltip covers common metric labels', () => {
  for (const label of ['Intelligence', 'HumanEval+', 'Resolved %', 'Score', 'Votes']) {
    assert.ok(lbTooltip(label).length > 0, `missing tooltip for "${label}"`);
  }
});
test('lbTooltip returns empty string for unknown labels', () => {
  assert.strictEqual(lbTooltip('Totally Unknown Column'), '');
});

// ── renderLbLinks: pure markup, no tabs, correct anchors ──
test('renderLbLinks renders one anchor per item with name/url/source', () => {
  const lb = { groups: [{ label: 'Group A', items: [
    { name: 'Alpha', source: 'a.com', url: 'https://a.com/x' },
    { name: 'Beta', source: 'b.com', url: 'https://b.com/y' },
  ] }] };
  const html = renderLbLinks(lb);
  assert.match(html, /Group A/);
  assert.match(html, /href="https:\/\/a\.com\/x"/);
  assert.match(html, /href="https:\/\/b\.com\/y"/);
  assert.match(html, /Alpha/);
  assert.match(html, /a\.com \u2197/);
  assert.strictEqual((html.match(/<a /g) || []).length, 2);
  assert.ok(!html.includes('lb-tab'), 'links markup must not include tab buttons');
});

// ── sourceLinkHtml: real link vs. kept-topic "Source pending" ──
test('sourceLinkHtml renders a Read source anchor for a real url', () => {
  const html = sourceLinkHtml('https://www.figure.ai/news/project-go-big');
  assert.match(html, /^<a /);
  assert.match(html, /href="https:\/\/www\.figure\.ai\/news\/project-go-big"/);
  assert.match(html, /Read source/);
});
test('sourceLinkHtml degrades to a non-link Source pending span when url is missing', () => {
  for (const url of [null, undefined, '']) {
    const html = sourceLinkHtml(url);
    assert.ok(!html.includes('<a '), 'must not emit an anchor (no dead link)');
    assert.match(html, /Source pending/);
    assert.match(html, /card-link-pending/);
  }
});

// ── Data-contract checks on the shipped leaderboards object ──
test('new T2I/T2V/links tabs exist', () => {
  for (const key of ['arena_t2i', 'arena_video', 'links']) {
    assert.ok(leaderboards[key], `missing leaderboards.${key}`);
  }
});

test('structured-API tabs (swe, coding) exist and disable provider dots', () => {
  for (const key of ['swe', 'coding']) {
    const lb = leaderboards[key];
    assert.ok(lb, `missing leaderboards.${key}`);
    assert.strictEqual(lb.providerCol, -1, `${key} should set providerCol:-1`);
    assert.strictEqual(typeof lb.scoreCol, 'number', `${key}.scoreCol must be a number`);
    assert.ok(Array.isArray(lb.rows) && lb.rows.length > 0, `${key} needs seed rows`);
  }
});

test('arena tabs declare numeric column config', () => {
  for (const key of ['arena_image', 'arena_t2i', 'arena_video']) {
    const lb = leaderboards[key];
    for (const f of ['providerCol', 'scoreCol', 'scoreMax']) {
      assert.strictEqual(typeof lb[f], 'number', `${key}.${f} must be a number`);
    }
  }
});

test('every table row matches its column count', () => {
  for (const [key, lb] of Object.entries(leaderboards)) {
    if (!Array.isArray(lb.rows) || !Array.isArray(lb.cols)) continue;
    lb.rows.forEach((row, i) =>
      assert.strictEqual(row.length, lb.cols.length, `${key} row ${i} arity != cols`));
  }
});

test('every table row provider has a PROVIDER_COLORS entry', () => {
  for (const [key, lb] of Object.entries(leaderboards)) {
    if (!Array.isArray(lb.rows) || !Array.isArray(lb.cols)) continue;
    const { providerCol } = resolveLbColumns(lb, key);
    if (providerCol < 0) continue; // tabs without a provider column render no dots
    lb.rows.forEach((row) => {
      const provider = row[providerCol];
      assert.ok(PROVIDER_COLORS[provider], `no color for provider "${provider}" in ${key}`);
    });
  }
});

test('every table tab\'s score-column label has a glossary tooltip', () => {
  for (const [key, lb] of Object.entries(leaderboards)) {
    if (!Array.isArray(lb.cols)) continue;
    const { scoreCol } = resolveLbColumns(lb, key);
    if (scoreCol < 0) continue; // tabs without a primary score column
    const label = lb.cols[scoreCol];
    assert.ok(lbTooltip(label).length > 0, `no tooltip for score column "${label}" in ${key}`);
  }
});

test('links tab is well-formed with resolvable URLs', () => {
  const lb = leaderboards.links;
  assert.strictEqual(lb.type, 'links');
  assert.ok(Array.isArray(lb.groups) && lb.groups.length > 0);
  for (const g of lb.groups) {
    assert.strictEqual(typeof g.label, 'string');
    assert.ok(Array.isArray(g.items) && g.items.length > 0);
    for (const it of g.items) {
      assert.strictEqual(typeof it.name, 'string');
      assert.ok(/^https?:\/\//.test(it.url), `bad url: ${it.url}`);
    }
  }
});
