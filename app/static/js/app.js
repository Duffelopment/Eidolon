const scanList = document.getElementById('scan-list');
const scanDetails = document.getElementById('scan-details');
const uploadForm = document.getElementById('upload-form');
const apiForm = document.getElementById('api-form');
const apiList = document.getElementById('api-list');
const svg = d3.select('#graph');
const graphContainer = document.getElementById('graph-container');

const width = graphContainer?.clientWidth || 600;
const height = 320;
svg.attr('viewBox', `0 0 ${width} ${height}`);

function renderScanList(scans) {
  scanList.innerHTML = '';
  scans.forEach((scan) => {
    const li = document.createElement('li');
    li.dataset.scanId = scan.id;
    li.innerHTML = `
      <strong>${scan.filename}</strong>
      <span class="badge ${badgeClass(scan.score)}">Score: ${scan.score}</span>
      <small>${new Date(scan.created_at).toLocaleString()}</small>
    `;
    li.addEventListener('click', () => selectScan(scan.id));
    scanList.appendChild(li);
  });
  if (scans.length) {
    selectScan(scans[0].id);
  } else {
    scanDetails.innerHTML = '<p>No scans yet. Upload a file to get started.</p>';
    clearGraph();
  }
}

function badgeClass(score) {
  if (score >= 12) return 'score-high';
  if (score >= 6) return 'score-medium';
  if (score > 0) return 'score-low';
  return 'score-clean';
}

function nodeColor(node) {
  switch (node.type) {
    case 'file':
      return '#536dff';
    case 'hash':
      return '#4db6ff';
    case 'finding':
      return '#ff8a65';
    case 'metadata':
      return '#9ccc65';
    default:
      return '#b0bec5';
  }
}

function nodeStroke(node) {
  switch (node.type) {
    case 'file':
      return '#aab4ff';
    case 'hash':
      return '#82b1ff';
    case 'finding':
      return '#ffab91';
    case 'metadata':
      return '#c5e1a5';
    default:
      return '#eceff1';
  }
}

function renderDetails(scan) {
  const findings = scan.findings || [];
  const findingsMarkup = findings.length
    ? `<ul>${findings
        .map(
          (f) => `
            <li>
              <strong>${f.severity}</strong> — ${f.name}
              ${f.category ? `<em> (${f.category})</em>` : ''}
              ${f.description ? `<p>${f.description}</p>` : ''}
            </li>
          `
        )
        .join('')}</ul>`
    : '<p>No heuristic findings recorded.</p>';

  scanDetails.innerHTML = `
    <table>
      <tr><th>File name</th><td>${scan.filename}</td></tr>
      <tr><th>Size</th><td>${(scan.size / 1024).toFixed(2)} KB</td></tr>
      <tr><th>MD5</th><td>${scan.md5}</td></tr>
      <tr><th>SHA1</th><td>${scan.sha1}</td></tr>
      <tr><th>SHA256</th><td>${scan.sha256}</td></tr>
      <tr><th>MIME</th><td>${scan.mime_type || 'Unknown'}</td></tr>
      <tr><th>Score</th><td>${scan.score}</td></tr>
      <tr><th>Summary</th><td>${scan.summary || 'Not available'}</td></tr>
    </table>
    <h3>Indicators</h3>
    ${findingsMarkup}
  `;
}

function clearGraph() {
  svg.selectAll('*').remove();
}

