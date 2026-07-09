const PROVIDER_COLORS = {
  OpenAI: '#10a37f', Anthropic: '#d4763b', Google: '#4285f4',
  DeepSeek: '#1a6cf5', Alibaba: '#ff6a00', Meta: '#0866ff',
  Kimi: '#8b5cf6', Xiaomi: '#ff6900', 'Z AI': '#06b6d4', MiniMax: '#ec4899',
  Reve: '#7c3aed', 'Microsoft AI': '#00a4ef', xAI: '#e0e0e0',
  Ideogram: '#ff5c8a', 'Luma AI': '#14b8a6', 'Black Forest Labs': '#16a34a',
  Bytedance: '#325ab4', 'Alibaba-ATH': '#ff8c42', KlingAI: '#00c2a8',
  Runway: '#22c55e', Pixverse: '#a855f7', Pruna: '#f59e0b', Kandinsky: '#6366f1',
  Tencent: '#1e90ff', Lightricks: '#ef4444', 'Genmo AI': '#0ea5e9',
  HiDream: '#db2777', NVIDIA: '#76b900', Recraft: '#e11d48', Krea: '#fbbf24',
  'Zhipu AI': '#38bdf8', 'Moonshot AI': '#a78bfa', Qwen: '#f97316', Meituan: '#ffb000'
};

const CAT_COLORS = {
  leaderboard: '#F39C12', analytics: '#6366F1', aisearch: '#F0883E', youtube: '#E74C3C',
  'agentic-ai': '#0EA5E9',
  llm: '#2C3E50', rag: '#14B8A6', 'image-gen': '#8E44AD', 'design-ai': '#16A085',
  typography: '#C0392B', robotics: '#E67E22', research: '#2980B9'
};

// Plain-language explanations for leaderboard column headers, shown on hover.
// Keyed by the exact label text used in each tab's `cols` array.
const LB_GLOSSARY = {
  '#': 'Rank by the leaderboard\u2019s primary metric.',
  'Model': 'Model being evaluated.',
  'Model / Agent': 'Model (with its agent/scaffold) being evaluated.',
  'Provider': 'Organization that develops the model.',
  'Intelligence': 'Artificial Analysis Intelligence Index \u2014 a composite across reasoning, knowledge, coding and math benchmarks; higher is better.',
  'Speed (t/s)': 'Output speed in tokens generated per second; higher is faster.',
  'Latency (s)': 'Time to first token, in seconds; lower is more responsive.',
  'Context': 'Maximum context window (input + output tokens) the model accepts.',
  'Price /1M': 'Blended cost per 1 million tokens, in USD.',
  'Resolved %': 'Share of SWE-bench Verified GitHub issues the agent fully resolved; higher is better.',
  'Date': 'Date the result was submitted to the leaderboard.',
  'Params (B)': 'Model size in billions of parameters (\u2014 if undisclosed).',
  'HumanEval+': 'EvalPlus HumanEval+ pass@1 \u2014 % of Python problems solved against the harder, augmented test suite.',
  'MBPP+': 'EvalPlus MBPP+ pass@1 \u2014 % solved on the augmented MBPP Python benchmark.',
  '\uD83C\uDF0D': 'Country/region where the model originates.',
  'Code Arena': 'Code-focused arena Elo from head-to-head human preference votes.',
  'Reasoning': 'Reasoning benchmark score; higher is better.',
  'Math': 'Math benchmark score; higher is better.',
  'Elo': 'Elo rating from pairwise human preference votes \u2014 users pick the better of two outputs; higher means it wins more head-to-head matchups.',
  'Score': 'Arena score (Elo-style) from head-to-head human preference votes; higher is better.',
  'Votes': 'Number of human preference votes collected in the arena for this model.'
};

function lbTooltip(label) {
  return LB_GLOSSARY[label] || '';
}

function resolveLbColumns(lb, activeLb) {
  return {
    providerCol: lb.providerCol != null ? lb.providerCol : (activeLb === 'aa' || activeLb === 'open') ? 2 : 1,
    scoreCol:    lb.scoreCol    != null ? lb.scoreCol    : (activeLb === 'aa') ? 3 : -1,
    scoreMax:    lb.scoreMax    != null ? lb.scoreMax    : (activeLb === 'aa') ? 60 : 100
  };
}

function renderLbLinks(lb) {
  return lb.groups.map(g => `
        <div class="lb-links-group">
          <div class="lb-links-head">${g.label}</div>
          ${g.items.map(it => `<a class="lb-link-row" href="${it.url}" target="_blank" rel="noopener"><span class="lb-link-name">${it.name}</span><span class="lb-link-src">${it.source} ↗</span></a>`).join('')}
        </div>`).join('');
}

