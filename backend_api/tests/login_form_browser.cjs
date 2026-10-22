const fs = require('fs');
const assert = require('assert');
const {chromium} = require('C:/Users/aaron/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const source = fs.readFileSync(require('path').join(__dirname,'../routers/som_web.py'),'utf8');
const form = source.match(/<form id="loginForm"[\s\S]*?<\/form>/)[0];
(async () => {
  const browser = await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
  try {
    const page = await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
    await page.setContent(form);
    await page.evaluate(() => {
      window.submits=0;
      document.querySelector('form').onsubmit=e=>{e.preventDefault();window.submits++;};
    });
    assert.equal(await page.locator('#pass').getAttribute('autocomplete'),'current-password');
    assert.equal(await page.locator('#user').getAttribute('name'),'username');
    assert.equal(await page.locator('#pass').getAttribute('name'),'password');
    await page.locator('#loginBtn').click();
    assert.equal(await page.evaluate(()=>window.submits),0);
    await page.locator('#user').fill('test-only');
    await page.locator('#pass').fill('not-a-real-password');
    await page.locator('#pass').press('Enter');
    assert.equal(await page.evaluate(()=>window.submits),1);
    await page.locator('#bioBtn').click();
    assert.equal(await page.evaluate(()=>window.submits),1);
    assert(source.includes('$("loginForm").onsubmit = event => { event.preventDefault(); login(); };'));
    console.log('PASS: mobile semantic login, autocomplete, validation, Enter and independent passkey button. Native password-manager prompts require real-device verification.');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
