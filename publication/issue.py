from collections.abc import Callable
from uuid import uuid4

from analysis.occupation import forecast_occupation
from archive.catalog import HandoverArchive
from archive.plan_store import PlanStore
from archive.report_store import ReportStore
from publication.encoding import encode_receipt, encode_report
from publication.receipt import IssueReceipt, make_receipt
from publication.report import OccupationReport, validate_report


def issue_report(
    archive: HandoverArchive,
    plan_id: str,
    *,
    before_commit: Callable[[], None] | None = None,
) -> tuple[OccupationReport, IssueReceipt]:
    plan = PlanStore(archive).load(plan_id)
    draft = forecast_occupation(plan)
    if draft.plan_id != plan.plan_id or draft.stations != plan.stations:
        raise ValueError('occupation draft does not match the requested plan')
    report = validate_report(OccupationReport(f'report-{uuid4().hex}', draft.plan_id, draft.stations, draft.zero, draft.rare))
    receipt = make_receipt(report)
    ReportStore(archive).commit_issue(
        report.report_id,
        report.plan_id,
        encode_report(report),
        encode_receipt(receipt),
        before_commit=before_commit,
    )
    return report, receipt