function renderGraph(graph) {
  clearGraph();
  const simulation = d3
    .forceSimulation(graph.nodes)
    .force('link', d3.forceLink(graph.links).id((d) => d.id).distance(110))
    .force('charge', d3.forceManyBody().strength(-240))
    .force('center', d3.forceCenter(width / 2, height / 2));

  const link = svg
    .append('g')
    .attr('stroke', 'rgba(130, 158, 255, 0.5)')
    .attr('stroke-width', 1.5)
    .selectAll('line')
    .data(graph.links)
    .enter()
    .append('line')
    .attr('class', 'link');

  const node = svg
    .append('g')
    .selectAll('g')
    .data(graph.nodes)
    .enter()
    .append('g')
    .attr('class', 'node')
    .call(
      d3
        .drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended)
    );

  node
    .append('circle')
    .attr('r', 18)
    .attr('fill', nodeColor)
    .attr('stroke', nodeStroke);

  node
    .append('text')
    .attr('text-anchor', 'middle')
    .attr('dy', 4)
    .text((d) => d.label);

  simulation.on('tick', () => {
    link
      .attr('x1', (d) => d.source.x)
      .attr('y1', (d) => d.source.y)
      .attr('x2', (d) => d.target.x)
      .attr('y2', (d) => d.target.y);

    node.attr('transform', (d) => `translate(${d.x}, ${d.y})`);
  });

  function dragstarted(event) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    event.subject.fx = event.subject.x;
    event.subject.fy = event.subject.y;
  }

  function dragged(event) {
    event.subject.fx = event.x;
    event.subject.fy = event.y;
  }

  function dragended(event) {
    if (!event.active) simulation.alphaTarget(0);
    event.subject.fx = null;
    event.subject.fy = null;
  }
}

async function selectScan(scanId) {
  try {
    const [scanRes, graphRes] = await Promise.all([
      fetch(`/api/scans/${scanId}`),
      fetch(`/api/scans/${scanId}/graph`),
    ]);
    if (!scanRes.ok) throw new Error('Unable to load scan');
    const scan = await scanRes.json();
    renderDetails(scan);

    if (graphRes.ok) {
      const graph = await graphRes.json();
      renderGraph(graph);
    } else {
      clearGraph();
    }
  } catch (error) {
    console.error(error);
  }
}

uploadForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const file = document.getElementById('file-input').files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch('/api/scans', {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) throw new Error('Scan failed');
    const newScan = await response.json();
    const current = await fetch('/api/scans').then((res) => res.json());
    renderScanList(current);
    selectScan(newScan.id);
    uploadForm.reset();
  } catch (error) {
    alert('Failed to scan file: ' + error.message);
  }
});

apiForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const formData = new FormData(apiForm);
  const payload = Object.fromEntries(formData.entries());
  try {
    const response = await fetch('/api/apis', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error('Unable to save endpoint');
    apiForm.reset();
    await refreshApiList();
  } catch (error) {
    alert(error.message);
  }
});

async function refreshApiList() {
  const apis = await fetch('/api/apis').then((res) => res.json());
  renderApiList(apis);
}

function renderApiList(apis) {
  apiList.innerHTML = '';
  apis.forEach((api) => {
    const li = document.createElement('li');
    li.dataset.apiId = api.id;
    li.innerHTML = `
      <div class="api-list__header">
        <strong>${api.name}</strong>
        <button class="api-calibrate" data-api-id="${api.id}">Calibrate</button>
      </div>
      <p class="muted">${api.base_url}</p>
      ${api.last_test_status ? `<p class="muted">Last calibration: ${api.last_test_status} at ${api.last_tested_at}</p>` : ''}
      ${api.last_test_notes ? `<pre>${api.last_test_notes}</pre>` : ''}
    `;
    li.querySelector('button').addEventListener('click', () => calibrateApi(api.id));
    apiList.appendChild(li);
  });
}

async function calibrateApi(apiId) {
  try {
    const response = await fetch(`/api/apis/${apiId}/calibrate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        request_template: {
          example_path: '/health',
          method: 'GET',
        },
      }),
    });
    if (!response.ok) throw new Error('Calibration failed');
    await refreshApiList();
  } catch (error) {
    alert(error.message);
  }
}

(async function init() {
  const scans = await fetch('/api/scans').then((res) => res.json());
  renderScanList(scans);
  await refreshApiList();
})();
