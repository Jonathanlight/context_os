"""Tests for the P* platform rules."""

from __future__ import annotations

import pytest

from contextos.analyzers.agent import platform
from contextos.ast.agent import AgentDocument, Rule
from contextos.ast.common import Position, Severity
from contextos.diagnostics import DiagSeverity


def _rule(title: str) -> Rule:
    return Rule(
        id="X-001",
        title=title,
        severity=Severity.MUST,
        position=Position(file="x.md", line=10),
    )


def _codes(title: str) -> list[str]:
    return [d.code for d in platform.check(AgentDocument(rules=[_rule(title)]))]


class TestP001PersonalPath:
    @pytest.mark.parametrize(
        "title",
        [
            "Store credentials in /Users/jonathan/.config/myapp/secrets.json",
            "Run /home/alice/bin/check.sh before every PR",
            r"Logs land in C:\Users\bob\AppData\Roaming\MyApp\logs",
        ],
    )
    def test_detects_personal_paths(self, title: str) -> None:
        assert "P001" in _codes(title)

    @pytest.mark.parametrize(
        "title",
        [
            "Store credentials under ~/.config/myapp/",
            "Use a project-relative path like ./config",
            "Symlink /usr/local/bin/foo to a wrapper",  # /usr/local — not personal
            "Read /etc/myapp/config",
        ],
    )
    def test_does_not_flag_portable_paths(self, title: str) -> None:
        assert "P001" not in _codes(title)

    def test_message_names_matched_path(self) -> None:
        diags = list(platform.check(AgentDocument(rules=[_rule("Read /Users/jonathan/file.txt")])))
        p001 = next(d for d in diags if d.code == "P001")
        assert "/Users/jonathan" in p001.message

    def test_severity_is_warning(self) -> None:
        diags = list(platform.check(AgentDocument(rules=[_rule("Read /Users/jonathan/file.txt")])))
        p001 = next(d for d in diags if d.code == "P001")
        assert p001.severity == DiagSeverity.WARNING


class TestP002Email:
    @pytest.mark.parametrize(
        "title",
        [
            "Send build failures to ops@example.com",
            "Approval required from jonathan.kablan@example.com",
            "Ping security+oncall@acme.io before changing auth code",
        ],
    )
    def test_detects_email(self, title: str) -> None:
        assert "P002" in _codes(title)

    @pytest.mark.parametrize(
        "title",
        [
            "Notify the ops team on every build failure",
            "Approval required from the platform team",
            "Use @ as the array-spread marker in TypeScript",
            "twitter-style @mentions are OK in titles",
        ],
    )
    def test_does_not_flag_non_emails(self, title: str) -> None:
        assert "P002" not in _codes(title)

    def test_message_names_email(self) -> None:
        diags = list(platform.check(AgentDocument(rules=[_rule("CC ops@example.com on every PR")])))
        p002 = next(d for d in diags if d.code == "P002")
        assert "ops@example.com" in p002.message


class TestP003BareUrl:
    @pytest.mark.parametrize(
        "title",
        [
            "Read the deploy runbook at https://example.com/runbooks/deploy",
            "Reject requests to http://internal.example.com/admin",
            "Spec lives at https://contextos.dev/rules/P001",
        ],
    )
    def test_detects_url(self, title: str) -> None:
        assert "P003" in _codes(title)

    @pytest.mark.parametrize(
        "title",
        [
            "Read the deploy runbook before any prod change",
            "OAuth tokens documented in the wiki",
            "Use HTTPS for every outbound request",  # mentions HTTPS but no URL
        ],
    )
    def test_does_not_flag_descriptions(self, title: str) -> None:
        assert "P003" not in _codes(title)

    def test_message_names_url(self) -> None:
        diags = list(platform.check(AgentDocument(rules=[_rule("Doc at https://example.com/foo")])))
        p003 = next(d for d in diags if d.code == "P003")
        assert "https://example.com/foo" in p003.message


class TestCheckIntegration:
    def test_empty_agent_yields_nothing(self) -> None:
        assert list(platform.check(AgentDocument())) == []

    def test_multiple_p_rules_can_co_fire(self) -> None:
        # A title containing both a personal path AND an email.
        rule = _rule("Email /Users/alice/path summary to ops@example.com")
        codes = [d.code for d in platform.check(AgentDocument(rules=[rule]))]
        assert "P001" in codes
        assert "P002" in codes

    def test_source_kwarg_accepted(self) -> None:
        list(platform.check(AgentDocument(rules=[_rule("Use HTTPS")]), source="x.md"))
