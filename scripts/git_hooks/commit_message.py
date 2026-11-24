#!/usr/bin/env python3
"""Commit messages of Marmotte: prefill the header from the branch, check the convention.

Convention (CLAUDE.md, "Conventions"): ``type(module): description``, in English.

- ``prefill <file>``: pre-commit ``prepare-commit-msg`` stage. Writes ``type(module): `` at the
  start of the message, from the branch (``type/<n>-<slug>``) and the staged files.
- ``check <file>``: pre-commit ``commit-msg`` stage. Refuses a message outside the convention.
- ``check -``: same check on the text read from stdin (the CI uses it for pull request titles).

Standard library only, Python 3.12 or later: it runs with the system ``python3``.
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from pathlib import PurePosixPath

TYPES = ("feat", "fix", "refactor", "test", "docs", "chore", "ci")
MAX_TITLE_LENGTH = 72
HEADER = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<module>[a-z0-9-]+)\))?!?:(?: (?P<description>.*))?$")
BRANCH = re.compile(r"^(?P<type>[a-z]+)/[a-z0-9][a-z0-9._-]*$")
WRITTEN_BY_GIT = ("Merge ", 'Revert "', "fixup! ", "squash! ", "amend! ")
CLAUDE_MENTIONS = (
    re.compile(r"^co-authored-by:.*claude", re.IGNORECASE | re.MULTILINE),
    re.compile(r"generated with \[?claude code", re.IGNORECASE),
)
SCISSORS = "# ------------------------ >8 ------------------------"
TOP_LEVEL_MODULES = ("backend", "frontend", "system", "hardware", "docs")


def meaningful_lines(message: str) -> list[str]:
    """Lines Git keeps: without comments, and without what follows the scissors line."""
    lines: list[str] = []
    for line in message.splitlines():
        if line == SCISSORS:
            break
        if not line.startswith("#"):
            lines.append(line.rstrip())
    while lines and not lines[-1]:
        lines.pop()
    return lines


def check_message(message: str) -> list[str]:
    """Return the reasons why the message breaks the convention (empty list: it is valid)."""
    lines = meaningful_lines(message)
    if not lines or not lines[0].strip():
        return ["le message est vide"]
    title = lines[0]
    if title.startswith(WRITTEN_BY_GIT):
        return []
    errors: list[str] = []
    match = HEADER.match(title)
    if match is None:
        errors.append(f"le titre doit suivre « type(module): description » (module facultatif), reçu « {title} »")
    else:
        if match["type"] not in TYPES:
            errors.append(f"type inconnu « {match['type']} » ; types permis : {', '.join(TYPES)}")
        description = match["description"] or ""
        if not description.strip():
            errors.append("la description est vide")
        elif len(description) > 1 and description[0].isupper() and description[1].islower():
            errors.append("la description commence par une minuscule (« add », pas « Add »)")
        if description.endswith("."):
            errors.append("pas de point final dans le titre")
    if len(title) > MAX_TITLE_LENGTH:
        errors.append(f"le titre fait {len(title)} caractères, {MAX_TITLE_LENGTH} caractères au plus")
    if len(lines) > 1 and lines[1].strip():
        errors.append("laisser une ligne vide entre le titre et le corps")
    if any(pattern.search("\n".join(lines)) for pattern in CLAUDE_MENTIONS):
        errors.append("aucune mention de Claude (ni Co-Authored-By, ni « Generated with Claude Code »)")
    return errors


def module_of(path: str) -> str | None:
    """Module of one file, as written between the parentheses of the header."""
    parts = list(PurePosixPath(path).parts)
    first = parts[0] if parts else ""
    if first == "backend" and len(parts) > 3 and parts[1] == "marmotte":
        return parts[2]
    if first == ".claude" or path == "CLAUDE.md":
        return "claude"
    if first == ".github":
        return "ci"
    if path == "README.md":
        return "docs"
    if first in TOP_LEVEL_MODULES:
        return first
    return None


def module_for(paths: list[str]) -> str | None:
    """Common module of the files; None when they differ or have none."""
    modules = {module_of(path) for path in paths}
    if len(modules) == 1:
        return modules.pop()
    if paths and all(path.startswith("backend/") for path in paths):
        # Several back-end packages, or a package and other back-end files: the whole back.
        return "backend"
    return None


def prefill(message: str, branch: str, paths: list[str], source: str) -> str:
    """Message with ``type(module): `` in front, when the branch gives a type and the message has none."""
    if source in ("merge", "squash", "commit"):
        return message
    match = BRANCH.match(branch)
    if match is None or match["type"] not in TYPES:
        return message
    lines = meaningful_lines(message)
    first = lines[0] if lines else ""
    if first.startswith(WRITTEN_BY_GIT) or HEADER.match(first):
        return message
    branch_type = match["type"]
    module = module_for(paths)
    header = f"{branch_type}({module}): " if module and module != branch_type else f"{branch_type}: "
    # With the editor, the template starts with an empty line: the header fills it.
    return header + message


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    return result.stdout.strip()


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in ("check", "prefill"):
        print("usage : commit_message.py check <fichier|->  |  commit_message.py prefill <fichier>", file=sys.stderr)
        return 2
    command, target = argv[0], argv[1]
    if command == "check":
        message = sys.stdin.read() if target == "-" else Path(target).read_text(encoding="utf-8")
        errors = check_message(message)
        if errors:
            print("Message de commit refusé :", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            print("Format : type(module): description, en anglais (CLAUDE.md, « Conventions »).", file=sys.stderr)
            return 1
        return 0
    path = Path(target)
    source = os.environ.get("PRE_COMMIT_COMMIT_MSG_SOURCE", argv[2] if len(argv) > 2 else "")
    branch = _git("symbolic-ref", "--short", "-q", "HEAD") or "HEAD"
    paths = _git("diff", "--cached", "--name-only").splitlines()
    message = path.read_text(encoding="utf-8")
    path.write_text(prefill(message, branch, paths, source), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
