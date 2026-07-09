"""Diagnostics archive: index.json + frame index.html (mirrors reports layout)."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.paths import REPO_ROOT


def list_diagnostics_jsons(diag_dir: Path) -> list[Path]:
    return sorted(diag_dir.glob("*.diagnostics.json"), key=lambda p: p.stem)


def diagnostics_index_entry(
    data: dict[str, Any],
    stem: str,
    *,
    story_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    prefix = data.get("prefix") or stem.replace(".diagnostics", "")
    date = f"{prefix[0:4]}-{prefix[4:6]}-{prefix[6:8]}"
    try:
        display_date = datetime.strptime(date, "%Y-%m-%d").strftime("%b %d, %Y")
    except ValueError:
        display_date = date
    totals = data.get("totals") or {}
    llm = data.get("llm") or {}
    env = data.get("environment") or {}
    net = data.get("network") or {}
    gpu = env.get("gpu") or {}
    duration_ms = float(data.get("total_duration_ms") or 0)
    tokens = int(totals.get("total_tokens") or 0)
    story_count = None
    if story_counts and prefix in story_counts:
        story_count = story_counts[prefix]
    return {
        "prefix": prefix,
        "date": date,
        "display_date": display_date,
        "started_at": data.get("started_at"),
        "finished_at": data.get("finished_at"),
        "total_duration_ms": duration_ms,
        "total_duration_label": _ms_label(duration_ms),
        "total_tokens": tokens,
        "llm_call_count": totals.get("llm_call_count"),
        "llm_duration_ms": totals.get("llm_duration_ms"),
        "llm_share_pct": totals.get("llm_share_pct"),
        "model": llm.get("model"),
        "poc_id": data.get("poc_id"),
        "intensity": _intensity_score(duration_ms, tokens),
        "story_count": story_count,
        "platform_kind": env.get("platform_kind"),
        "cpu": env.get("cpu"),
        "gpu_name": gpu.get("name"),
        "ram_gb": env.get("ram_gb"),
        "vram_gb": gpu.get("vram_gb"),
        "net_mbps": net.get("throughput_mbps"),
        "hw_inferred": bool(env.get("inferred")),
        "report_source": data.get("report_source"),
        "report_source_label": data.get("report_source_label"),
        "report_source_badge": data.get("report_source_badge"),
    }


def _story_counts_by_prefix(cfg: dict[str, Any] | None, diag_dir: Path | None = None) -> dict[str, int]:
    """Join digest story counts onto diagnostics runs when reports are available."""
    candidates: list[Path] = []
    if diag_dir is not None:
        candidates.append(diag_dir.parent / "reports" / "index.json")
    if cfg is not None:
        try:
            from llm_pipeline.paths import reports_dir

            candidates.append(reports_dir(cfg) / "index.json")
        except (ImportError, OSError):
            pass
    candidates.append(REPO_ROOT / "app" / "reports" / "index.json")

    for index_path in candidates:
        if not index_path.is_file():
            continue
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
            return {
                entry["prefix"]: int(entry.get("story_count") or 0)
                for entry in index.get("digests", [])
                if entry.get("prefix")
            }
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
    return {}


def build_diagnostics_index(diag_dir: Path, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    from llm_pipeline.config import load_config
    from llm_pipeline.diagnostics import _enrich_report_paths

    if cfg is None:
        cfg = load_config()
    story_counts = _story_counts_by_prefix(cfg, diag_dir)
    entries: list[dict[str, Any]] = []
    by_date: dict[str, dict[str, Any]] = {}
    for path in list_diagnostics_jsons(diag_dir):
        raw = json.loads(path.read_text(encoding="utf-8"))
        prefix = raw.get("prefix") or path.stem.replace(".diagnostics", "")
        data = _enrich_report_paths(raw, cfg, prefix)
        from lib.report_source import enrich_diagnostics_with_source

        data = enrich_diagnostics_with_source(data, diag_dir)
        entry = diagnostics_index_entry(data, path.stem, story_counts=story_counts)
        entries.append(entry)
        prev = by_date.get(entry["date"])
        if not prev or entry["prefix"] > prev["prefix"]:
            by_date[entry["date"]] = entry
    entries.sort(key=lambda e: e["prefix"])
    latest = entries[-1]["prefix"] if entries else None
    return {
        "schema": "direct_pipeline_py.diagnostics_index/v1",
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latest": latest,
        "runs": entries,
        "by_date": list(by_date.values()),
    }


def rebuild_diagnostics_archive(diag_dir: Path, cfg: dict[str, Any] | None = None) -> Path:
    """Write index.json + index.html into the diagnostics output dir."""
    from llm_pipeline.config import load_config
    from llm_pipeline.frame_author import inject_author_card
    from llm_pipeline.frame_nav import admin_nav_enabled, inject_frame_nav
    from llm_pipeline.site_footer import inject_site_footer

    if cfg is None:
        cfg = load_config()

    diag_dir.mkdir(parents=True, exist_ok=True)
    index = build_diagnostics_index(diag_dir, cfg)
    index_path = diag_dir / "index.json"
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    frame_path = diag_dir / "index.html"
    frame_html = build_diagnostics_frame_html(index)
    frame_html = inject_author_card(frame_html, cfg)
    frame_html = inject_frame_nav(
        frame_html, "diagnostics", admin_available=admin_nav_enabled(cfg)
    )
    frame_html = inject_site_footer(frame_html, cfg)
    from llm_pipeline.frame_html import assert_archive_html_ready

    assert_archive_html_ready(frame_html)
    frame_path.write_text(frame_html, encoding="utf-8")
    print(f"  OK diagnostics archive {frame_path}")
    return frame_path


def _intensity_score(duration_ms: float, tokens: int) -> float:
    """0–1 score for heatmap coloring (duration-weighted, token boost)."""
    mins = max(duration_ms / 60_000, 0.1)
    dur_score = min(1.0, math.log10(mins) / 1.8)
    if tokens <= 0:
        return dur_score
    tok = max(tokens / 50_000, 0.1)
    return max(dur_score, min(1.0, math.log10(mins * tok) / 2.5))


def _ms_label(ms: float) -> str:
    if ms >= 60_000:
        return f"{ms / 60_000:.1f}m"
    if ms >= 1000:
        return f"{ms / 1000:.1f}s"
    return f"{ms:.0f}ms"


def _heat_color(intensity: float) -> str:
    if intensity >= 0.85:
        return "#58a6ff"
    if intensity >= 0.65:
        return "#1a6fa0"
    if intensity >= 0.45:
        return "#1a4a7a"
    if intensity >= 0.25:
        return "#1a3a5c"
    return "#21262d"


def build_diagnostics_frame_html(index: dict[str, Any]) -> str:
    from llm_pipeline.styles import frame_styles, heatmap_script, theme_script, trend_charts_script

    index_json = json.dumps(index, ensure_ascii=False)
    styles = frame_styles()
    theme_js = theme_script()
    heatmap_js = heatmap_script()
    trend_js = trend_charts_script()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pipeline Diagnostics</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<style>
{styles}
</style>
<script>{theme_js}</script>
</head>
<body class="diag-archive-frame">

<details class="archive-details" id="archive-details" open>
  <summary class="archive-summary">
    <span class="archive-title">Diagnostics Archive</span>
    <span class="archive-sub">Pipeline runs · click a day on the heatmap</span>
  </summary>
  <div class="archive-body">
    <div class="archive-charts-row">
      <div class="chart-panel">
        <div class="chart-panel-title">Run intensity</div>
        <div class="archive-header">
          <span class="archive-sub">Wall time · hover for tokens &amp; LLM stats</span>
        </div>
        <div id="heatmap-wrap"></div>
        <div class="archive-legend">
          <span class="hm-leg-label">Faster</span>
          <span class="hm-swatch hm-empty"></span>
          <span class="hm-swatch hm-1"></span>
          <span class="hm-swatch hm-2"></span>
          <span class="hm-swatch hm-3"></span>
          <span class="hm-swatch hm-4"></span>
          <span class="hm-leg-label">Slower</span>
        </div>
      </div>
      <div class="chart-panel">
        <div class="chart-panel-title">Topics vs runtime</div>
        <div id="perf-trend-wrap"></div>
      </div>
      __AUTHOR_CARD__
    </div>
    <div class="year-pills" id="year-pills"></div>
  </div>
</details>

<div class="panel-bar" id="panel-bar">
  <span>Select a run above</span>
</div>
<iframe class="diag-panel" id="diag-panel" title="Pipeline diagnostics detail"></iframe>
<div class="d3-tooltip" id="tooltip"></div>

<script>window.__DIAG_INDEX__ = {index_json};</script>
<script>{heatmap_js}</script>
<script>{trend_js}</script>
<script>
let currentPrefix = null;
let heatmapCells = {{}};
let heatmapYear = null;

function heatmapEntries(index) {{
  return index.by_date || index.runs || [];
}}

function sourceBadgeHtml(entry, colors) {{
  if (!entry || !entry.report_source_badge) return '';
  const label = entry.report_source_label || entry.report_source || '';
  return '<span style="display:inline-flex;align-items:center;gap:6px;margin-right:8px;vertical-align:middle">' +
    '<img src="' + entry.report_source_badge + '" alt="' + label + '" title="Produced by ' + label + '" ' +
    'style="height:24px;width:auto;border-radius:6px;border:1px solid rgba(255,255,255,0.12);background:#1e293b;padding:2px 6px" loading="lazy"></span>';
}}

function heatmapTooltipHtml(entry, colors) {{
  const badge = sourceBadgeHtml(entry, colors);
  return '<div style="display:flex;align-items:center;gap:8px;font-weight:700;margin-bottom:4px">' +
    badge + '<span>' + entry.display_date + '</span></div>' +
    '<div style="font-size:10px;color:' + colors.label + '">' + (entry.model || '') +
    (entry.report_source_label ? ' · ' + entry.report_source_label : '') + '</div>' +
    '<div style="font-size:10px;margin-top:4px">' + entry.total_duration_label + ' · ' +
    (entry.llm_call_count || 0) + ' calls · ' + ((entry.total_tokens || 0).toLocaleString()) + ' tok</div>' +
    (entry.story_count != null ? '<div style="font-size:10px;color:' + colors.label + ';margin-top:4px">' +
      entry.story_count + ' stories</div>' : '') +
    (entry.gpu_name ? '<div style="font-size:10px;color:' + colors.label + ';margin-top:4px">' +
      (entry.platform_kind || '') + ' · ' + entry.gpu_name +
      (entry.vram_gb ? ' · ' + entry.vram_gb + ' GB VRAM' : '') +
      (entry.ram_gb ? ' · ' + entry.ram_gb + ' GB RAM' : '') +
      (entry.hw_inferred ? ' (est.)' : '') + '</div>' : '') +
    (entry.net_mbps != null ? '<div style="font-size:10px;color:' + colors.label + '">Net ' +
      entry.net_mbps + ' Mbps</div>' : '');
}}

function yearsFromEntries(entries) {{
  const years = new Set();
  entries.forEach(e => {{ if (e.date) years.add(parseInt(e.date.slice(0, 4), 10)); }});
  years.add(new Date().getFullYear());
  return Array.from(years).sort((a, b) => a - b);
}}

function heatmapRange(viewYear, today) {{
  const start = new Date(viewYear, 0, 1);
  start.setDate(start.getDate() - start.getDay());
  let end;
  if (viewYear === today.getFullYear()) {{
    end = new Date(today);
    end.setDate(end.getDate() - end.getDay() + 6);
  }} else {{
    end = new Date(viewYear, 11, 31);
    end.setDate(end.getDate() - end.getDay() + 6);
  }}
  return {{ start, end }};
}}

function renderYearPills(entries, onYear) {{
  const bar = document.getElementById('year-pills');
  if (!bar) return;
  const years = yearsFromEntries(entries);
  bar.innerHTML = '';
  bar.style.display = 'flex';
  years.forEach(y => {{
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'year-pill' + (y === heatmapYear ? ' active' : '');
    btn.textContent = String(y);
    btn.onclick = () => {{ heatmapYear = y; onYear(y); }};
    bar.appendChild(btn);
  }});
}}

function syncYearPills() {{
  document.querySelectorAll('.year-pill').forEach(btn => {{
    btn.classList.toggle('active', parseInt(btn.textContent, 10) === heatmapYear);
  }});
}}

function ensureHeatmapYear(index, prefix) {{
  const entries = heatmapEntries(index);
  const years = yearsFromEntries(entries);
  if (prefix) {{
    const entry = entries.find(e => e.prefix === prefix);
    if (entry) {{
      heatmapYear = parseInt(entry.date.slice(0, 4), 10);
      return;
    }}
  }}
  if (!heatmapYear || !years.includes(heatmapYear)) {{
    heatmapYear = years[years.length - 1] || new Date().getFullYear();
  }}
}}

function syncDiagIframeTheme(iframe) {{
  if (!iframe) return;
  try {{
    const theme = localStorage.getItem('aidigest-theme') || 'dark';
    const value = theme === 'light' ? 'light' : 'dark';
    if (iframe.contentDocument && iframe.contentDocument.documentElement) {{
      iframe.contentDocument.documentElement.setAttribute('data-theme', value);
    }}
    if (iframe.contentWindow) {{
      iframe.contentWindow.postMessage({{ type: 'aidigest-theme', theme: value }}, '*');
    }}
  }} catch (e) {{}}
}}

function selectRun(prefix, opts) {{
  opts = opts || {{}};
  const entry = (window.__DIAG_INDEX__.runs || []).find(r => r.prefix === prefix);
  if (!entry || prefix === currentPrefix) return;
  currentPrefix = prefix;
  const iframe = document.getElementById('diag-panel');
  iframe.addEventListener('load', function onLoad() {{
    iframe.removeEventListener('load', onLoad);
    syncDiagIframeTheme(iframe);
  }});
  iframe.src = prefix + '.diagnostics.html';
  const bar = document.getElementById('panel-bar');
  bar.innerHTML = sourceBadgeHtml(entry, {{ label: '#8b949e' }}) +
    '<strong>' + entry.display_date + '</strong> · ' + entry.total_duration_label +
    ' · ' + (entry.llm_call_count || 0) + ' LLM calls · ' +
    ((entry.total_tokens || 0).toLocaleString()) + ' tokens · ' +
    '<a href="' + prefix + '.diagnostics.json" target="_blank" rel="noopener">JSON</a>';
  const index = window.__DIAG_INDEX__;
  const entryYear = parseInt(entry.date.slice(0, 4), 10);
  if (index && entryYear !== heatmapYear) {{
    heatmapYear = entryYear;
    renderHeatmap(index);
    syncYearPills();
  }}
  highlightHeatmap(prefix);
  document.title = 'Diagnostics | ' + entry.date;
  if (opts.updateHash !== false && location.hash !== '#' + prefix) {{
    history.replaceState(null, '', '#' + prefix);
  }}
}}

function initialPrefix(index) {{
  const hash = location.hash.replace(/^#/, '');
  if (hash && (index.runs || []).some(r => r.prefix === hash)) return hash;
  return index.latest || (index.runs || []).slice(-1)[0]?.prefix;
}}

function highlightHeatmap(prefix) {{
  const sel = (window.AIDigestHeatmap && window.AIDigestHeatmap.palette().selection) || '#58a6ff';
  Object.entries(heatmapCells).forEach(([p, cell]) => {{
    cell.attr('stroke', p === prefix ? sel : null).attr('stroke-width', p === prefix ? 2 : null);
  }});
}}

function renderHeatmap(index) {{
  const wrap = document.getElementById('heatmap-wrap');
  wrap.innerHTML = '';
  heatmapCells = {{}};
  const hm = window.AIDigestHeatmap;
  const colors = hm ? hm.palette() : {{ label: '#8b949e', empty: '#21262d' }};
  const byDate = {{}};
  (index.by_date || index.runs || []).forEach(d => {{ byDate[d.date] = d; }});
  const latest = (index.runs || []).slice(-1)[0];
  const today = latest ? new Date(latest.date + 'T12:00:00') : new Date();
  const viewYear = heatmapYear || today.getFullYear();
  const CELL = 13, GAP = 3, STEP = CELL + GAP;
  const DAY_LABELS = ['', 'Mon', '', 'Wed', '', 'Fri', ''];
  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const {{ start, end }} = heatmapRange(viewYear, today);
  const weeks = [];
  const cur = new Date(start);
  while (cur <= end) {{
    const week = [];
    for (let d = 0; d < 7; d++) {{ week.push(new Date(cur)); cur.setDate(cur.getDate() + 1); }}
    weeks.push(week);
  }}
  const W = weeks.length * STEP + 32, H = 7 * STEP + 24;
  const tooltip = document.getElementById('tooltip');
  const svg = d3.select(wrap).append('svg').attr('width', W).attr('height', H).style('overflow', 'visible');
  DAY_LABELS.forEach((lbl, i) => {{
    if (!lbl) return;
    svg.append('text').attr('x', 26).attr('y', 18 + i * STEP + CELL * 0.75).attr('text-anchor', 'end').attr('font-size', 9).attr('fill', colors.label).text(lbl);
  }});
  let lastMonth = -1;
  weeks.forEach((week, wi) => {{
    const mo = week[0].getMonth();
    if (mo !== lastMonth) {{
      lastMonth = mo;
      svg.append('text').attr('x', 30 + wi * STEP).attr('y', 10).attr('font-size', 9).attr('fill', colors.label).text(MONTHS[mo]);
    }}
  }});
  weeks.forEach((week, wi) => {{
    week.forEach((day, di) => {{
      const dateStr = day.toISOString().slice(0, 10);
      const entry = byDate[dateStr];
      const isFuture = day > today;
      let fill = colors.empty;
      if (entry && !isFuture) fill = hm ? hm.fillForIntensity(entry.intensity || 0) : fill;
      const x = 30 + wi * STEP, y = 18 + di * STEP;
      const cell = svg.append('rect').attr('x', x).attr('y', y).attr('width', CELL).attr('height', CELL).attr('rx', 2).attr('fill', fill)
        .style('cursor', entry ? 'pointer' : 'default');
      if (entry) {{
        heatmapCells[entry.prefix] = cell;
        cell.on('mouseover', function() {{
          if (entry.prefix !== currentPrefix) d3.select(this).attr('stroke', colors.hover).attr('stroke-width', 1);
          tooltip.style.opacity = '1';
          tooltip.innerHTML = heatmapTooltipHtml(entry, colors);
        }})
        .on('mousemove', function(event) {{ tooltip.style.left = (event.clientX + 14) + 'px'; tooltip.style.top = (event.clientY - 12) + 'px'; }})
        .on('mouseout', function() {{
          if (entry.prefix !== currentPrefix) d3.select(this).attr('stroke', null);
          tooltip.style.opacity = '0';
        }})
        .on('click', () => selectRun(entry.prefix));
      }}
    }});
  }});
}}

function init() {{
  const index = window.__DIAG_INDEX__;
  if (!index) throw new Error('Missing diagnostics index');
  const prefix = initialPrefix(index);
  ensureHeatmapYear(index, prefix);
  renderYearPills(heatmapEntries(index), () => {{
    renderHeatmap(index);
    highlightHeatmap(currentPrefix);
    syncYearPills();
  }});
  renderHeatmap(index);
  if (window.AIDigestTrends) {{
    window.AIDigestTrends.renderPerfTrend('perf-trend-wrap', index.runs || [], 'tooltip');
  }}
  if (prefix) selectRun(prefix);
  document.addEventListener('aidigest-theme-change', () => {{
    renderHeatmap(index);
    highlightHeatmap(currentPrefix);
    syncDiagIframeTheme(document.getElementById('diag-panel'));
  }});
  window.addEventListener('hashchange', () => {{
    const p = location.hash.replace(/^#/, '');
    if (p && p !== currentPrefix && (index.runs || []).some(r => r.prefix === p)) {{
      selectRun(p, {{ updateHash: false }});
    }}
  }});
}}

init().catch(err => {{
  document.body.insertAdjacentHTML('beforeend', '<div class="frame-error">' + err.message + '</div>');
}});
</script>
</body>
</html>"""