let allStories = [];
let activeFilter = 'all';
let activeSig = null;
let activeTag = null;

function applyFilters() {
  let stories = activeFilter === 'all' ? allStories : allStories.filter(s => s.catId === activeFilter);
  if (activeSig !== null) stories = stories.filter(s => s.significance === activeSig);
  if (activeTag !== null) stories = stories.filter(s => s.tags.includes(activeTag));
  return stories;
}

function setSig(sig) {
  activeSig = activeSig === sig ? null : sig;
  redrawSigChart();
  renderCards(activeFilter);
}

function setTag(tag) {
  activeTag = activeTag === tag ? null : tag;
  redrawTagCloud();
  renderCards(activeFilter);
}

/** Branch badge: LLM Pipeline vs Hermes Agent (see report_source_* in digest JSON). */
function reportSourceSealMarkup(data) {
  const href = data && data.report_source_badge;
  const label = (data && (data.report_source_label || data.report_source)) || 'Digest source';
  if (!href) return '';
  const tip = 'Produced by ' + label;
  return '<img src="' + escHtml(href) + '" alt="' + escHtml(label) + '" title="' + escHtml(tip) + '">';
}

function renderReportSourceSeal(data) {
  const el = document.getElementById('report-source-seal');
  if (!el) return;
  const label = (data && (data.report_source_label || data.report_source)) || 'Digest source';
  const markup = reportSourceSealMarkup(data);
  if (!markup) {
    el.hidden = true;
    el.innerHTML = '';
    el.removeAttribute('title');
    return;
  }
  el.hidden = false;
  el.title = 'Produced by ' + label;
  el.setAttribute('aria-label', label + ' report');
  el.innerHTML = markup;
}

function render(data) {
  allStories = [];
  data.categories.forEach(cat => {
    cat.stories.forEach(s => allStories.push({ ...s, catId: cat.id, catLabel: cat.label, catIcon: cat.icon }));
  });
  renderReportSourceSeal(data);
  const dt = new Date(data.generated_at);
  document.getElementById('digest-date').textContent =
    dt.toLocaleDateString('en-US', { weekday:'long', year:'numeric', month:'long', day:'numeric' }).toUpperCase();
  document.getElementById('digest-summary').textContent = data.summary;
  renderTopStories(data);
  renderFilterPills(data);
  renderDonut(data);
  renderSigChart(data);
  renderTagCloud(data);
  renderCards('all');
  document.getElementById('footer-count').textContent =
    allStories.length + ' stories · ' + data.categories.length + ' categories';
  initLayoutResizer();
}

function renderTopStories(data) {
  const bar = document.getElementById('top-stories-bar');
  data.visualizations.top_stories.forEach(ts => {
    const pill = document.createElement('button');
    pill.className = 'top-story-pill';
    pill.textContent = ts.title;
    pill.onclick = () => scrollToStory(ts.id);
    bar.appendChild(pill);
  });
}

function renderFilterPills(data) {
  const bar = document.getElementById('filter-bar');
  bar.innerHTML = '';
  const allPill = document.createElement('button');
  allPill.className = 'pill active';
  allPill.textContent = 'All (' + allStories.length + ')';
  allPill.dataset.filter = 'all';
  allPill.onclick = () => setFilter('all');
  bar.appendChild(allPill);
  data.categories.forEach(cat => {
    const pill = document.createElement('button');
    pill.className = 'pill inactive';
    if (cat.id === 'leaderboard' || cat.id === 'aisearch' || cat.id === 'youtube') {
      pill.innerHTML = cat.icon + ' ' + cat.label;
    } else {
      if (!cat.stories.length) return;
      pill.innerHTML = cat.icon + ' ' + cat.label + ' <span style="color:var(--muted);font-size:.7em">(' + cat.stories.length + ')</span>';
    }
    pill.dataset.filter = cat.id;
    pill.onclick = () => setFilter(cat.id);
    bar.appendChild(pill);
  });
}

function setFilter(id) {
  activeFilter = id;
  document.querySelectorAll('.pill').forEach(p => {
    p.className = 'pill ' + (p.dataset.filter === id ? 'active' : 'inactive');
  });
  renderCards(id);
}

