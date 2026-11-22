import json

from archive.catalog import HandoverArchive
from archive.transactions import write_transaction
from plan.snapshot import FrozenPlan, FrozenRoute, validate_snapshot
from routing.stations import validate_identity


class PlanStore:
    def __init__(self, archive: HandoverArchive):
        self.connection = archive.connection

    def save(self, plan: FrozenPlan) -> None:
        plan = validate_snapshot(plan)
        payload = json.dumps({
            'stations': plan.stations,
            'initial': [str(mass) for mass in plan.initial],
            'routes': [
                [route.route_id, route.source, route.destination, str(route.base_probability), route.releases]
                for route in plan.routes
            ],
        }, ensure_ascii=False)
        with write_transaction(self.connection):
            self.connection.execute(
                'INSERT INTO plans (plan_id, revision_id, payload) VALUES (?, ?, ?)',
                (plan.plan_id, plan.revision_id, payload),
            )

    def load(self, plan_id: str) -> FrozenPlan:
        validate_identity(plan_id, 'plan identity')
        row = self.connection.execute(
            'SELECT revision_id, payload FROM plans WHERE plan_id = ?', (plan_id,),
        ).fetchone()
        if row is None:
            raise KeyError(plan_id)
        try:
            revision_id, payload = row
            value = json.loads(payload)
            return validate_snapshot(FrozenPlan(
                plan_id,
                revision_id,
                value['stations'],
                value['initial'],
                tuple(FrozenRoute(*route) for route in value['routes']),
            ))
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f'invalid fixed plan payload for {plan_id!r}') from error
