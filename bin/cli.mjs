#!/usr/bin/env node

import { main } from '../src/main.mjs';

const major = Number(process.versions.node.split('.')[0]);
if (Number.isFinite(major) && major < 18) {
  console.error(
    `\n  \u2718 architecture-assessment-tools requires Node.js 18 or newer (found ${process.versions.node}).\n`,
  );
  process.exit(1);
}

const args = process.argv.slice(2);

if (args.includes('--help') || args.includes('-h')) {
  console.log(`
  Usage: npx github:jochenvw/architecture-assessment-tools [options]

  Installs this repository's Copilot skills into your project or personal
  Copilot folder.

  Options:
    --global           Install into your personal Copilot folder (~/.copilot/skills)
    --local            Install into this project (default: .copilot/skills)
    --dest <path>      Destination directory for a local install
    --force            Overwrite existing skill folders without asking
    --no-settings      Skip the .vscode/settings.json update (local install)
    --clean            Remove previous installs from this package, then install
    --clean-only       Remove previous installs from this package and exit
    --help, -h         Show this help message

  Examples:
    npx github:jochenvw/architecture-assessment-tools --global
    npx github:jochenvw/architecture-assessment-tools --local --dest .copilot/skills
`);
  process.exit(0);
}

if (args.includes('--global') && args.includes('--local')) {
  console.error('\n  \u2718 Choose either --global or --local, not both.\n');
  process.exit(1);
}

const options = {
  dest: getFlag('--dest'),
  force: args.includes('--force'),
  noSettings: args.includes('--no-settings'),
  mode: args.includes('--global')
    ? 'global'
    : args.includes('--local')
      ? 'local'
      : undefined,
  clean: args.includes('--clean'),
  cleanOnly: args.includes('--clean-only'),
};

main(options).catch((err) => {
  console.error(`\n  \u2718 ${err.message}\n`);
  process.exit(1);
});

/**
 * Extract a flag value: `--flag value` or `--flag=value`.
 * @param {string} flag
 * @returns {string | undefined}
 */
function getFlag(flag) {
  const idx = args.indexOf(flag);
  if (idx !== -1 && idx + 1 < args.length) {
    return args[idx + 1];
  }
  const prefix = flag + '=';
  const match = args.find((a) => a.startsWith(prefix));
  return match ? match.slice(prefix.length) : undefined;
}