function renderAISearch(grid) {
  const stories = allStories.filter(s => s.catId === 'aisearch');
  const videoUrl   = digestData.aisearch_video_url   || 'https://www.youtube.com/@theAIsearch';
  const videoLabel = digestData.aisearch_video_label || 'Latest video';
  grid.innerHTML = `
    <div style="grid-column:1/-1;display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding-bottom:14px;border-bottom:1px solid var(--border);margin-bottom:4px;">
      <span style="font-size:12px;font-weight:600;color:var(--text)">🔍 theAIsearch</span>
      <a href="${videoUrl}" target="_blank" rel="noopener"
         style="font-size:11px;color:var(--accent);text-decoration:none;display:flex;align-items:center;gap:4px;">
        ▶ ${videoLabel}
      </a>
      <span style="margin-left:auto;display:flex;gap:12px;">
        <a href="https://ai-search.io" target="_blank" rel="noopener" style="font-size:11px;color:var(--muted);text-decoration:none;">🌐 ai-search.io</a>
        <a href="https://www.youtube.com/@theAIsearch" target="_blank" rel="noopener" style="font-size:11px;color:var(--muted);text-decoration:none;">▶ @theAIsearch</a>
      </span>
    </div>`;
  stories.forEach(story => grid.appendChild(buildCard(story)));
}

function renderYouTube(grid) {
  const cat = (digestData.categories || []).find(c => c.id === 'youtube');
  const stories = allStories.filter(s => s.catId === 'youtube');
  const sources = (cat && cat.sources) || [];

  const channels = sources.length
    ? sources.map(src => ({
        key: src.channel_key || src.channel_label,
        label: src.channel_label || src.channel_key,
      }))
    : Object.values(
        stories.reduce((acc, s) => {
          const key = s.channel_key || s.channel_label || 'youtube';
          if (!acc[key]) {
            acc[key] = { key, label: s.channel_label || s.channel_key || 'YouTube' };
          }
          return acc;
        }, {})
      ).sort((a, b) => a.label.localeCompare(b.label));

  let activeChannel = 'all';

  function channelTabs() {
    return `
      <div class="lb-tabs">
        <button class="lb-tab ${activeChannel === 'all' ? 'active' : ''}" data-ch="all">
          All (${stories.length})
        </button>
        ${channels.map(ch => `
          <button class="lb-tab ${activeChannel === ch.key ? 'active' : ''}" data-ch="${ch.key}">
            📺 ${ch.label}
          </button>`).join('')}
      </div>`;
  }

  function storiesForChannel(ch) {
    return stories.filter(
      s => s.channel_key === ch.key || s.channel_label === ch.label
    );
  }

  function visibleStories() {
    if (activeChannel === 'all') return stories;
    const ch = channels.find(c => c.key === activeChannel);
    return ch ? storiesForChannel(ch) : stories;
  }

  function draw() {
    grid.innerHTML = '';
    const wrap = document.createElement('div');
    wrap.className = 'lb-wrap';
    wrap.style.gridColumn = '1 / -1';
    wrap.innerHTML = channelTabs();
    wrap.querySelectorAll('.lb-tab').forEach(btn => {
      btn.onclick = () => { activeChannel = btn.dataset.ch; draw(); };
    });
    grid.appendChild(wrap);
    visibleStories().forEach(story => grid.appendChild(buildCard(story)));
  }

  draw();
}

function renderCards(filter) {
  const grid = document.getElementById('story-grid');
  if (filter === 'leaderboard') { renderLeaderboard(grid); return; }
  if (filter === 'aisearch') { renderAISearch(grid); return; }
  if (filter === 'youtube') { renderYouTube(grid); return; }
  const stories = applyFilters();
  if (!stories.length) { grid.innerHTML = '<div class="empty-state">No stories match the current filters.</div>'; return; }
  grid.innerHTML = '';
  stories.forEach(story => grid.appendChild(buildCard(story)));
}

