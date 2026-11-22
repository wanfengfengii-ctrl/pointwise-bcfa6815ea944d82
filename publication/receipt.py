from dataclasses import dataclass

from publication.report import OccupationReport
from routing.stations import validate_identity


@dataclass(frozen=True, slots=True)
class IssueReceipt:
    report_id: str
    plan_id: str


def make_receipt(report: OccupationReport) -> IssueReceipt:
    return IssueReceipt(
        validate_identity(report.report_id, 'receipt report identity'),
        validate_identity(report.plan_id, 'receipt plan identity'),
    )


def validate_receipt_binding(report: OccupationReport, receipt: IssueReceipt) -> None:
    if receipt != make_receipt(report):
        raise ValueError('issue receipt does not match its report and plan')
