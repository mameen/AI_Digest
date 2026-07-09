(function (global) {
  var CAT_COLORS = {
    leaderboard: '#F39C12', analytics: '#6366F1', aisearch: '#F0883E', 'agentic-ai': '#0EA5E9',
    llm: '#388bfd', rag: '#10B981', 'image-gen': '#8E44AD', 'design-ai': '#16A085',
    typography: '#C0392B', robotics: '#E67E22', research: '#2980B9'
  };
  var CAT_ORDER = [
    'aisearch', 'leaderboard', 'research', 'analytics', 'agentic-ai', 'llm',
    'rag', 'image-gen', 'design-ai', 'typography', 'robotics'
  ];

  function weekStart(dateStr) {
    var d = new Date(dateStr + 'T12:00:00');
    var day = d.getDay();
    d.setDate(d.getDate() - day);
    return d.toISOString().slice(0, 10);
  }

  function weekLabel(iso) {
    var d = new Date(iso + 'T12:00:00');
    return 'W' + String(Math.ceil((d.getDate()) / 7)).padStart(2, '0') + ' ' +
      d.toLocaleString('en-US', { month: 'short', day: 'numeric' });
  }

  function resolveTooltip(tooltipEl) {
    if (!tooltipEl) return null;
    if (typeof tooltipEl === 'string') {
      var id = tooltipEl.replace(/^#/, '');
      var node = document.getElementById(id);
      return node ? global.d3.select(node) : null;
    }
    return global.d3.select(tooltipEl);
  }

  function showTooltip(tooltip, event, html) {
    if (!tooltip) return;
    tooltip.style('opacity', 1).html(html);
    tooltip.style('left', (event.clientX + 14) + 'px').style('top', (event.clientY - 12) + 'px');
  }

  function hideTooltip(tooltip) {
    if (tooltip) tooltip.style('opacity', 0);
  }

  function perfTooltipHtml(d) {
    var mins = (d.total_duration_ms / 60000).toFixed(1);
    var lines = [
      '<div style="font-weight:700;margin-bottom:4px">' + (d.display_date || d.date) + '</div>',
      '<div style="font-size:10px;color:var(--muted)">' + (d.model || 'unknown model') + '</div>',
      '<div style="font-size:10px;margin-top:6px">' + d.story_count + ' topics · ' +
        (d.total_duration_label || mins + 'm') + '</div>',
      '<div style="font-size:10px;color:var(--muted);margin-top:4px">' +
        (d.llm_call_count || 0) + ' LLM calls · ' +
        ((d.total_tokens || 0).toLocaleString()) + ' tokens</div>'
    ];
    if (d.platform_kind) {
      lines.push(
        '<div style="font-size:10px;color:var(--muted);margin-top:4px">Platform: ' +
          d.platform_kind + '</div>'
      );
    }
    return lines.join('');
  }

  function aggregateWeeklyDigests(digests) {
    var weeks = {};
    (digests || []).forEach(function (entry) {
      if (!entry || !entry.date) return;
      var key = weekStart(entry.date);
      if (!weeks[key]) {
        weeks[key] = { week: key, label: weekLabel(key), categories: {}, story_count: 0 };
      }
      var bucket = weeks[key];
      if (entry.prefix > (bucket.prefix || '')) {
        bucket.prefix = entry.prefix;
        bucket.story_count = entry.story_count || 0;
        bucket.categories = Object.assign({}, entry.categories || {});
      }
    });
    return Object.keys(weeks).sort().map(function (k) { return weeks[k]; });
  }

  function renderTopicTrend(wrapId, digests, tooltipEl) {
    var wrap = document.getElementById(wrapId);
    if (!wrap || !global.d3) return;
    wrap.innerHTML = '';
    var rows = aggregateWeeklyDigests(digests);
    if (!rows.length) {
      wrap.innerHTML = '<div style="font-size:11px;color:var(--muted)">No weekly data yet</div>';
      return;
    }

    var cats = CAT_ORDER.filter(function (c) {
      return rows.some(function (r) { return (r.categories || {})[c]; });
    });
    if (!cats.length) cats = CAT_ORDER.slice(0, 6);

    var margin = { top: 8, right: 8, bottom: 48, left: 36 };
    var barW = 22;
    var width = Math.max(260, rows.length * (barW + 8) + margin.left + margin.right);
    var height = 150;

    var svg = global.d3.select(wrap).append('svg').attr('width', width).attr('height', height);
    var g = svg.append('g').attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    var x = global.d3.scaleBand()
      .domain(rows.map(function (r) { return r.week; }))
      .range([0, width - margin.left - margin.right])
      .padding(0.18);

    var maxTotal = global.d3.max(rows, function (r) {
      return global.d3.sum(cats, function (c) { return (r.categories || {})[c] || 0; });
    }) || 1;

    var y = global.d3.scaleLinear().domain([0, maxTotal]).range([height - margin.top - margin.bottom, 0]);

    var stack = global.d3.stack().keys(cats).value(function (d, key) {
      return (d.categories || {})[key] || 0;
    });

    var series = stack(rows);
    var tooltip = resolveTooltip(tooltipEl);

    g.selectAll('g.layer').data(series).join('g')
      .attr('class', 'layer')
      .attr('fill', function (d) { return CAT_COLORS[d.key] || '#888'; })
      .selectAll('rect').data(function (d) { return d; }).join('rect')
      .attr('x', function (d) { return x(d.data.week); })
      .attr('y', function (d) { return y(d[1]); })
      .attr('height', function (d) { return Math.max(0, y(d[0]) - y(d[1])); })
      .attr('width', x.bandwidth())
      .on('mouseover', function (event, d) {
        showTooltip(tooltip, event,
          '<div style="font-weight:700">' + d.data.label + '</div>' +
          '<div style="font-size:10px;margin-top:4px">' + d.data.story_count + ' stories</div>'
        );
      })
      .on('mousemove', function (event) {
        if (!tooltip) return;
        tooltip.style('left', (event.clientX + 14) + 'px').style('top', (event.clientY - 12) + 'px');
      })
      .on('mouseout', function () { hideTooltip(tooltip); });

    g.append('g')
      .attr('transform', 'translate(0,' + (height - margin.top - margin.bottom) + ')')
      .call(global.d3.axisBottom(x).tickFormat(function (w) {
        var row = rows.find(function (r) { return r.week === w; });
        return row ? row.label.split(' ').slice(0, 2).join(' ') : w.slice(5);
      }))
      .selectAll('text')
      .attr('font-size', 9)
      .attr('fill', 'var(--muted)')
      .attr('transform', 'rotate(-45)')
      .style('text-anchor', 'end')
      .attr('dx', '-0.35em')
      .attr('dy', '0.35em');

    g.append('g').call(global.d3.axisLeft(y).ticks(4).tickFormat(global.d3.format('d')))
      .selectAll('text').attr('font-size', 9).attr('fill', 'var(--muted)');

    return { categories: cats, colors: CAT_COLORS };
  }

  function renderPerfTrend(wrapId, runs, tooltipEl) {
    var wrap = document.getElementById(wrapId);
    if (!wrap || !global.d3) return;
    wrap.innerHTML = '';
    var points = (runs || []).filter(function (r) {
      return r && r.total_duration_ms != null && r.story_count != null;
    });
    if (points.length < 2) {
      wrap.innerHTML = '<div style="font-size:11px;color:var(--muted)">Need 2+ runs with story counts</div>';
      return;
    }

    var margin = { top: 10, right: 12, bottom: 32, left: 44 };
    var width = Math.max(260, 280);
    var height = 150;
    var svg = global.d3.select(wrap).append('svg').attr('width', width).attr('height', height);
    var g = svg.append('g').attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    var x = global.d3.scaleLinear()
      .domain(global.d3.extent(points, function (d) { return d.story_count; }))
      .nice()
      .range([0, width - margin.left - margin.right]);
    var y = global.d3.scaleLinear()
      .domain(global.d3.extent(points, function (d) { return d.total_duration_ms / 60000; }))
      .nice()
      .range([height - margin.top - margin.bottom, 0]);

    var tooltip = resolveTooltip(tooltipEl);

    g.selectAll('circle').data(points).join('circle')
      .attr('cx', function (d) { return x(d.story_count); })
      .attr('cy', function (d) { return y(d.total_duration_ms / 60000); })
      .attr('r', 5)
      .attr('fill', '#58a6ff')
      .attr('opacity', 0.85)
      .style('cursor', 'pointer')
      .on('mouseover', function (event, d) {
        global.d3.select(this).attr('r', 7).attr('opacity', 1);
        showTooltip(tooltip, event, perfTooltipHtml(d));
      })
      .on('mousemove', function (event) {
        if (!tooltip) return;
        tooltip.style('left', (event.clientX + 14) + 'px').style('top', (event.clientY - 12) + 'px');
      })
      .on('mouseout', function () {
        global.d3.select(this).attr('r', 5).attr('opacity', 0.85);
        hideTooltip(tooltip);
      });

    g.append('g')
      .attr('transform', 'translate(0,' + (height - margin.top - margin.bottom) + ')')
      .call(global.d3.axisBottom(x).ticks(5))
      .selectAll('text').attr('font-size', 9).attr('fill', 'var(--muted)');
    g.append('text')
      .attr('x', (width - margin.left - margin.right) / 2)
      .attr('y', height - margin.top - 6)
      .attr('text-anchor', 'middle')
      .attr('font-size', 9)
      .attr('fill', 'var(--muted)')
      .text('Topics');

    g.append('g').call(global.d3.axisLeft(y).ticks(4))
      .selectAll('text').attr('font-size', 9).attr('fill', 'var(--muted)');
    g.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('x', -(height - margin.top - margin.bottom) / 2)
      .attr('y', -34)
      .attr('text-anchor', 'middle')
      .attr('font-size', 9)
      .attr('fill', 'var(--muted)')
      .text('Minutes');
  }

  function renderTrendLegend(containerId, categories) {
    var el = document.getElementById(containerId);
    if (!el || !categories || !categories.length) return;
    el.innerHTML = categories.map(function (c) {
      return '<span class="trend-legend-item"><span class="trend-legend-swatch" style="background:' +
        (CAT_COLORS[c] || '#888') + '"></span>' + c + '</span>';
    }).join('');
  }

  var api = {
    CAT_COLORS: CAT_COLORS,
    aggregateWeeklyDigests: aggregateWeeklyDigests,
    renderTopicTrend: renderTopicTrend,
    renderPerfTrend: renderPerfTrend,
    renderTrendLegend: renderTrendLegend
  };

  global.AIDigestTrends = api;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
})(typeof window !== 'undefined' ? window : globalThis);
