const cp = require('child_process'), vm = require('vm');
const source = `import ast,json
t=ast.parse(open('backend_api/routers/som_web.py',encoding='utf-8-sig').read())
f=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='som_web_home')
a=next(n for n in f.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='html' for x in n.targets))
print(json.dumps(ast.literal_eval(a.value)))`;
const html = JSON.parse(cp.execFileSync('python',['-c',source],{encoding:'utf8'}));
for (const match of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) new vm.Script(match[1]);
console.log('PASS: rendered SOM inline JavaScript parses');
