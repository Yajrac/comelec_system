(() => {
  const node = document.getElementById('dashboardChartData');
  if (!node) return;
  const message = document.getElementById('chartLoadMessage');
  if (typeof Chart === 'undefined') {
    message.textContent = 'Charts could not load. Totals remain available in the summary cards and tables.';
    return;
  }
  const data = JSON.parse(node.textContent);
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  Chart.defaults.font.family = "'Segoe UI', sans-serif";
  Chart.defaults.color = '#718096';
  const noData = { id: 'dashboardEmpty', afterDraw(chart) {
    if (chart.data.datasets.some(dataset => dataset.data.some(value => Number(value) > 0))) return;
    const { ctx, chartArea } = chart;
    if (!chartArea) return;
    ctx.save(); ctx.fillStyle = '#718096'; ctx.font = '12px Segoe UI';
    ctx.textAlign = 'center'; ctx.fillText('No records yet', (chartArea.left + chartArea.right) / 2, (chartArea.top + chartArea.bottom) / 2); ctx.restore();
  }};
  const sum = values => values.reduce((total, value) => total + Number(value), 0);
  const format = value => Number(value).toLocaleString();
  const percent = (value, total) => total ? `${(Number(value) * 100 / total).toFixed(1)}%` : '0%';
  const tooltip = total => ({ backgroundColor: '#142b54', titleColor: '#fff', bodyColor: '#dbe6fa', padding: 12, cornerRadius: 9, displayColors: true, boxPadding: 5,
    callbacks: { label: context => ` ${format(context.raw)} applications (${percent(context.raw, total)})` } });
  const base = { responsive: true, maintainAspectRatio: false, animation: reducedMotion ? false : { duration: 500 }, interaction: { mode: 'nearest', intersect: true }, plugins: { legend: { display: false } } };
  const numericAxis = { beginAtZero: true, ticks: { precision: 0, font: { size: 10 }, maxTicksLimit: 5 }, border: { display: false }, grid: { color: '#f0f3f8', drawTicks: false } };
  const labelAxis = { grid: { display: false }, border: { display: false }, ticks: { font: { size: 11 }, padding: 10, autoSkip: false } };
  const typeColors = ['#ff9a4b', '#37d4da', '#8175ff', '#f33c8e', '#e7c65a'];
  const typeLabels = data.types.labels.map(label => label === 'Update Information' ? 'Update / Correction' : label);
  new Chart(document.getElementById('dashboardTypeChart'), {
    type: 'bar', data: { labels: typeLabels, datasets: [{ label: 'Applications', data: data.types.values, backgroundColor: typeColors, borderRadius: { topLeft: 6, topRight: 6 }, maxBarThickness: 42, categoryPercentage: .65, barPercentage: .85 }] },
    options: { ...base, plugins: { ...base.plugins, tooltip: { ...tooltip(sum(data.types.values)), callbacks: { label: context => ` ${format(context.raw)} applications (${percent(context.raw, sum(data.types.values))} of all applications)` } } }, scales: {
      y: { ...numericAxis, ticks: { ...numericAxis.ticks, color: '#718096' }, grid: { color: '#edf1f7', drawTicks: false } },
      x: { border: { display: false }, grid: { display: false }, ticks: { color: '#526783', font: { size: 9 }, maxRotation: 0, autoSkip: false, callback(value) { return [['New','Registration'],['Update /','Correction'],'Transfer','Reactivation','Reinstatement'][value]; } } },
    } },
  });
  const breakdown = document.getElementById('typeChartBreakdown');
  typeLabels.forEach((label, typeIndex) => {
    const group = document.createElement('div'); group.className = 'type-breakdown-item';
    const heading = document.createElement('strong'); heading.textContent = label;
    const count = document.createElement('b'); count.textContent = format(data.types.values[typeIndex]);
    const caption = document.createElement('small'); caption.textContent = 'Total applications';
    group.append(heading, count, caption); breakdown.append(group);
  });
  const statusTotal = sum(data.statuses.values);
  const donutCenter = { id: 'statusTotal', afterDraw(chart) {
    const { ctx, chartArea } = chart;
    if (!chartArea) return;
    const x = (chartArea.left + chartArea.right) / 2;
    const y = (chartArea.top + chartArea.bottom) / 2;
    ctx.save(); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillStyle = '#142b54'; ctx.font = '700 30px Segoe UI'; ctx.fillText(format(statusTotal), x, y - 9);
    ctx.fillStyle = '#8a99ae'; ctx.font = '10px Segoe UI'; ctx.fillText(statusTotal ? 'TOTAL APPLICATIONS' : 'NO RECORDS YET', x, y + 20); ctx.restore();
  }};
  new Chart(document.getElementById('dashboardStatusChart'), {
    type: 'doughnut', data: { labels: data.statuses.labels, datasets: [{ data: data.statuses.values, backgroundColor: ['#e6b84c','#9674cd','#56a87f','#d77b71'], borderWidth: 0, spacing: 5, borderRadius: 6, hoverOffset: 6 }] },
    options: { ...base, cutout: '79%', layout: { padding: 8 }, plugins: { ...base.plugins, tooltip: tooltip(statusTotal) } }, plugins: [donutCenter],
  });
  document.querySelectorAll('.analytics-status-legend > span').forEach((item, index) => {
    const percentage = document.createElement('small'); percentage.className = 'legend-percentage';
    percentage.textContent = percent(data.statuses.values[index], statusTotal); item.append(percentage);
  });
  const allLabels = data.barangays.labels;
  const allValues = data.barangays.values;
  const ranking = document.getElementById('barangayRanking');
  const toggle = document.getElementById('barangayChartToggle');
  const caption = document.getElementById('barangayChartCaption');
  const notice = document.getElementById('barangayUnassigned');
  const assigned = allLabels.map((name, index) => ({ name, count: Number(allValues[index]) })).filter(item => item.name !== 'Unassigned');
  const unassignedIndex = allLabels.indexOf('Unassigned');
  const unassigned = unassignedIndex === -1 ? 0 : Number(allValues[unassignedIndex]);
  if (unassigned) {
    notice.hidden = false;
    notice.textContent = `${format(unassigned)} applicant${unassigned === 1 ? ' has' : 's have'} no assigned barangay.`;
  }
  let expanded = false;
  function renderRanking() {
    const visible = expanded ? assigned : assigned.slice(0, 5);
    ranking.replaceChildren();
    if (!assigned.length) {
      const empty = document.createElement('p'); empty.className = 'barangay-ranking-empty';
      empty.textContent = 'No barangays registered yet. Add a barangay to display its applicant count.'; ranking.append(empty);
    }
    const maximum = Math.max(1, ...assigned.map(item => item.count));
    visible.forEach((item, index) => {
      const row = document.createElement('li'); row.className = 'barangay-rank-row';
      const rank = document.createElement('span'); rank.className = 'barangay-rank-number'; rank.textContent = String(index + 1).padStart(2, '0');
      const name = document.createElement('span'); name.className = 'barangay-rank-name'; name.textContent = item.name;
      const track = document.createElement('span'); track.className = 'barangay-rank-track'; track.setAttribute('aria-hidden', 'true');
      const bar = document.createElement('span'); bar.className = 'barangay-rank-fill'; bar.style.width = `${item.count / maximum * 100}%`; track.append(bar);
      const count = document.createElement('strong'); count.className = 'barangay-rank-count'; count.textContent = format(item.count);
      const accessible = document.createElement('span'); accessible.className = 'visually-hidden'; accessible.textContent = ' applicants'; count.append(accessible);
      row.append(rank, name, track, count); ranking.append(row);
    });
    caption.textContent = assigned.length ? `Showing ${visible.length} of ${assigned.length} registered barangays, including those with 0 applicants.` : 'Barangay rankings will appear as records are assigned.';
    toggle.hidden = assigned.length <= 5;
    toggle.textContent = expanded ? 'Show top 5' : 'View all barangays';
    toggle.setAttribute('aria-expanded', String(expanded));
  }
  toggle.addEventListener('click', () => { expanded = !expanded; renderRanking(); });
  renderRanking();
  const trendsCanvas = document.getElementById('dashboardTrendsChart');
  if (trendsCanvas && data.trends) new Chart(trendsCanvas, {
    type: 'line', data: { labels: data.trends.labels, datasets: [{ label: 'Applications', data: data.trends.values,
      borderColor: '#073ba8', backgroundColor: '#073ba812', fill: true, tension: .25, pointRadius: 3, pointHoverRadius: 5, borderWidth: 2 }] },
    options: { ...base, scales: { y: numericAxis, x: { ...labelAxis, ticks: { font: { size: 10 }, maxRotation: 30 } } } }, plugins: [noData],
  });
  const ageCanvas = document.getElementById('dashboardAgeChart');
  const barCounts = { id: 'ageCounts', afterDatasetsDraw(chart) {
    const { ctx } = chart;
    ctx.save(); ctx.font = '600 11px Segoe UI'; ctx.fillStyle = '#526783'; ctx.textBaseline = 'middle';
    chart.getDatasetMeta(0).data.forEach((bar, index) => {
      ctx.fillText(format(chart.data.datasets[0].data[index]), bar.x + 8, bar.y);
    });
    ctx.restore();
  } };
  if (ageCanvas && data.age) new Chart(ageCanvas, {
    type: 'bar', data: { labels: data.age.labels, datasets: [{ label: 'Applicants', data: data.age.values,
      backgroundColor: '#8f7bc5', hoverBackgroundColor: '#7356b2', borderRadius: 5, maxBarThickness: 19 }] },
    options: { ...base, indexAxis: 'y', layout: { padding: { right: 30 } },
      scales: { x: { ...numericAxis, suggestedMax: Math.max(2, ...data.age.values) }, y: labelAxis } }, plugins: [barCounts],
  });
  [['sex', 'dashboardSexChart', 'sexDemographicLegend', ['#7399df', '#ad91d5', '#cbd5e1']],
   ['pwd', 'dashboardPwdChart', 'pwdDemographicLegend', ['#e4b65b', '#56a87f', '#cbd5e1']]].forEach(([key, id, legendId, colors]) => {
    const canvas = document.getElementById(id);
    if (!canvas || !data[key]) return;
    const total = sum(data[key].values);
    const center = { id: 'demographicTotal', afterDraw(chart) {
      const { ctx, chartArea } = chart;
      if (!chartArea) return;
      const x = (chartArea.left + chartArea.right) / 2, y = (chartArea.top + chartArea.bottom) / 2;
      ctx.save(); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillStyle = '#142b54'; ctx.font = '700 28px Segoe UI'; ctx.fillText(format(total), x, y - 7);
      ctx.fillStyle = '#8a99ae'; ctx.font = '10px Segoe UI'; ctx.fillText(total ? 'APPLICANTS' : 'NO RECORDS YET', x, y + 17); ctx.restore();
    } };
    new Chart(canvas, { type: 'doughnut', data: { labels: data[key].labels, datasets: [{
      data: total ? data[key].values : data[key].values.map((_, index) => index === 0 ? 1 : 0),
      backgroundColor: total ? colors : ['#edf1f7', '#edf1f7', '#edf1f7'], borderWidth: 0,
      spacing: total ? 3 : 0, borderRadius: total ? 4 : 0, hoverOffset: total ? 4 : 0 }] },
      options: { ...base, cutout: '78%', layout: { padding: 8 }, plugins: { ...base.plugins,
        tooltip: { enabled: total > 0, callbacks: { label: context => ` ${format(context.raw)} applicants (${percent(context.raw, total)})` } } } }, plugins: [center],
    });
    const legend = document.getElementById(legendId);
    if (!legend) return;
    data[key].labels.forEach((label, index) => {
      const row = document.createElement('li');
      const dot = document.createElement('i'); dot.style.backgroundColor = colors[index]; dot.setAttribute('aria-hidden', 'true');
      const name = document.createElement('span'); name.textContent = label;
      const count = document.createElement('strong'); count.textContent = format(data[key].values[index]);
      const share = document.createElement('small'); share.textContent = percent(data[key].values[index], total);
      row.append(dot, name, count, share); legend.append(row);
    });
  });
})();
