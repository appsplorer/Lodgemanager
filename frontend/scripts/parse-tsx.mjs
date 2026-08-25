import fs from 'fs';
import path from 'path';
import {createRequire} from 'module';
import {execFileSync} from 'child_process';

const require=createRequire(import.meta.url);
let ts;
try {
  ts=require('typescript');
} catch {
  try {
    const globalRoot=execFileSync('npm',['root','-g'],{encoding:'utf8'}).trim();
    ts=require(path.join(globalRoot,'typescript'));
  } catch (error) {
    console.error('TypeScript is required for the LodgeFlow syntax scan. Run npm install in frontend/.');
    process.exit(2);
  }
}

function walk(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === 'node_modules' || entry.name === '.next' || entry.name === 'playwright-report' || entry.name === 'test-results') return [];
      return walk(fullPath);
    }
    return [fullPath];
  });
}

const files = walk('.')
  .filter((file) => /\.(ts|tsx)$/.test(file))
  .filter((file) => !file.endsWith('.d.ts'));

let errors = 0;
for (const file of files) {
  const source = fs.readFileSync(file, 'utf8');
  const scriptKind = file.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS;
  const parsed = ts.createSourceFile(file, source, ts.ScriptTarget.ES2022, true, scriptKind);
  for (const diagnostic of parsed.parseDiagnostics || []) {
    if (diagnostic.category !== ts.DiagnosticCategory.Error) continue;
    errors += 1;
    const start = diagnostic.start ?? 0;
    const position = parsed.getLineAndCharacterOfPosition(start);
    const message = ts.flattenDiagnosticMessageText(diagnostic.messageText, ' ');
    console.error(`${file}:${position.line + 1}:${position.character + 1}: ${message}`);
  }
}

console.log(`${files.length} TypeScript/TSX files parsed; ${errors} syntax error(s)`);
process.exit(errors ? 1 : 0);
