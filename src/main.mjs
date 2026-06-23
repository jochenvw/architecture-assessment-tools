import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {
  DEFAULT_DEST,
  INSTALL_MARKER,
  PACKAGE_NAME,
  USER_SKILLS_DIR_SEGMENTS,
} from './constants.mjs';
import {
  PKG_ROOT,
  installSkills,
  listSkillNames,
  readMarker,
  safeJoin,
  writeMarker,
} from './copy-assets.mjs';
import { mergeSettings } from './settings.mjs';

/**
 * Read this package's version from its own package.json.
 * @returns {string}
 */
function getVersion() {
  const pkg = JSON.parse(
    fs.readFileSync(path.join(PKG_ROOT, 'package.json'), 'utf-8'),
  );
  return pkg.version;
}

/**
 * Render the banner. Colors are applied only when stdout is an interactive TTY.
 * @param {string} version
 * @returns {string}
 */
function renderBanner(version) {
  const useColor = process.stdout.isTTY && !process.env.NO_COLOR;
  const cyan = useColor ? '\u001b[36m' : '';
  const bold = useColor ? '\u001b[1m' : '';
  const dim = useColor ? '\u001b[2m' : '';
  const reset = useColor ? '\u001b[0m' : '';
  return (
    `\n  ${cyan}${bold}architecture-assessment-tools${reset}\n` +
    `  ${dim}GitHub Copilot skills installer${reset}\n` +
    `  ${dim}v${version}${reset}\n`
  );
}

/**
 * Prompt for a free-text answer with a default.
 * @param {string} question
 * @param {string} fallback
 * @returns {Promise<string>}
 */
async function ask(question, fallback) {
  if (!process.stdin.isTTY) return fallback;
  const { createInterface } = await import('node:readline/promises');
  const rl = createInterface({ input: process.stdin, output: process.stdout });
  try {
    const answer = await rl.question(question);
    return answer.trim() || fallback;
  } catch {
    return fallback;
  } finally {
    rl.close();
  }
}

/**
 * Resolve and validate a local destination path against the project root.
 * Rejects absolute paths, empty paths, and paths that escape the project root.
 *
 * @param {string} projectRoot
 * @param {string | undefined} rawDest
 * @returns {{ dest: string, resolved: string }}
 */
function resolveLocalDest(projectRoot, rawDest) {
  let dest = (rawDest || DEFAULT_DEST).replace(/\\/g, '/');
  if (path.isAbsolute(dest)) {
    console.error('\n  \u2718 Please use a relative path (e.g., .copilot/skills).\n');
    process.exit(1);
  }
  dest = dest.replace(/\/+$/, '');
  if (!dest) {
    console.error('\n  \u2718 Please provide a non-empty destination path.\n');
    process.exit(1);
  }
  const resolved = path.resolve(projectRoot, dest);
  if (resolved !== projectRoot && !resolved.startsWith(projectRoot + path.sep)) {
    console.error('\n  \u2718 Destination must be within the current project.\n');
    process.exit(1);
  }
  // Defend against symlink/junction escape: the nearest existing ancestor of
  // the destination must resolve (realpath) to a location inside the project.
  const realRoot = fs.realpathSync(projectRoot);
  let probe = resolved;
  while (!fs.existsSync(probe)) {
    const parent = path.dirname(probe);
    if (parent === probe) break;
    probe = parent;
  }
  const realProbe = fs.existsSync(probe) ? fs.realpathSync(probe) : probe;
  if (realProbe !== realRoot && !realProbe.startsWith(realRoot + path.sep)) {
    console.error('\n  \u2718 Destination resolves outside the project (symlink?).\n');
    process.exit(1);
  }
  return { dest, resolved };
}

/**
 * Remove previously installed skill folders from a destination directory.
 * Only folders recorded in this package's install marker are removed, so a
 * user's own skills are never touched.
 *
 * @param {string} destDir – absolute directory that contains skill folders
 * @param {string} label – human-readable description of the location
 * @returns {boolean} true if anything was removed
 */
function removeInstall(destDir, label) {
  const marker = readMarker(destDir);
  if (!marker || !Array.isArray(marker.skills) || marker.skills.length === 0) {
    return false;
  }

  let removed = 0;
  for (const name of marker.skills) {
    let target;
    try {
      target = safeJoin(destDir, name);
    } catch {
      continue;
    }
    if (fs.existsSync(target)) {
      fs.rmSync(target, { recursive: true, force: true });
      removed++;
      console.log(`      - ${name}/`);
    }
  }
  fs.rmSync(path.join(destDir, INSTALL_MARKER), { force: true });

  if (removed > 0) {
    console.log(`  \u2714 Removed ${removed} skill folder${removed === 1 ? '' : 's'} from ${label}`);
  }
  return removed > 0;
}

/**
 * Run cleanup across the global skills folder and the local destination.
 *
 * @param {string} userSkillsDir
 * @param {string} localDest
 * @returns {boolean} true if any cleanup happened
 */
function runCleanup(userSkillsDir, localDest) {
  console.log('\n  \uD83E\uDDF9 Cleaning previous installs from this package:\n');
  const a = removeInstall(userSkillsDir, `${userSkillsDir}/`);
  const b = removeInstall(localDest, `${localDest}/`);
  if (!a && !b) {
    console.log('  No previous installation from this package found.');
  }
  return a || b;
}