function renderLeaderboard(grid) {
  let activeLb = 'aa';
  function tabs(lb) {
    return `
      <div class="lb-tabs">
        <button class="lb-tab ${activeLb==='aa'?'active':''}"           data-lb="aa">🏅 AA: All Models</button>
        <button class="lb-tab ${activeLb==='open'?'active':''}"         data-lb="open">🔓 Open-Weight</button>
        <button class="lb-tab ${activeLb==='swe'?'active':''}"          data-lb="swe">🐛 SWE-bench</button>
        <button class="lb-tab ${activeLb==='coding'?'active':''}"       data-lb="coding">⌨️ EvalPlus</button>
        <button class="lb-tab ${activeLb==='arena_image'?'active':''}"  data-lb="arena_image">🎨 Image Arena</button>
        <button class="lb-tab ${activeLb==='arena_t2i'?'active':''}"    data-lb="arena_t2i">🖼️ T2I: AA</button>
        <button class="lb-tab ${activeLb==='arena_video'?'active':''}"  data-lb="arena_video">🎬 T2V: Arena</button>
        <button class="lb-tab ${activeLb==='vellum'?'active':''}"       data-lb="vellum">📊 Vellum: All</button>
        <button class="lb-tab ${activeLb==='vellum_open'?'active':''}"  data-lb="vellum_open">📊 Vellum: Open</button>
        <button class="lb-tab ${activeLb==='links'?'active':''}"        data-lb="links">🔗 More</button>
        ${lb.url ? `<a class="lb-src" href="${lb.url}" target="_blank" rel="noopener">↗ ${lb.source}</a>` : ''}
        ${lb.updated ? `<span class="lb-updated">Updated ${lb.updated}</span>` : ''}
      </div>`;
  }
  function buildTable(lb) {
    let sortCol = null, sortDir = 1;
    grid.innerHTML = `<div class="lb-wrap">${tabs(lb)}
      <div class="lb-table-wrap">
        <table class="lb-table" id="lb-table">
          <thead><tr>${lb.cols.map((c,i)=>{const tip=lbTooltip(c);return `<th class="lb-th${tip?' lb-th-info':''}" data-col="${i}"${tip?` title="${tip.replace(/"/g,'&quot;')}"`:''}>${c} <span class="sort-arrow">↕</span></th>`;}).join('')}</tr></thead>
          <tbody id="lb-body"></tbody>
        </table>
      </div></div>`;
    grid.querySelectorAll('.lb-tab').forEach(btn => { btn.onclick = () => { activeLb = btn.dataset.lb; build(); }; });
    function scoreColor(val, max) {
      const t = val/max;
      return t > 0.9 ? '#3fb950' : t > 0.75 ? '#58a6ff' : t > 0.6 ? '#d29922' : '#8b949e';
    }
    function drawRows(rows) {
      const { providerCol, scoreCol, scoreMax } = resolveLbColumns(lb, activeLb);
      document.getElementById('lb-body').innerHTML = rows.map(row => {
        const provider = row[providerCol];
        const dot = `<span class="lb-dot" style="background:${PROVIDER_COLORS[provider]||'#555'}"></span>`;
        return '<tr>' + row.map((cell, i) => {
          if (i === providerCol) return `<td>${dot}${cell}</td>`;
          if (i === scoreCol && typeof cell === 'number' && cell > 0) {
            const pct = Math.round((cell/scoreMax)*100);
            return `<td><div class="lb-bar-cell"><span class="lb-bar-fill" style="width:${Math.min(pct,100)}%;background:${scoreColor(cell,scoreMax)}"></span><span class="lb-bar-val">${cell}</span></div></td>`;
          }
          return `<td>${cell === 0 ? '—' : cell}</td>`;
        }).join('') + '</tr>';
      }).join('');
    }
    drawRows(lb.rows);
    grid.querySelectorAll('.lb-th').forEach(th => {
      th.onclick = () => {
        const col = +th.dataset.col;
        sortDir = sortCol === col ? -sortDir : 1; sortCol = col;
        grid.querySelectorAll('.lb-th .sort-arrow').forEach(a => a.textContent='↕');
        th.querySelector('.sort-arrow').textContent = sortDir===1?'↑':'↓';
        drawRows([...lb.rows].sort((a,b) => {
          const va=a[col], vb=b[col];
          if (va==='—'||va===null||va===0) return 1; if (vb==='—'||vb===null||vb===0) return -1;
          return typeof va==='number'&&typeof vb==='number' ? (va-vb)*sortDir : String(va).localeCompare(String(vb))*sortDir;
        }));
      };
    });
  }
  function buildCharts(lb) {
    grid.innerHTML = `<div class="lb-wrap">${tabs(lb)}<div class="lb-charts-grid" id="lb-charts"></div></div>`;
    grid.querySelectorAll('.lb-tab').forEach(btn => { btn.onclick = () => { activeLb = btn.dataset.lb; build(); }; });
    const container = document.getElementById('lb-charts');
    lb.benchmarks.forEach(bm => {
      const card = document.createElement('div');
      card.className = 'lb-chart-card';
      card.innerHTML = `<div class="lb-chart-title"><span class="lb-chart-name">${bm.name}</span><span class="lb-chart-task">${bm.task}</span></div><svg class="lb-chart-svg"></svg>`;
      container.appendChild(card);
      const svg = card.querySelector('svg');
      const W = card.clientWidth || 280, H = 180;
      const ml = 8, mr = 8, mt = 28, mb = 52;
      const w = W - ml - mr, h = H - mt - mb;
      const models = bm.models;
      const maxVal = Math.max(...models.map(m => m.score));
      const minVal = Math.min(...models.map(m => m.score));
      const yMin = Math.max(0, minVal - (maxVal - minVal) * 0.3);
      const x = d3.scaleBand().domain(models.map((_,i)=>i)).range([0,w]).padding(0.25);
      const y = d3.scaleLinear().domain([yMin, maxVal * 1.08]).range([h, 0]);
      const s = d3.select(svg).attr('width','100%').attr('height', H).attr('viewBox',`0 0 ${W} ${H}`);
      const g = s.append('g').attr('transform',`translate(${ml},${mt})`);
      [0.25,0.5,0.75,1].forEach(t => {
        const yv = yMin + (maxVal*1.08 - yMin)*t;
        g.append('line').attr('x1',0).attr('x2',w).attr('y1',y(yv)).attr('y2',y(yv)).attr('stroke','#30363d').attr('stroke-width',1);
        g.append('text').attr('x',-2).attr('y',y(yv)+3).attr('text-anchor','end').attr('font-size',8).attr('fill','#8b949e')
          .text(bm.unit==='%' ? Math.round(yv)+'%' : Math.round(yv));
      });
      models.forEach((m, i) => {
        const color = PROVIDER_COLORS[m.provider] || '#58a6ff';
        const bx = x(i), bw = x.bandwidth();
        const bar = g.append('rect').attr('x', bx).attr('y', h).attr('width', bw).attr('height', 0).attr('rx', 3).attr('fill', color).attr('opacity', 0.85);
        bar.transition().duration(500).delay(i*80).attr('y', y(m.score)).attr('height', h - y(m.score));
        g.append('text').attr('x', bx+bw/2).attr('y', y(m.score)-4).attr('text-anchor','middle').attr('font-size',9).attr('font-weight','700').attr('fill','#e6edf3')
          .attr('opacity',0).text(m.score + (bm.unit==='%'?'%':''))
          .transition().duration(400).delay(i*80+300).attr('opacity',1);
        g.append('text').attr('transform',`translate(${bx+bw/2},${h+6}) rotate(35)`).attr('text-anchor','start').attr('font-size',9).attr('fill','#8b949e')
          .text(m.model.length>14 ? m.model.slice(0,13)+'…' : m.model);
      });
    });
  }
  function buildLinks(lb) {
    grid.innerHTML = `<div class="lb-wrap">${tabs(lb)}<div class="lb-links">${renderLbLinks(lb)}</div></div>`;
    grid.querySelectorAll('.lb-tab').forEach(btn => { btn.onclick = () => { activeLb = btn.dataset.lb; build(); }; });
  }
  function build() {
    const lb = leaderboards[activeLb];
    if (lb.type === 'links') buildLinks(lb);
    else if (lb.type === 'charts') buildCharts(lb);
    else buildTable(lb);
  }
  build();
}

