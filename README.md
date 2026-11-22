# 返修试验线工位占用与交班归档

白班工艺员登记完整返修规程，质控分析员按源修订固定当班计划，再按试行比例复核每条路线。排班员用正式报告中的两列长期占比安排复核。白班更正源规程后，夜班可以断源重开归档，凭原计划号重新核账，凭原报告号领取报告和回执。

## 运行

在项目根目录使用 Python 3.11。SQLite 和其他依赖均来自标准库。

```sh
python3 -B -S verify.py
python3 -B -S -m unittest discover -s tests
python3 -B -S demo.py
```

演示从 `examples/day.json` 读取白班规程，再从 `examples/correction.json` 登记更正。它将两套成果写入临时归档，关闭并移开源数据库，从重开归档核对旧路线、旧报告和回执。测试与演示结束时清理各自的临时目录。样例从 A 工位开工，在 `1/4` 比例下两条原路线概率分别为 `1/8` 和 `1/32`。旧报告的完全关闭列为 `(1, 0)`，微量放行列为 `(0, 1)`，均按 `(A, B)` 顺序。

## 计算约定

- 工位名称和路线编号为非空白字符串，各自在一次修订内唯一。输入工位、开工分布和路线使用有序集合。工位可以使用字符串或 `routing.stations.Station`，路线使用 `routing.routes.RouteRule`。开工分布按工位位置提供，非负且合计为一。
- 概率输入接受 `Fraction`、整数和精确有理字符串，例如 `1/4`。布尔值、浮点值和空值会被拒绝。路线基准概率非负，放行次数为整数 `0`、`1` 或 `2`。每个出发工位的全量概率预算至多为一。
- 每步路线概率为基准概率乘以放行比例的对应次幂。零次放行条件保持基准概率。同端点路线的核账行按原身份分别返回，显式零概率路线也有一行。各工位的留驻余量是扣除其所有转送路线后的剩余概率。矩阵合并平行路线，显式本站路线与留驻余量一起计入对角。
- 固定计划包含二至六个工位，严格正比例下所有工位互达。完全关闭的长期占用取决于开工分布和零比例时流入各闭类的概率。微量放行列先取正比例下的长期时间平均，再令比例趋近于零。周期链也使用长期时间平均。两列按原工位顺序返回精确 `Fraction`，各自和为一。

## Python 接口

| 入口 | 返回 |
| --- | --- |
| `routing.intake.record_revision(source, stations, initial, routes)` | 新的不可变源修订号 |
| `plan.freeze.freeze_plan(source, archive, revision_id)` | 持久的固定计划号 |
| `plan.audit.audit_plan(archive, plan_id, ratio)` | `AuditResult`，包含原工位、逐路线 `RouteAuditRow` 与逐工位留驻余量 |
| `publication.issue.issue_report(archive, plan_id)` | 同次提交的 `(OccupationReport, IssueReceipt)` |
| `publication.read.read_report(archive, report_id)` | 原样读回 `(OccupationReport, IssueReceipt)` |

调用方用 `routing.revision_store.RevisionStore(path)` 打开源库，用 `archive.catalog.HandoverArchive.open(path)` 打开另一个本地 SQLite 文件。两者支持 `with` 和显式 `close()`。打开时初始化缺失的结构，重复调用 `initialize()` 保留已有数据。登记更正后的整份规程会产生新修订号。冻结快照保留源修订出处、原工位顺序、开工分布、路线身份、基准概率和放行次数。归档分数按规范字符串保存，编号是用于查询的独立身份。

```python
from archive.catalog import HandoverArchive
from plan.audit import audit_plan
from plan.freeze import freeze_plan
from publication.issue import issue_report
from publication.read import read_report
from routing.intake import record_revision
from routing.revision_store import RevisionStore
from routing.routes import RouteRule

routes = (
    RouteRule('outbound', 'A', 'B', '1/2', 1),
    RouteRule('return', 'B', 'A', '1/2', 2),
)
with RevisionStore('routing.sqlite') as source, HandoverArchive.open('handover.sqlite') as archive:
    revision_id = record_revision(source, ('A', 'B'), (1, 0), routes)
    plan_id = freeze_plan(source, archive, revision_id)
    audit = audit_plan(archive, plan_id, '1/4')
    report, receipt = issue_report(archive, plan_id)

with HandoverArchive.open('handover.sqlite') as archive:
    original = read_report(archive, report.report_id)
```

非法输入、比例和计划资格抛 `ValueError`。未知修订、计划或报告号抛 `KeyError`。登记、固定和签发均在相应存储操作成功后返回。报告与成功回执同一事务提交。可选 `before_commit` 回调在两条写入暂存后、提交前调用，回调抛错时本次签发回滚。回调只观察或注入异常，事务由归档管理。SQLite 异常向调用方传播。失败后可以继续读取已经提交的历史件。
