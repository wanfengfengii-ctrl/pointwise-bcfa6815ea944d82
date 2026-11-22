import json

from publication.receipt import IssueReceipt
from publication.report import OccupationReport, validate_report
from routing.stations import validate_identity


def encode_report(report: OccupationReport) -> str:
    report = validate_report(report)
    return json.dumps({
        'report_id': report.report_id,
        'plan_id': report.plan_id,
        'stations': report.stations,
        'zero': [str(mass) for mass in report.zero],
        'rare': [str(mass) for mass in report.rare],
    }, ensure_ascii=False)


def decode_report(payload: str) -> OccupationReport:
    try:
        value = json.loads(payload)
        return validate_report(OccupationReport(
            value['report_id'], value['plan_id'], value['stations'], value['zero'], value['rare'],
        ))
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('invalid archived occupation report') from error


def encode_receipt(receipt: IssueReceipt) -> str:
    return json.dumps({
        'report_id': validate_identity(receipt.report_id, 'receipt report identity'),
        'plan_id': validate_identity(receipt.plan_id, 'receipt plan identity'),
    }, ensure_ascii=False)


def decode_receipt(payload: str) -> IssueReceipt:
    try:
        value = json.loads(payload)
        return IssueReceipt(
            validate_identity(value['report_id'], 'receipt report identity'),
            validate_identity(value['plan_id'], 'receipt plan identity'),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('invalid archived issue receipt') from error
