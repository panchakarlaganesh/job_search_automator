#!/usr/bin/env python3
"""Supply-chain security guards for job_search_automator.

Ported from MadsLorentzen/ai-job-search tools/security_guards.py (upstream feat 3efc52e).

Checks:
1. .claude/settings.json  — every permissions.allow entry and every hook command
   must be in the exact allowlists below. Catches permission widening and
   zero-click hook execution (e.g. Shai-Hulud worm, August 2026).
2. .gitignore             — personal-data ignore rules must all be present, and
   no un-allowlisted negation (!pattern) may re-include them.
3. .agents/**/package.json — no npm/bun lifecycle scripts and no trustedDependencies.

Run from repo root:  python tools/security_guards.py
Exit 0 = OK, Exit 1 = failures listed.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors: list[str] = []

# Permissions that job_search_automator legitimately pre-approves.
# Add new entries here in the same PR that adds them to settings.json.
ALLOWED_PERMISSIONS: set[str] = {
    "Bash(python:*)",
    "Bash(python3:*)",
    "Bash(git:*)",
    "Bash(pip:*)",
}

# Personal-data files that must always be gitignored.
REQUIRED_IGNORE_RULES = [
    ".env",
    ".env.*",
    "data/*.db",
    "resumes/tailored/**",
    "logs/**",
]

# Negation (re-include) rules this project legitimately ships.
ALLOWED_IGNORE_NEGATIONS: set[str] = {
    "!data/.gitkeep",
    "!resumes/.gitkeep",
    "!logs/.gitkeep",
}

# Hook commands this project legitimately ships, as "<Event>:<command>" strings.
# Empty by design — this project ships no hooks at all.
# A hook runs unconditionally when its event fires (no prompt, no model decision).
# This is the vector the Shai-Hulud worm used in August 2026:
# https://research.jfrog.com/post/shai-hulud-is-back-august/
ALLOWED_HOOKS: set[str] = set()

FORBIDDEN_SCRIPTS = {"preinstall", "install", "postinstall", "prepare", "prepack"}


def _hook_commands(event: str, entries: object):
    """Yield '<Event>:<command>' for every hook command. Fails closed on unknown shapes."""
    unrecognised = f"{event}:<unrecognised hook shape>"
    if not isinstance(entries, list):
        yield unrecognised
        return
    for entry in entries:
        if not isinstance(entry, dict):
            yield unrecognised
            continue
        inner = entry.get("hooks")
        if not isinstance(inner, list):
            yield unrecognised
            continue
        for hook in inner:
            command = hook.get("command") if isinstance(hook, dict) else None
            yield f"{event}:{command}" if isinstance(command, str) else unrecognised


def check_permissions() -> None:
    # Check .claude/settings.json if it exists
    for settings_path in [ROOT / ".claude" / "settings.json", ROOT / ".agents" / "settings.json"]:
        if not settings_path.exists():
            continue
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{settings_path.name}: unreadable or invalid JSON: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{settings_path.name}: top-level JSON value must be an object")
            continue

        # Check hooks BEFORE permissions — a malformed permissions block paired
        # with a hook must not return early and skip the hook check.
        hooks = data.get("hooks", {})
        if hooks:
            if not isinstance(hooks, dict):
                errors.append(f"{settings_path.name}: hooks must be an object")
            else:
                for event, entries in hooks.items():
                    for command in _hook_commands(str(event), entries):
                        if command not in ALLOWED_HOOKS:
                            errors.append(
                                f"{settings_path.name}: hook not in reviewed allowlist: "
                                f"{command!r}. A hook runs automatically when its event fires "
                                "with no prompt. If intentional, add it to ALLOWED_HOOKS in "
                                "tools/security_guards.py in the same PR."
                            )

        permissions = data.get("permissions", {})
        if not isinstance(permissions, dict):
            continue
        allow = permissions.get("allow", [])
        if not isinstance(allow, list) or not all(isinstance(e, str) for e in allow):
            errors.append(f"{settings_path.name}: permissions.allow must be a list of strings")
            continue
        for entry in allow:
            if entry not in ALLOWED_PERMISSIONS:
                errors.append(
                    f"{settings_path.name}: permission not in reviewed allowlist: {entry!r}. "
                    "Add it to ALLOWED_PERMISSIONS in tools/security_guards.py in the same PR."
                )


def check_gitignore() -> None:
    path = ROOT / ".gitignore"
    if not path.exists():
        errors.append(".gitignore: file not found")
        return
    try:
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    except OSError as exc:
        errors.append(f".gitignore: unreadable: {exc}")
        return
    rules = set(lines)
    for rule in REQUIRED_IGNORE_RULES:
        if rule not in rules:
            errors.append(
                f".gitignore: required personal-data rule missing: {rule!r}. "
                "Update REQUIRED_IGNORE_RULES in tools/security_guards.py in the same PR."
            )
    for line in lines:
        if line.startswith("!") and line not in ALLOWED_IGNORE_NEGATIONS:
            errors.append(
                f".gitignore: negation rule not in reviewed allowlist: {line!r}. "
                "A negation can silently re-expose personal data. "
                "Add it to ALLOWED_IGNORE_NEGATIONS in tools/security_guards.py in the same PR."
            )


def check_package_manifests() -> None:
    manifests = [
        p for p in ROOT.glob(".agents/**/package.json") if "node_modules" not in p.parts
    ]
    for manifest in manifests:
        relpath = manifest.relative_to(ROOT)
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{relpath}: unreadable or invalid JSON: {exc}")
            continue
        if not isinstance(data, dict):
            continue
        scripts = data.get("scripts", {})
        if isinstance(scripts, dict):
            bad = FORBIDDEN_SCRIPTS & set(scripts)
            if bad:
                errors.append(
                    f"{relpath}: lifecycle script(s) {sorted(bad)} are forbidden — "
                    "they execute arbitrary code during `bun install`."
                )
        if "trustedDependencies" in data:
            errors.append(
                f"{relpath}: trustedDependencies is forbidden — it re-enables dependency "
                "lifecycle scripts that bun blocks by default."
            )


def main() -> int:
    check_permissions()
    check_gitignore()
    check_package_manifests()
    if errors:
        print(f"security_guards: {len(errors)} failure(s)")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("security_guards: OK (permissions allowlist, hooks allowlist, gitignore rules, package manifests)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
