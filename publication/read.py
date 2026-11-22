from archive.catalog import HandoverArchive
from archive.report_store import ReportStore
from publication.encoding import decode_receipt, decode_report
from publication.receipt import IssueReceipt, validate_receipt_binding
from publication.report import OccupationReport


def read_report(archive: HandoverArchive, report_id: str) -> tuple[OccupationReport, IssueReceipt]:
    indexed_plan_id, report_payload, receipt_payload = ReportStore(archive).load_issue(report_id)
    report = decode_report(report_payload)
    if report.report_id != report_id or report.plan_id != indexed_plan_id:
        raise ValueError('archived report does not match its index')
    receipt = decode_receipt(receipt_payload)
    validate_receipt_binding(report, receipt)
    return report, receipt
