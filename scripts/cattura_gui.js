// Screenshot della GUI ShadowBroker per la documentazione.
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1600, height: 900 } });
  await p.goto('http://127.0.0.1:3000', { waitUntil: 'networkidle', timeout: 120000 });
  await p.waitForTimeout(25000);   // la mappa deve caricare le tessere e i layer
  await p.screenshot({ path: 'd:/assistenteeee/odysseus/docs/immagini/shadowbroker-gui.png' });
  console.log('catturato');
  await b.close();
})();
