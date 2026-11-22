from uuid import uuid4

from archive.catalog import HandoverArchive
from archive.plan_store import PlanStore
from plan.eligibility import check_eligibility
from plan.snapshot import FrozenPlan, FrozenRoute
from routing.revision_store import RevisionStore


def freeze_plan(source: RevisionStore, archive: HandoverArchive, revision_id: str) -> str:
    revision = source.get(revision_id)
    stations = tuple(station.name for station in revision.stations)
    check_eligibility(stations, revision.routes)
    routes = tuple(
        FrozenRoute(route.route_id, route.source, route.destination, route.base_probability, int(bool(route.releases)))
        for route in revision.routes
    )
    plan = FrozenPlan(f"plan-{uuid4().hex}", revision.revision_id, stations, revision.initial, routes)
    PlanStore(archive).save(plan)
    return plan.plan_id