// Story link: real article -> "Read source"; ungrounded/demoted -> neutral
// "Source pending" affordance (the topic is kept, we just have no verified URL).
function sourceLinkHtml(url) {
  return url
    ? '<a class="card-link" href="' + url + '" target="_blank" rel="noopener">Read source →</a>'
    : '<span class="card-link card-link-pending" title="No verified source link yet">Source pending</span>';
}

function storyLinksHtml(links) {
  if (!links || !links.length) return '';
  function label(link) {
    const name = link.name || link.url || 'Link';
    const kind = link.kind || '';
    if (kind === 'github') return 'GitHub · ' + name;
    if (kind === 'x') return 'X · ' + name;
    if (kind === 'linkedin') return 'LinkedIn · ' + name;
    if (kind === 'huggingface') return 'HF · ' + name;
    if (kind === 'arxiv') return 'arXiv · ' + name;
    return name;
  }
  return '<div class="card-links">' + links.map(function (link, i) {
    const url = escHtml(link.url || '');
    if (!url) return '';
    const primary = i === 0 ? ' card-resource-link-primary' : '';
    return '<a class="card-resource-link' + primary + '" href="' + url + '" target="_blank" rel="noopener">' + escHtml(label(link)) + ' ↗</a>';
  }).join('') + '</div>';
}

