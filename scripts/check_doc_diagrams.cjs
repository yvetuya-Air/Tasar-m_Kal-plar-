// Gerçek Mermaid kaynaklarını yerel Chromium içinde çizerek doğrular.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require('../.ui-tools/node_modules/playwright');

(async () => {
  const root = path.resolve(__dirname, '..');
  const stage = Number(process.env.DOC_AUDIT_STAGE || 11);
  assert.ok(Number.isInteger(stage) && stage > 0);
  const distribution = path.join(root, '.test-tmp/docs11-diagrams/node_modules/mermaid/dist');
  assert.ok(fs.existsSync(distribution), 'Mermaid geçici doğrulama paketi kurulmalıdır.');
  const executablePath = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(fs.existsSync);
  const browser = await chromium.launch({ executablePath, headless: true });
  const results = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
    await page.route('http://diagram.local/**', async route => {
      const pathname = new URL(route.request().url()).pathname;
      if (pathname === '/') return route.fulfill({ contentType: 'text/html', body: '<!doctype html><html lang="tr"><body><main id="chart"></main></body></html>' });
      const filename = path.resolve(distribution, '.' + pathname);
      if (!filename.startsWith(distribution + path.sep) || !fs.existsSync(filename)) return route.fulfill({ status: 404, body: '' });
      await route.fulfill({ contentType: 'text/javascript', body: fs.readFileSync(filename) });
    });
    await page.goto('http://diagram.local/');
    await page.evaluate(async () => {
      const { default: mermaid } = await import('/mermaid.esm.min.mjs');
      window.mermaid = mermaid;
      mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'default' });
    });
    const cases = ['factory', 'adapter', 'strategy', 'observer', 'er'].map(name => ({ name, source: fs.readFileSync(path.join(root, 'docs/diagrams', name + '.mmd'), 'utf8') }));
    const architecture = fs.readFileSync(path.join(root, 'docs/MIMARI.md'), 'utf8');
    let extra = 0;
    for (const match of architecture.matchAll(/```mermaid\s*\n([\s\S]*?)```/g)) {
      if (!match[1].trim().startsWith('erDiagram')) cases.push({ name: 'architecture-' + (++extra), source: match[1] });
    }
    for (const { name, source } of cases) {
      try {
        const dimensions = await page.evaluate(async ({ source, name }) => {
          await window.mermaid.parse(source);
          const { svg } = await window.mermaid.render('diagram-' + name, source);
          document.getElementById('chart').innerHTML = svg;
          const element = document.querySelector('#chart svg');
          return { viewBox: element.getAttribute('viewBox'), labels: element.querySelectorAll('text, foreignObject').length };
        }, { source, name });
        assert.ok(dimensions.labels > 0);
        assert.ok(dimensions.viewBox);
        await page.locator('#chart').screenshot({ path: path.join(root, '.test-tmp', 'docs' + stage + '-' + name + '.png') });
        results.push({ name, status: 'passed', ...dimensions });
      } catch (error) {
        results.push({ name, status: 'failed', error: error.message });
      }
    }
  } finally {
    await browser.close();
  }
  const report = { executed_at: new Date().toISOString(), status: results.every(item => item.status === 'passed') ? 'passed' : 'failed', diagrams: results };
  fs.writeFileSync(path.join(root, 'docs/audit', 'diagrams-stage' + stage + '.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report));
  if (report.status !== 'passed') process.exitCode = 1;
})().catch(error => { console.error(error); process.exitCode = 1; });
