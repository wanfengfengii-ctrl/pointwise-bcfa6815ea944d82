import json
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory

from archive.catalog import HandoverArchive
from archive.plan_store import PlanStore
from demo import audit_columns, load_shift, prepare_shift, report_columns
from plan.audit import audit_plan
from plan.snapshot import FrozenPlan, FrozenRoute
from publication.issue import issue_report
from routing.revision_store import RevisionStore


EXPECTED = {
    "audit": {
        "routes": [["outbound", "1/8"], ["return", "1/32"]],
        "remaining": [["A", "7/8"], ["B", "31/32"]],
    },
    "report": {"stations": ["A", "B"], "zero": ["1", "0"], "rare": ["0", "1"]},
}


def prepare_cases(source, archive):
    _, shift_audit = prepare_shift(source, archive, load_shift("day.json"))
    independent = FrozenPlan(
        "offsite-plan", "offsite-revision", ("A", "B"), (Fraction(1), Fraction(0)),
        (
            FrozenRoute("outbound", "A", "B", Fraction(1, 2), 1),
            FrozenRoute("return", "B", "A", Fraction(1, 2), 2),
        ),
    )
    PlanStore(archive).save(independent)
    return {"shift": shift_audit.plan_id, "independent": independent.plan_id}


def measure_cases(archive, plan_ids):
    actual = {}
    for name, plan_id in plan_ids.items():
        audit = audit_plan(archive, plan_id, "1/4")
        report, _ = issue_report(archive, plan_id)
        actual[name] = {"audit": audit_columns(audit), "report": report_columns(report)}
    return actual


def main():
    with TemporaryDirectory(prefix="occupation-incident-") as temporary:
        source_path = Path(temporary) / "routing.sqlite"
        archive_path = Path(temporary) / "handover.sqlite"
        with RevisionStore(source_path) as source, HandoverArchive.open(archive_path) as archive:
            plan_ids = prepare_cases(source, archive)
        source_path.rename(source_path.with_suffix(".offline"))
        with HandoverArchive.open(archive_path) as archive:
            actual = measure_cases(archive, plan_ids)
    print(json.dumps({"expected": EXPECTED, "actual": actual}, ensure_ascii=False, sort_keys=True))
    if any(result != EXPECTED for result in actual.values()):
        print("OCCUPANCY_HANDOFF_MISMATCH")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
