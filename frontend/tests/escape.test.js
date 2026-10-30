const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const utilsPath = path.join(__dirname, '..', 'js', 'utils.js');
const sandbox = { window: {} };
vm.runInNewContext(fs.readFileSync(utilsPath, 'utf8'), sandbox);

const escapeHTML = sandbox.window.escapeHTML;
assert.strictEqual(
    escapeHTML('<img src=x onerror=alert(1)>'),
    '&lt;img src=x onerror=alert(1)&gt;'
);
assert.strictEqual(escapeHTML('&"\''), '&amp;&quot;&#39;');
assert.strictEqual(escapeHTML(null), '');
assert.strictEqual(escapeHTML(undefined), '');
assert.strictEqual(escapeHTML('<script>alert(1)</script>'), '&lt;script&gt;alert(1)&lt;/script&gt;');

console.log('escapeHTML: OK');
