from collections.abc import Callable

from archive.catalog import HandoverArchive
from archive.transactions import write_transaction
from routing.stations import validate_identity


class ReportStore:
    def __init__(self, archive: HandoverArchive):
        self.connection = archive.connection

    def commit_issue(
        self,
        report_id: str,
        plan_id: str,
        report_payload: str,
        receipt_payload: str,
        *,
        before_commit: Callable[[], None] | None = None,
    ) -> None:
        with write_transaction(self.connection):
            self.connection.execute(
                'INSERT INTO reports (report_id, plan_id, payload) VALUES (?, ?, ?)',
                (report_id, plan_id, report_payload),
            )
            self.connection.execute(
                'INSERT INTO receipts (report_id, payload) VALUES (?, ?)',
                (report_id, receipt_payload),
            )
            if before_commit is not None:
                before_commit()

    def load_issue(self, report_id: str) -> tuple[str, str, str]:
        validate_identity(report_id, 'report identity')
        row = self.connection.execute('''
            SELECT reports.plan_id, reports.payload, receipts.payload
            FROM reports
            JOIN receipts ON receipts.report_id = reports.report_id
            WHERE reports.report_id = ?
        ''', (report_id,)).fetchone()
        if row is None:
            raise KeyError(report_id)
        return row