/**
 * Orchestrator: parse mode, install globally or locally, write marker, merge
 * settings, print summary.
 *
 * @param {{ dest?: string, force?: boolean, noSettings?: boolean, mode?: 'global' | 'local', clean?: boolean, cleanOnly?: boolean }} options
 */
export async function main(options = {}) {
  const version = getVersion();
  console.log(renderBanner(version));

  const projectRoot = process.cwd();
  const hasProjectMarker =
    fs.existsSync(path.join(projectRoot, 'package.json')) ||
    fs.existsSync(path.join(projectRoot, '.git'));
  if (!hasProjectMarker) {
    console.warn(
      '  \u26A0 This directory does not look like a project root (no package.json or .git). Proceeding anyway.\n',
    );
  }

  const userSkillsDir = path.join(os.homedir(), ...USER_SKILLS_DIR_SEGMENTS);

  // --- Optional cleanup of previous installs ---
  if (options.clean || options.cleanOnly) {
    const { resolved: localDest } = resolveLocalDest(projectRoot, options.dest);
    runCleanup(userSkillsDir, localDest);
    if (options.cleanOnly) {
      console.log('\n  Done.\n');
      return;
    }
  }

  // --- Determine install mode ---
  let mode = options.mode;
  if (!mode) {
    const answer = await ask(
      '  Install (g)lobally for all projects or (l)ocally into this project? [g/l]: ',
      'g',
    );
    mode = answer.toLowerCase().startsWith('l') ? 'local' : 'global';
  }

  // --- Global install ---
  if (mode === 'global') {
    if (fs.existsSync(userSkillsDir)) {
      const marker = readMarker(userSkillsDir);
      const collisions = listSkillNames().filter(
        (name) =>
          fs.existsSync(path.join(userSkillsDir, name)) &&
          !(marker?.skills ?? []).includes(name),
      );
      if (collisions.length > 0 && !options.force) {
        console.error(
          `\n  \u2718 These skill folders already exist in ${userSkillsDir} and were not\n` +
            `    installed by ${PACKAGE_NAME}: ${collisions.join(', ')}.\n` +
            '    Re-run with --force to overwrite them.\n',
        );
        process.exit(1);
      }
    }

    const { copied, skills } = installSkills(userSkillsDir, { force: options.force });
    writeMarker(userSkillsDir, version, skills);

    console.log(
      `\n  \u2714 Installed ${skills.length} skill${skills.length === 1 ? '' : 's'} ` +
        `(${copied} file${copied === 1 ? '' : 's'}) to ${userSkillsDir}/`,
    );
    for (const name of skills) console.log(`    \u2022 ${name}/`);
    console.log(
      '\n  \u2139 Global skill names share a flat namespace. If you maintain your own\n' +
        '    skills with the same names, prefer a local install instead.\n' +
        '\n  Done. Open Copilot in any project and start using the skills.\n',
    );
    return;
  }

  // --- Local install ---
  let dest = options.dest;
  if (!dest) {
    dest = await ask(
      `  Destination directory for skills [${DEFAULT_DEST}]: `,
      DEFAULT_DEST,
    );
  }
  const { dest: relDest, resolved: fullDest } = resolveLocalDest(projectRoot, dest);

  if (fs.existsSync(fullDest) && !options.force) {
    const marker = readMarker(fullDest);
    const collisions = listSkillNames().filter(
      (name) =>
        fs.existsSync(path.join(fullDest, name)) &&
        !(marker?.skills ?? []).includes(name),
    );
    if (collisions.length > 0) {
      console.error(
        `\n  \u2718 These skill folders already exist in ${relDest} and were not\n` +
          `    installed by ${PACKAGE_NAME}: ${collisions.join(', ')}.\n` +
          '    Re-run with --force to overwrite them.\n',
      );
      process.exit(1);
    }
  }

  const { copied, skills } = installSkills(fullDest, { force: true });
  writeMarker(fullDest, version, skills);

  console.log(
    `\n  \u2714 Installed ${skills.length} skill${skills.length === 1 ? '' : 's'} ` +
      `(${copied} file${copied === 1 ? '' : 's'}) to ${relDest}/`,
  );
  for (const name of skills) console.log(`    \u2022 ${name}/`);

  if (!options.noSettings) {
    const { created, added, skipped } = mergeSettings(projectRoot, relDest);
    if (skipped) {
      console.log(
        '\n  \u26A0 Could not parse .vscode/settings.json (left untouched).' +
          `\n    Add "${relDest}" to "chat.agentSkillsLocations" manually.`,
      );
    } else if (added) {
      console.log(
        `\n  \u2714 ${created ? 'Created' : 'Updated'} .vscode/settings.json ` +
          `(chat.agentSkillsLocations \u2192 ${relDest})`,
      );
    } else {
      console.log('\n  \u2022 .vscode/settings.json already points at this location \u2014 unchanged');
    }
  } else {
    console.log('\n  \u2298 Skipped .vscode/settings.json (--no-settings)');
  }

  console.log('\n  Done. Reload VS Code so Copilot picks up the new skills location.\n');
}
