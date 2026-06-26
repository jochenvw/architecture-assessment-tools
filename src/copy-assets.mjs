import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { INSTALL_MARKER, PACKAGE_NAME, SKILLS_SOURCE_DIR } from './constants.mjs';

/** Resolve the root of this package (one level up from src/). */
export const PKG_ROOT = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '..',
);

/**
 * Join an untrusted path segment onto a trusted base directory, ensuring the
 * resolved path stays within `base`. Directory entry names read from disk are
 * an external boundary, so guard against any segment that would escape the
 * destination (e.g. via `..` or an absolute path).
 *
 * @param {string} base – trusted base directory
 * @param {string} segment – untrusted path segment
 * @returns {string} the safe joined path, guaranteed to be inside `base`
 * @throws {Error} if the resolved path escapes `base`
 */
export function safeJoin(base, segment) {
  const target = path.join(base, segment);
  const relative = path.relative(base, target);
  if (relative === '' || relative.startsWith('..') || path.isAbsolute(relative)) {
    throw new Error(`Refusing to operate outside target directory: ${segment}`);
  }
  return target;
}

/**
 * List the skill folder names shipped by this package (each folder under
 * the source skills directory that contains a SKILL.md).
 *
 * @returns {string[]}
 */
export function listSkillNames() {
  const src = path.join(PKG_ROOT, SKILLS_SOURCE_DIR);
  if (!fs.existsSync(src)) return [];
  return fs
    .readdirSync(src, { withFileTypes: true })
    .filter((e) => e.isDirectory())
    .filter((e) => fs.existsSync(path.join(src, e.name, 'SKILL.md')))
    .map((e) => e.name)
    .sort();
}

/**
 * Recursively copy a directory tree.
 * @param {string} src
 * @param {string} dest
 */
export function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const srcPath = safeJoin(src, entry.name);
    const destPath = safeJoin(dest, entry.name);
    if (entry.isDirectory()) {
      copyDir(srcPath, destPath);
    } else {
      try {
        fs.cpSync(srcPath, destPath, { force: true });
      } catch (err) {
        if (err.code === 'EACCES') {
          console.error(`\n  \u2718 Permission denied writing to ${destPath}\n`);
          process.exit(1);
        }
        throw err;
      }
    }
  }
}

/**
 * Count files recursively in a directory.
 * @param {string} dir
 * @returns {number}
 */
export function countFiles(dir) {
  let count = 0;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      count += countFiles(path.join(dir, entry.name));
    } else {
      count++;
    }
  }
  return count;
}

/**
 * Validate that a name read from an (untrusted) install marker is a plausible
 * single-segment skill folder name. Rejects path separators, traversal, empty
 * or hidden names, and anything outside a conservative charset.
 *
 * @param {unknown} name
 * @returns {boolean}
 */
export function isValidSkillName(name) {
  return (
    typeof name === 'string' &&
    name.length > 0 &&
    name.length <= 128 &&
    name !== '.' &&
    name !== '..' &&
    !name.startsWith('.') &&
    /^[A-Za-z0-9._-]+$/.test(name)
  );
}

/**
 * Read the install marker from a skills destination directory.
 *
 * Only a marker that is well-formed AND owned by this package (matching
 * `PACKAGE_NAME`) is honoured. A corrupt, foreign, or schema-invalid marker
 * returns null so the installer never treats someone else's folders as its own
 * (which would let a forged marker bypass collision checks or be deleted by
 * `--clean`).
 *
 * The `skills` array is user-editable, so it is treated as untrusted: every
 * entry must be a valid single-segment name AND must correspond either to a
 * skill shipped by this package or to an existing folder that actually contains
 * a `SKILL.md`. This prevents a hand-forged marker from (a) claiming ownership
 * of unrelated pre-existing folders to bypass collision checks, or (b) listing
 * arbitrary directory names that `--clean` would then delete.
 *
 * @param {string} destDir – directory that contains skill folders
 * @returns {{ package: string, version?: string, skills: string[] } | null}
 */
export function readMarker(destDir) {
  const markerPath = path.join(destDir, INSTALL_MARKER);
  if (!fs.existsSync(markerPath)) return null;
  let parsed;
  try {
    parsed = JSON.parse(fs.readFileSync(markerPath, 'utf-8'));
  } catch {
    return null;
  }
  if (
    !parsed ||
    typeof parsed !== 'object' ||
    parsed.package !== PACKAGE_NAME ||
    !Array.isArray(parsed.skills) ||
    !parsed.skills.every((s) => typeof s === 'string')
  ) {
    return null;
  }
  const shipped = new Set(listSkillNames());
  const skills = parsed.skills.filter(
    (name) =>
      isValidSkillName(name) &&
      (shipped.has(name) ||
        fs.existsSync(path.join(destDir, name, 'SKILL.md'))),
  );
  return { ...parsed, skills };
}

/**
 * Write the install marker recording which skill folders this package owns.
 * @param {string} destDir – directory that contains skill folders
 * @param {string} version – package version
 * @param {string[]} skills – installed skill folder names
 */
export function writeMarker(destDir, version, skills) {
  const markerPath = path.join(destDir, INSTALL_MARKER);
  const payload = {
    package: PACKAGE_NAME,
    version,
    installedAt: new Date().toISOString(),
    skills: [...skills].sort(),
  };
  fs.mkdirSync(destDir, { recursive: true });
  fs.writeFileSync(markerPath, JSON.stringify(payload, null, 2) + '\n');
}

/**
 * Copy the package's skill folders into a destination directory.
 *
 * Collision safety: if a target skill folder already exists and is NOT recorded
 * in this package's install marker, the install refuses unless `force` is set.
 *
 * Clean upgrades: when a target folder is going to be (re)written, it is removed
 * first so files deleted upstream do not linger from a previous install.
 *
 * @param {string} destDir – absolute directory that will contain skill folders
 * @param {{ force?: boolean }} [opts]
 * @returns {{ copied: number, skills: string[] }}
 */
export function installSkills(destDir, { force = false } = {}) {
  const src = path.join(PKG_ROOT, SKILLS_SOURCE_DIR);
  const skills = listSkillNames();
  const marker = readMarker(destDir);
  const owned = new Set(marker?.skills ?? []);

  let copied = 0;
  for (const name of skills) {
    const target = safeJoin(destDir, name);
    if (fs.existsSync(target) && !owned.has(name) && !force) {
      console.error(
        `\n  \u2718 A skill folder named "${name}" already exists at ${destDir}` +
          `\n    and was not installed by ${PACKAGE_NAME}. Re-run with --force to overwrite.\n`,
      );
      process.exit(1);
    }
    // Replace the folder wholesale so files removed upstream don't survive.
    if (fs.existsSync(target)) {
      fs.rmSync(target, { recursive: true, force: true });
    }
    copyDir(safeJoin(src, name), target);
    copied += countFiles(target);
  }

  return { copied, skills };
}
