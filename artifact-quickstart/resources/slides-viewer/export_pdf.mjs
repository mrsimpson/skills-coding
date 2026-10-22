// Exportiert ein mit build_standalone.py gebautes Deck als PDF, eine Seite je Folie.
//
//   node export_pdf.mjs <deck.html> <ausgabe.pdf>
//
// Braucht Playwright (`npm i playwright`) und einen installierten Chromium.
// Ohne Playwright geht derselbe Weg im Browser: <deck.html>?print-pdf öffnen,
// Drucken, Ziel "Als PDF speichern", Ränder "Keine", Hintergrundgrafiken an.
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

const { chromium } = createRequire(import.meta.url)('playwright');
const [, , input, output] = process.argv;
if (!input || !output) {
  console.error('Aufruf: node export_pdf.mjs <deck.html> <ausgabe.pdf>');
  process.exit(2);
}

const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto(pathToFileURL(resolve(input)).href + '?print-pdf', { waitUntil: 'load' });
  await page.waitForSelector('html.reveal-print .pdf-page, html.print-pdf .pdf-page', { timeout: 15000 });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(500);
  await page.pdf({
    path: resolve(output),
    width: '1920px',
    height: '1080px',
    printBackground: true,
    preferCSSPageSize: true,
    margin: { top: 0, right: 0, bottom: 0, left: 0 },
  });
  console.log('PDF geschrieben:', resolve(output));
} finally {
  await browser.close();
}