// Minimal HTML escaping for values shown inside the provenance trace popover.
function escHtml(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Provenance affordance: a light "(i)" that, on click, reveals how a story
// entered the digest (its trace id + origin stage) so a mismatch between a
// claim and its cited source can be traced back. Hidden by default.
function provenanceHtml(story) {
  const rows = [['id', story.id], ['via', story.provenance || 'unknown'], ['source', story.source]];
  if (story.url) rows.push(['url', story.url]);
  if (story.carried_forward) rows.push(['carried', 'yes']);
  const items = rows.map(([k, v]) =>
    '<div class="trace-row"><span class="trace-k">' + k + '</span><code class="trace-v">' + escHtml(v) + '</code></div>'
  ).join('');
  return '<button type="button" class="card-info" title="Show provenance trace" aria-label="Show provenance trace">i</button>' +
    '<div class="card-trace" id="trace-' + escHtml(story.id) + '" hidden>' + items + '</div>';
}

// Shareable representations of a story for the clipboard: a rich-text HTML
// fragment (links + emphasis preserved) and a Markdown/plain-text fallback.
// Kept pure so it can be unit-tested without a DOM or a real clipboard.
function storyCopyFormats(story) {
  const title = String(story.title == null ? '' : story.title).trim();
  const summary = String(story.summary == null ? '' : story.summary).trim();
  const source = String(story.source == null ? '' : story.source).trim();
  const url = story.url ? String(story.url).trim() : '';
  const cat = String(story.catLabel || story.catId || '').trim();
  const tags = Array.isArray(story.tags) ? story.tags : [];
  const links = Array.isArray(story.links) ? story.links : [];

  const meta = [source, cat].filter(Boolean).join(' \u00b7 ');
  const tagLine = tags.length ? tags.map(t => '#' + String(t).trim().replace(/\s+/g, '')).join(' ') : '';
  const linkLines = links.filter(l => l && l.url).map(l => '- [' + (l.name || l.url) + '](' + l.url + ')');

  const md = [];
  md.push('## ' + title);
  if (meta) md.push('_' + meta + '_');
  if (summary) md.push(summary);
  if (linkLines.length) md.push(linkLines.join('\n'));
  if (tagLine) md.push(tagLine);
  if (url) md.push('[Read source \u2192](' + url + ')');
  const markdown = md.join('\n\n');

  const h = [];
  h.push('<h3>' + (url ? '<a href="' + escHtml(url) + '">' + escHtml(title) + '</a>' : escHtml(title)) + '</h3>');
  if (meta) h.push('<p><em>' + escHtml(meta) + '</em></p>');
  if (summary) h.push('<p>' + escHtml(summary) + '</p>');
  if (tagLine) h.push('<p>' + escHtml(tagLine) + '</p>');
  if (url) h.push('<p><a href="' + escHtml(url) + '">Read source \u2192</a></p>');
  const html = h.join('\n');

  return { markdown, html };
}

// Write both formats to the clipboard in one shot (rich-text editors take the
// HTML, plain editors take the Markdown), degrading to plain text where the
// async ClipboardItem API is unavailable. Gives brief visual feedback.
async function copyStory(story, btn) {
  const { markdown, html } = storyCopyFormats(story);
  let ok = false;
  try {
    if (navigator.clipboard && typeof ClipboardItem !== 'undefined') {
      await navigator.clipboard.write([new ClipboardItem({
        'text/html': new Blob([html], { type: 'text/html' }),
        'text/plain': new Blob([markdown], { type: 'text/plain' })
      })]);
      ok = true;
    } else if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(markdown);
      ok = true;
    }
  } catch (e) {
    try { await navigator.clipboard.writeText(markdown); ok = true; } catch (e2) { ok = false; }
  }
  if (btn) {
    btn.classList.remove('copied', 'copy-failed');
    btn.classList.add(ok ? 'copied' : 'copy-failed');
    btn.title = ok ? 'Copied!' : 'Copy failed';
    setTimeout(() => {
      btn.classList.remove('copied', 'copy-failed');
      btn.title = 'Copy story (rich text + Markdown)';
    }, 1400);
  }
  return ok;
}

// One-icon copy affordance in the card's top-right corner.
function copyButtonHtml() {
  return '<button type="button" class="card-copy" title="Copy story (rich text + Markdown)" aria-label="Copy story">' +
    '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<rect x="9" y="9" width="11" height="11" rx="2"></rect>' +
    '<path d="M5 15V5a2 2 0 0 1 2-2h10"></path></svg></button>';
}

function buildCard(story) {
  const color = CAT_COLORS[story.catId] || '#888';
  const div = document.createElement('div');
  div.className = 'story-card';
  div.id = 'card-' + story.id;
  const sigDots = Array.from({length:5},(_,i) => '<div class="sig-dot ' + (i < story.significance ? 'filled' : '') + '"></div>').join('');
  const tags = story.tags.map(t => '<span class="card-tag">' + t + '</span>').join('');
  div.innerHTML =
    '<div class="card-cat-stripe" style="background:' + color + '"></div>' +
    '<span class="card-cat-badge">' + story.catIcon + '</span>' +
    copyButtonHtml() +
    '<div class="card-meta"><span class="card-source">' + story.source + '</span>' + provenanceHtml(story) + '<div class="card-sig">' + sigDots + '</div></div>' +
    '<div class="card-title">' + story.title + '</div>' +
    '<div class="card-expand" id="expand-' + story.id + '">' +
      '<p class="card-summary">' + story.summary + '</p>' +
      storyLinksHtml(story.links) +
      '<div class="card-tags">' + tags + '</div>' +
      sourceLinkHtml(story.url) +
    '</div>';
  const info = div.querySelector('.card-info');
  if (info) info.onclick = (e) => {
    e.stopPropagation();
    const trace = div.querySelector('.card-trace');
    if (trace) trace.hidden = !trace.hidden;
  };
  const copyBtn = div.querySelector('.card-copy');
  if (copyBtn) copyBtn.onclick = (e) => {
    e.stopPropagation();
    copyStory(story, copyBtn);
  };
  div.onclick = () => toggleCard(story.id, div);
  return div;
}

