import json
from pathlib import Path
from tempfile import TemporaryDirectory

from archive.catalog import HandoverArchive
from plan.audit import audit_plan
from plan.freeze import freeze_plan
from publication.issue import issue_report
from publication.read import read_report
from routing.intake import record_revision
from routing.revision_store import RevisionStore
from routing.routes import RouteRule


EXAMPLES = Path(__file__).resolve().parent / 'examples'


def load_shift(name):
    return json.loads((EXAMPLES / name).read_text(encoding='utf-8'))


def prepare_shift(source, archive, shift):
    revision_id = record_revision(
        source, shift['stations'], shift['initial'], tuple(RouteRule(**route) for route in shift['routes']),
    )
    plan_id = freeze_plan(source, archive, revision_id)
    return revision_id, audit_plan(archive, plan_id, shift['audit_ratio'])


def audit_columns(audit):
    return {
        'routes': [[row.route_id, str(row.probability)] for row in audit.routes],
        'remaining': [[station, str(mass)] for station, mass in zip(audit.stations, audit.remaining, strict=True)],
    }


def report_columns(report):
    return {
        'stations': list(report.stations),
        'zero': [str(value) for value in report.zero],
        'rare': [str(value) for value in report.rare],
    }


def check_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(f'{label} expected {expected!r}, received {actual!r}')


def main():
    day = load_shift('day.json')
    correction = load_shift('correction.json')
    with TemporaryDirectory(prefix='repair-handover-') as temporary:
        source_path = Path(temporary) / 'routing.sqlite'
        archive_path = Path(temporary) / 'handover.sqlite'
        with RevisionStore(source_path) as source, HandoverArchive.open(archive_path) as archive:
            source.initialize()
            archive.initialize()
            first_revision, day_audit = prepare_shift(source, archive, day)
            day_issue = issue_report(archive, day_audit.plan_id)
            correction_revision, correction_audit = prepare_shift(source, archive, correction)
            correction_issue = issue_report(archive, correction_audit.plan_id)
            if first_revision == correction_revision or day_issue[0].report_id == correction_issue[0].report_id:
                raise AssertionError('the two shifts must have separate archival identities')
        source_path.rename(source_path.with_suffix('.offline'))
        with HandoverArchive.open(archive_path) as archive:
            night_audit = audit_plan(archive, day_audit.plan_id, day['audit_ratio'])
            night_issue = read_report(archive, day_issue[0].report_id)
            check_equal(read_report(archive, correction_issue[0].report_id), correction_issue, 'corrected issue')
            check_equal(night_audit, day_audit, 'original audit after reopening')
            check_equal(night_issue, day_issue, 'original issue and receipt after reopening')

        expected_audit = {'routes': [['outbound', '1/8'], ['return', '1/32']], 'remaining': [['A', '7/8'], ['B', '31/32']]}
        expected_report = {'stations': ['A', 'B'], 'zero': ['1', '0'], 'rare': ['0', '1']}
        actual_audit, offline_audit = audit_columns(day_audit), audit_columns(night_audit)
        actual_report, offline_report = report_columns(day_issue[0]), report_columns(night_issue[0])
        check_equal(actual_audit, expected_audit, 'day-shift audit')
        check_equal(actual_report, expected_report, 'day-shift occupation')
        check_equal(report_columns(correction_issue[0]), {'stations': ['A', 'B'], 'zero': ['1', '0'], 'rare': ['1', '0']}, 'corrected occupation')
        check_equal((night_issue[1].report_id, night_issue[1].plan_id), (night_issue[0].report_id, night_audit.plan_id), 'night-shift receipt binding')
        print('POINTWISE_SCENARIO ' + json.dumps({
            'case_id': 'v_reopen.first_task_quarter',
            'input': {'original': day, 'correction': correction, 'source_disconnected': not source_path.exists()},
            'expected': {'audit': expected_audit, 'report': expected_report},
            'actual': {'audit': actual_audit, 'report': actual_report},
            'downstream_expected': {'audit': expected_audit, 'report': expected_report, 'original_receipt': True},
            'downstream_actual': {'audit': offline_audit, 'report': offline_report, 'original_receipt': night_issue[1] == day_issue[1]},
            'code_paths': ['routing/intake.py', 'plan/freeze.py', 'plan/audit.py', 'analysis/occupation.py', 'analysis/rare_limit.py', 'publication/issue.py', 'publication/read.py', 'archive/report_store.py'],
            'oracle': 'Substitute x=1/4 into x/2 and x squared over 2. At x=0 A retains the opening mass. Positive-ratio flow balance gives B a mass of 1/(1+x).',
        }, ensure_ascii=False, sort_keys=True))
        print(f'夜班凭 {night_issue[0].report_id} 领取原报告和回执。')
        for station, zero, rare in zip(night_issue[0].stations, night_issue[0].zero, night_issue[0].rare, strict=True):
            print(f'{station} 工位完全关闭占比 {zero}，微量放行极限占比 {rare}')


if __name__ == '__main__':
    main()
