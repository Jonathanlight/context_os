"""Tests for the Diagnostic model and DiagnosticBag collector."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from contextos.ast.common import Position
from contextos.diagnostics import (
    Diagnostic,
    DiagnosticBag,
    DiagSeverity,
)


class TestDiagnostic:
    def test_minimal_diagnostic(self) -> None:
        d = Diagnostic(code="A001", severity=DiagSeverity.WARNING, message="vague")
        assert d.code == "A001"
        assert d.severity == DiagSeverity.WARNING
        assert d.position is None
        assert d.suggestion is None
        assert d.doc_url is None

    def test_full_diagnostic(self) -> None:
        d = Diagnostic(
            code="S001",
            severity=DiagSeverity.ERROR,
            message="description too vague",
            position=Position(file="x.md", line=3, column=14),
            suggestion="describe input and output",
            doc_url="https://contextos.dev/rules/S001",
        )
        assert d.position is not None
        assert d.position.line == 3

    def test_is_frozen(self) -> None:
        d = Diagnostic(code="A001", severity=DiagSeverity.INFO, message="m")
        with pytest.raises(ValidationError):
            d.code = "B001"  # type: ignore[misc]

    def test_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            Diagnostic(
                code="A001",
                severity=DiagSeverity.INFO,
                message="m",
                extras={},  # type: ignore[call-arg]
            )

    @pytest.mark.parametrize(
        "valid_code",
        ["A001", "S010", "XA001", "R012", "VERYLONG999"],
    )
    def test_accepts_valid_code(self, valid_code: str) -> None:
        # Per SPEC §2: category prefix (A/C/K/S/R/XA) + 3+ digits, no hyphen.
        d = Diagnostic(code=valid_code, severity=DiagSeverity.INFO, message="m")
        assert d.code == valid_code

    @pytest.mark.parametrize(
        "invalid_code",
        ["a001", "001A", "A01", "", "A0Z1", "LINT-001"],
    )
    def test_rejects_invalid_code(self, invalid_code: str) -> None:
        # Rule.id uses A-001 (with hyphen); Diagnostic.code uses S001 (no
        # hyphen) per SPEC.md §2.4. Hyphenated codes belong to rules, not
        # diagnostics.
        with pytest.raises(ValidationError):
            Diagnostic(code=invalid_code, severity=DiagSeverity.INFO, message="m")

    def test_empty_message_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Diagnostic(code="A001", severity=DiagSeverity.INFO, message="")

    def test_round_trips_via_json(self) -> None:
        original = Diagnostic(
            code="S001",
            severity=DiagSeverity.ERROR,
            message="vague",
            position=Position(file="x.md", line=1, column=2),
            suggestion="be specific",
            doc_url="https://x/y",
        )
        restored = Diagnostic.model_validate_json(original.model_dump_json())
        assert restored == original

    def test_is_hashable(self) -> None:
        d = Diagnostic(code="A001", severity=DiagSeverity.INFO, message="m")
        s: set[Diagnostic] = {d, d}
        assert len(s) == 1


class TestDiagSeverity:
    def test_values_are_lowercase(self) -> None:
        assert DiagSeverity.ERROR.value == "error"
        assert DiagSeverity.WARNING.value == "warning"
        assert DiagSeverity.INFO.value == "info"


class TestDiagnosticBag:
    def _diag(
        self,
        code: str = "A001",
        sev: DiagSeverity = DiagSeverity.INFO,
        line: int | None = None,
    ) -> Diagnostic:
        return Diagnostic(
            code=code,
            severity=sev,
            message="m",
            position=Position(line=line) if line is not None else None,
        )

    def test_empty_bag(self) -> None:
        bag = DiagnosticBag()
        assert len(bag) == 0
        assert bag.count() == 0
        assert not bag.has_errors()
        assert not bool(bag)

    def test_add_and_iterate_preserves_order(self) -> None:
        bag = DiagnosticBag()
        bag.add(self._diag("A001"))
        bag.add(self._diag("A002"))
        codes = [d.code for d in bag]
        assert codes == ["A001", "A002"]

    def test_extend(self) -> None:
        bag = DiagnosticBag()
        bag.extend([self._diag("A001"), self._diag("A002")])
        assert len(bag) == 2

    def test_count_by_severity(self) -> None:
        bag = DiagnosticBag(
            [
                self._diag(sev=DiagSeverity.ERROR),
                self._diag(sev=DiagSeverity.ERROR),
                self._diag(sev=DiagSeverity.WARNING),
                self._diag(sev=DiagSeverity.INFO),
            ]
        )
        assert bag.count() == 4
        assert bag.count(DiagSeverity.ERROR) == 2
        assert bag.count(DiagSeverity.WARNING) == 1
        assert bag.count(DiagSeverity.INFO) == 1

    def test_has_errors_true(self) -> None:
        bag = DiagnosticBag([self._diag(sev=DiagSeverity.ERROR)])
        assert bag.has_errors()

    def test_has_errors_false_when_only_warnings(self) -> None:
        bag = DiagnosticBag([self._diag(sev=DiagSeverity.WARNING)])
        assert not bag.has_errors()

    def test_sorted_by_position_then_code(self) -> None:
        bag = DiagnosticBag(
            [
                self._diag("Z999", line=10),
                self._diag("A001", line=5),
                self._diag("B002"),  # no position — sorts first
                self._diag("A001", line=5),  # same line, same code, stable
            ]
        )
        ordered = bag.sorted()
        # No-position diagnostic comes first.
        assert ordered[0].code == "B002"
        # Then by line: 5, 5, 10.
        assert ordered[1].position is not None
        assert ordered[1].position.line == 5
        assert ordered[-1].position is not None
        assert ordered[-1].position.line == 10

    def test_contains(self) -> None:
        d = self._diag("A001")
        bag = DiagnosticBag([d])
        assert d in bag
