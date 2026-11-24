import pytest

from .commit_message import check_message
from .commit_message import module_for
from .commit_message import prefill

EDITOR_TEMPLATE = "\n# Please enter the commit message for your changes.\n#\n# On branch feat/4-cry-detection\n"


class TestCheckMessage:
    @pytest.mark.parametrize(
        "message",
        [
            "feat(backend): add Django project with health endpoint",
            "chore: add pre-commit hooks and just recipes",
            "fix(claude): fix backlog sync\n\nThe REST API gives the state reason.\n",
            "chore(deps-dev): bump vitest from 5.1.1 to 5.2.0",
            "docs: update README links",
            "feat(api): API keys for devices",
        ],
    )
    def test_accepts_conventional_messages(self, message: str) -> None:
        """Messages that follow the convention pass."""
        # WHEN / THEN
        assert check_message(message) == []

    @pytest.mark.parametrize(
        "message",
        [
            "Merge branch 'main' into feat/4-cry-detection",
            'Revert "feat(backend): add health endpoint"',
            "fixup! feat(backend): add health endpoint",
        ],
    )
    def test_accepts_messages_written_by_git(self, message: str) -> None:
        """Merges, reverts and fixups written by Git pass."""
        # WHEN / THEN
        assert check_message(message) == []

    def test_ignores_comment_lines(self) -> None:
        """Lines starting with # are comments: Git removes them."""
        # WHEN / THEN
        assert check_message("feat(backend): add x\n# Please enter the commit message\n") == []

    @pytest.mark.parametrize(
        ("message", "expected"),
        [
            ("add health endpoint", "type(module): description"),
            ("feature(backend): add x", "type inconnu"),
            ("feat(backend): Add x", "minuscule"),
            ("feat(backend): add x.", "point final"),
            ("feat(backend): ", "description est vide"),
            ("feat(Backend): add x", "type(module): description"),
            ("feat(backend): " + "a" * 60, "72 caractères"),
            ("feat(backend): add x\nbody without blank line", "ligne vide"),
            ("feat(backend): add x\n\nCo-Authored-By: Claude Opus <noreply@anthropic.com>", "Claude"),
            ("feat(backend): add x\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)", "Claude"),
            ("", "vide"),
            ("# only a comment\n", "vide"),
        ],
    )
    def test_refuses_with_a_clear_reason(self, message: str, expected: str) -> None:
        """A message outside the convention is refused with a reason in French."""
        # WHEN
        errors = check_message(message)
        # THEN
        assert any(expected in error for error in errors), errors


class TestModuleFor:
    @pytest.mark.parametrize(
        ("paths", "expected"),
        [
            (["backend/marmotte/detection/audio.py", "backend/marmotte/detection/tests/test_audio.py"], "detection"),
            (["backend/marmotte/api.py", "backend/pyproject.toml"], "backend"),
            (["backend/marmotte/base/views/health.py", "backend/marmotte/api.py"], "backend"),
            (["frontend/src/App.tsx"], "frontend"),
            ([".claude/skills/commit/SKILL.md", "CLAUDE.md"], "claude"),
            (["docs/plans/x.md", "README.md"], "docs"),
            ([".github/workflows/ci.yml"], "ci"),
            (["backend/manage.py", "frontend/src/App.tsx"], None),
            (["justfile"], None),
            ([], None),
        ],
    )
    def test_guesses_the_module_from_paths(self, paths: list[str], expected: str | None) -> None:
        """The module comes from the staged paths, or is left out when they differ."""
        # WHEN / THEN
        assert module_for(paths) == expected


class TestPrefill:
    def test_opens_the_editor_on_the_header(self) -> None:
        """With the editor, the header is written on the first line, before Git's comments."""
        # WHEN
        message = prefill(EDITOR_TEMPLATE, "feat/4-cry-detection", ["backend/marmotte/detection/audio.py"], "")
        # THEN
        assert message.startswith("feat(detection): \n# Please enter")

    def test_prefixes_a_message_given_with_m(self) -> None:
        """git commit -m "add x" gets the header in front of the text."""
        # WHEN
        message = prefill("add audio sources\n", "feat/4-cry-detection", ["backend/marmotte/detection/a.py"], "message")
        # THEN
        assert message == "feat(detection): add audio sources\n"

    def test_leaves_out_the_module_when_files_differ(self) -> None:
        """Files from several modules give a header without module."""
        # WHEN
        message = prefill(
            "bump tools\n", "chore/tooling", ["backend/pyproject.toml", "frontend/package.json"], "message"
        )
        # THEN
        assert message == "chore: bump tools\n"

    def test_leaves_out_a_module_equal_to_the_type(self) -> None:
        """A ci branch touching .github/ gives "ci: ", not "ci(ci): "."""
        # WHEN
        message = prefill("pin setup-uv\n", "ci/fix-setup-uv-version", [".github/workflows/ci.yml"], "message")
        # THEN
        assert message == "ci: pin setup-uv\n"

    @pytest.mark.parametrize(
        ("message", "branch", "source"),
        [
            ("feat(backend): add x\n", "feat/4-cry-detection", "message"),
            ("docs(claude): explain x\n", "feat/4-cry-detection", "message"),
            ("add x\n", "main", "message"),
            ("add x\n", "HEAD", "message"),
            ("add x\n", "wip-without-type", "message"),
            ("add x\n", "feature/4-x", "message"),
            ("Merge branch 'main'\n", "feat/4-cry-detection", "merge"),
            ("feat(backend): add x\n", "feat/4-cry-detection", "commit"),
            ("squash! add x\n", "feat/4-cry-detection", "message"),
        ],
    )
    def test_leaves_the_message_alone(self, message: str, branch: str, source: str) -> None:
        """Already formatted, on main, unknown branch type, merge, amend or squash: unchanged."""
        # WHEN / THEN
        assert prefill(message, branch, ["backend/manage.py"], source) == message