function toggleCard(id, el) {
  const expand = document.getElementById('expand-' + id);
  const isExpanded = expand.classList.contains('visible');
  document.querySelectorAll('.card-expand.visible').forEach(e => e.classList.remove('visible'));
  document.querySelectorAll('.story-card.expanded').forEach(c => c.classList.remove('expanded'));
  if (!isExpanded) { expand.classList.add('visible'); el.classList.add('expanded'); }
}

function scrollToStory(id) {
  setFilter('all');
  setTimeout(() => {
    const el = document.getElementById('card-' + id);
    if (el) { el.scrollIntoView({ behavior:'smooth', block:'center' }); toggleCard(id, el); }
  }, 50);
}

function renderDonut(data) {
  const counts = data.visualizations.category_counts;
  const cats = data.categories.filter(c => counts[c.id] > 0);
  const w = 208, h = 160, r = 60;
  const svg = d3.select('#donut-chart').attr('width', w).attr('height', h);
  const g = svg.append('g').attr('transform', 'translate(' + (r+10) + ',' + (h/2) + ')');
  const pie = d3.pie().value(d => counts[d.id]).sort(null);
  const arc = d3.arc().innerRadius(r*0.55).outerRadius(r);
  const arcHover = d3.arc().innerRadius(r*0.55).outerRadius(r+5);
  const tooltip = document.getElementById('tooltip');
  const paths = g.selectAll('path').data(pie(cats)).enter().append('path')
    .attr('fill', d => CAT_COLORS[d.data.id])
    .attr('stroke', '#0d1117').attr('stroke-width', 2)
    .attr('d', arc).style('cursor','pointer')
    .on('mouseover', function(event, d) {
      d3.select(this).transition().duration(120).attr('d', arcHover);
      tooltip.style.opacity = '1';
      tooltip.innerHTML = d.data.icon + ' ' + d.data.label + ': <strong>' + counts[d.data.id] + '</strong>';
    })
    .on('mousemove', function(event) {
      tooltip.style.left = (event.clientX+12)+'px'; tooltip.style.top = (event.clientY-8)+'px';
    })
    .on('mouseout', function() {
      d3.select(this).transition().duration(120).attr('d', arc); tooltip.style.opacity = '0';
    })
    .on('click', (event, d) => setFilter(d.data.id));
  paths.transition().duration(600).attrTween('d', function(d) {
    const interp = d3.interpolate({startAngle:0,endAngle:0}, d);
    return t => arc(interp(t));
  });
  const legend = svg.append('g').attr('transform', 'translate(' + (r*2+18) + ',10)');
  cats.forEach((cat, i) => {
    legend.append('rect').attr('x',0).attr('y',i*18).attr('width',8).attr('height',8).attr('rx',2).attr('fill',CAT_COLORS[cat.id]);
    legend.append('text').attr('x',12).attr('y',i*18+8).attr('font-size','9').attr('fill','#8b949e')
      .text(cat.label.split(' ')[0] + ' (' + counts[cat.id] + ')');
  });
}

let _sigItems = [], _sigX, _sigG, _sigW;

function renderSigChart(data) {
  const dist = data.visualizations.significance_distribution;
  _sigItems = [5,4,3,2,1].map(k => ({ sig:k, count: dist[k]||0 })).filter(d => d.count > 0);
  const w=208, h=100, ml=24, mr=8, mt=4, mb=4;
  const svg = d3.select('#sig-chart').attr('width',w).attr('height',h);
  svg.selectAll('*').remove();
  if (!_sigItems.length) return;
  const max = d3.max(_sigItems, d => d.count);
  _sigW = w-ml-mr;
  const rowH = (h-mt-mb)/_sigItems.length;
  _sigG = svg.append('g').attr('transform','translate('+ml+','+mt+')');
  _sigX = d3.scaleLinear().domain([0,max]).range([0,_sigW]);
  _sigItems.forEach((d,i) => {
    const y = i*rowH+2, bh = rowH-6;
    const row = _sigG.append('g').attr('class','sig-row').style('cursor','pointer');
    row.append('text').attr('x',-4).attr('y',y+bh/2+4).attr('text-anchor','end').attr('font-size','9').attr('fill','#888').text('★'.repeat(d.sig));
    row.append('rect').attr('x',0).attr('y',y).attr('height',bh).attr('rx',2).attr('class','sig-bar')
      .attr('fill', d3.interpolateViridis(d.sig/5)).attr('width',0)
      .transition().duration(500).delay(i*80).attr('width', _sigX(d.count));
    row.append('text').attr('x',_sigX(d.count)+4).attr('y',y+bh/2+4).attr('font-size','9').attr('fill','#8b949e').attr('class','sig-count').text(d.count);
    row.append('rect').attr('x',-ml).attr('y',y-2).attr('width',w).attr('height',bh+4).attr('fill','transparent')
      .on('click', () => setSig(d.sig));
  });
}

