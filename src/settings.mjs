import fs from 'node:fs';
import path from 'node:path';
import { applyEdits, modify, parse } from 'jsonc-parser';
import { SKILLS_SETTING_KEY } from './constants.mjs';

/**
 * Canonicalize a workspace-relative location for comparison: resolve it against
 * the project root and normalize separators. On Windows the comparison is
 * case-insensitive.
 *
 * @param {string} projectRoot
 * @param {string} location
 * @returns {string}
 */
function canonical(projectRoot, location) {
  const resolved = path.resolve(projectRoot, String(location));
  return process.platform === 'win32' ? resolved.toLowerCase() : resolved;
}

/**
 * Merge the skills location into `.vscode/settings.json`.
 *
 * `.vscode/settings.json` is JSONC (comments and trailing commas allowed), so
 * edits are applied with jsonc-parser to preserve the user's existing content.
 * The setting `chat.agentSkillsLocations` is an array of directory paths that
 * each contain skill folders; we add `location` if no equivalent path is
 * already present (compared canonically, not by raw string).
 *
 * If the existing settings file cannot be parsed as a JSON object, the merge is
 * skipped (returning `{ skipped: true }`) rather than overwriting the user's
 * file — the caller surfaces a manual-edit hint.
 *
 * @param {string} projectRoot – absolute project root
 * @param {string} location – workspace-relative directory containing skill folders
 * @returns {{ created: boolean, added: boolean, skipped?: boolean, location: string }}
 */
export function mergeSettings(projectRoot, location) {
  const vscodeDir = path.join(projectRoot, '.vscode');
  const settingsPath = path.join(vscodeDir, 'settings.json');

  let raw = '{}';
  let created = true;
  if (fs.existsSync(settingsPath)) {
    raw = fs.readFileSync(settingsPath, 'utf-8').trim() || '{}';
    created = false;
  }

  const normalized = location.replace(/\\/g, '/');

  // Parse defensively: a malformed settings.json must not be overwritten.
  // jsonc-parser tolerates comments and trailing commas (both valid in
  // VS Code settings) but reports real syntax errors via the errors array.
  const errors = [];
  const current = parse(raw, errors, { allowTrailingComma: true });
  if (
    errors.length > 0 ||
    current === undefined ||
    typeof current !== 'object' ||
    current === null ||
    Array.isArray(current)
  ) {
    return { created: false, added: false, skipped: true, location: normalized };
  }
  const existing = Array.isArray(current[SKILLS_SETTING_KEY])
    ? current[SKILLS_SETTING_KEY]
    : [];

  const wanted = canonical(projectRoot, normalized);
  const alreadyPresent = existing.some(
    (v) => canonical(projectRoot, v) === wanted,
  );
  if (alreadyPresent) {
    return { created: false, added: false, location: normalized };
  }

  const nextValue = [...existing, normalized];
  const edits = modify(raw, [SKILLS_SETTING_KEY], nextValue, {
    formattingOptions: { insertSpaces: true, tabSize: 2 },
  });
  const updated = applyEdits(raw, edits);

  fs.mkdirSync(vscodeDir, { recursive: true });
  fs.writeFileSync(settingsPath, updated);

  return { created, added: true, location: normalized };
}
