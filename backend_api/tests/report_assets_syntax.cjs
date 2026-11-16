const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../assets');
let count = 0;
function check(directory) {
  for (const entry of fs.readdirSync(directory, {withFileTypes: true})) {
    const file = path.join(directory, entry.name);
    if (entry.isDirectory()) check(file);
    else if (entry.name.endsWith('.js')) {
      new vm.Script(fs.readFileSync(file, 'utf8'), {filename: file});
      count++;
    }
  }
}
for (const folder of ['certificates', 'mci_surveys', 'tally', 'containers', 'logra']) {
  const directory = path.join(root, folder);
  if (fs.existsSync(directory)) check(directory);
}
console.log(`PASS: ${count} report JavaScript assets parse successfully`);