function redrawSigChart() {
  if (!_sigG) return;
  _sigG.selectAll('.sig-row').each(function(_, i) {
    const d = _sigItems[i];
    const isActive = activeSig === d.sig;
    const inactive = activeSig !== null && !isActive;
    d3.select(this).select('.sig-bar').attr('opacity', inactive ? 0.25 : 1);
    d3.select(this).select('.sig-count').attr('fill', isActive ? '#e6edf3' : '#8b949e');
    d3.select(this).selectAll('text').filter((_, j) => j === 0).attr('fill', isActive ? '#e6edf3' : inactive ? '#555' : '#888');
  });
}

let _tagData = [];

function renderTagCloud(data) {
  _tagData = data.visualizations.top_tags.slice(0, 12);
  redrawTagCloud();
}

function redrawTagCloud() {
  const cloud = document.getElementById('tag-cloud');
  cloud.innerHTML = '';
  _tagData.forEach(t => {
    const span = document.createElement('span');
    const isActive = activeTag === t.tag;
    const inactive = activeTag !== null && !isActive;
    span.className = 'tag-item' + (isActive ? ' tag-active' : '') + (inactive ? ' tag-dim' : '');
    span.innerHTML = t.tag + '<span class="tag-count">' + t.count + '</span>';
    span.onclick = () => setTag(t.tag);
    cloud.appendChild(span);
  });
}


function resetDigestView() {
  document.getElementById('top-stories-bar').innerHTML = '<span class="top-stories-label">Top Stories</span>';
  document.getElementById('filter-bar').innerHTML = '';
  document.getElementById('story-grid').innerHTML = '';
  d3.select('#donut-chart').selectAll('*').remove();
  d3.select('#sig-chart').selectAll('*').remove();
  document.getElementById('tag-cloud').innerHTML = '';
  activeFilter = 'all';
  activeSig = null;
  activeTag = null;
  allStories = [];
  _sigG = null;
}

const SIDEBAR_WIDTH_KEY = 'aidigest.sidebarWidth';

function initLayoutResizer() {
  const layout = document.querySelector('.layout');
  const resizer = document.getElementById('layout-resizer');
  const sidebar = layout && layout.querySelector('.sidebar');
  if (!layout || !resizer || !sidebar || resizer.dataset.bound) return;
  resizer.dataset.bound = '1';

  const saved = parseInt(localStorage.getItem(SIDEBAR_WIDTH_KEY), 10);
  if (saved >= 160 && saved <= 420) layout.style.setProperty('--sidebar-w', saved + 'px');

  let startX = 0;
  let startW = 0;

  function applyWidth(w) {
    const clamped = Math.min(420, Math.max(160, w));
    layout.style.setProperty('--sidebar-w', clamped + 'px');
    return clamped;
  }

  function onMove(e) {
    applyWidth(startW + (e.clientX - startX));
  }

  function onUp() {
    resizer.classList.remove('dragging');
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    const w = parseInt(getComputedStyle(layout).getPropertyValue('--sidebar-w'), 10);
    if (!isNaN(w)) localStorage.setItem(SIDEBAR_WIDTH_KEY, String(w));
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onUp);
  }

  function onDown(e) {
    if (window.matchMedia('(max-width: 860px)').matches) return;
    e.preventDefault();
    startX = e.clientX;
    startW = sidebar.getBoundingClientRect().width;
    resizer.classList.add('dragging');
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }

  resizer.addEventListener('mousedown', onDown);
  resizer.addEventListener('keydown', e => {
    const step = e.shiftKey ? 40 : 12;
    const cur = sidebar.getBoundingClientRect().width;
    if (e.key === 'ArrowLeft') { e.preventDefault(); localStorage.setItem(SIDEBAR_WIDTH_KEY, String(applyWidth(cur - step))); }
    if (e.key === 'ArrowRight') { e.preventDefault(); localStorage.setItem(SIDEBAR_WIDTH_KEY, String(applyWidth(cur + step))); }
  });
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { PROVIDER_COLORS, CAT_COLORS, LB_GLOSSARY, lbTooltip, resolveLbColumns, renderLbLinks, sourceLinkHtml, provenanceHtml, escHtml, storyCopyFormats, reportSourceSealMarkup };
}
