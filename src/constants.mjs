/**
 * Shared constants for the architecture-assessment-tools skills installer.
 */

/** Default destination directory (relative to project root) for a local install. */
export const DEFAULT_DEST = '.copilot/skills';

/** Directory inside this package that holds the distributable skill folders. */
export const SKILLS_SOURCE_DIR = '.github/skills';

/**
 * Path segments (relative to the user's home directory) for the personal
 * GitHub Copilot skills folder. Copilot reads skills from this location across
 * every workspace, so installing here makes the skills available globally.
 *   • macOS / Linux: ~/.copilot/skills
 *   • Windows:       %USERPROFILE%\.copilot\skills
 */
export const USER_SKILLS_DIR_SEGMENTS = ['.copilot', 'skills'];

/**
 * VS Code setting that tells Copilot where to discover workspace skills.
 * The value points at the directory that *contains* the skill folders.
 */
export const SKILLS_SETTING_KEY = 'chat.agentSkillsLocations';

/**
 * Name of the install marker written alongside installed skills. It records
 * which folders this package owns so `--clean` never removes a user's own
 * skills that happen to share a name.
 */
export const INSTALL_MARKER = '.installed-skills.json';

/** Human-readable package identity recorded in the install marker. */
export const PACKAGE_NAME = 'architecture-assessment-tools';
