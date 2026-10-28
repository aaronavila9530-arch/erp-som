const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = require('node:child_process').execFileSync('python', ['-X', 'utf8', '-W', 'ignore', '-c',
  "import ast; from pathlib import Path; tree=ast.parse(Path('backend_api/routers/som_web.py').read_text(encoding='utf-8-sig')); f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='som_web_home'); print(next(n.value.value for n in f.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='html' for t in n.targets)))"
], {encoding:'utf8', maxBuffer:4*1024*1024});
const word = source.slice(source.indexOf('    function downloadWordFile('), source.indexOf('    function downloadCollectionsExcel('));
const statement = source.slice(source.indexOf('    async function downloadCollectionsStatementWord('), source.indexOf('    function openCollectionDisputeForm('));
let company = 'MCI-CR';
let result;
const logo = fs.readFileSync('backend_api/assets/mci_logo.png');
const context = vm.createContext({
  crypto: require('node:crypto').webcrypto, btoa: s => Buffer.from(s, 'binary').toString('base64'),
  unescape, encodeURIComponent, Uint8Array, DataView,
  collectionRows: [{nombre_cliente:'QA CLIENT', saldo_pendiente:10, total:10, moneda:'USD'}],
  selectedCompany: () => company, esc: s => String(s ?? ''),
  fetch: async () => ({ok:true, arrayBuffer:async () => Uint8Array.from(logo).buffer}),
  alert: message => {throw new Error(message)},
  downloadText: (filename, body, type) => {result={filename,body,type}}
});
vm.runInContext(word + statement, context);
(async () => {
  await vm.runInContext('downloadCollectionsStatementWord()', context);
  assert.match(result.body, /multipart\/related/);
  assert.ok(result.body.includes(logo.toString('base64').slice(0,76)));
  if (process.argv.includes('--fixture')) fs.writeFileSync('tmp/branding-audit/statement-mci.doc', result.body);
  company = 'MSL-CR';
  await vm.runInContext('downloadCollectionsStatementWord()', context);
  assert.ok(result.body.startsWith('<!doctype html>'));
  assert.ok(!result.body.includes('mci-logo'));
  console.log('PASS: MCI embeds its logo; MSL retains original HTML export');
})().catch(error => {console.error(error);process.exitCode=1});
