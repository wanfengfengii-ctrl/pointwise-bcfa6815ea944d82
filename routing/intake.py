from collections.abc import Iterable
from uuid import uuid4

from routing.revision_store import RevisionStore
from routing.revisions import build_revision
from routing.routes import RouteRule
from routing.stations import RationalInput, Station


def record_revision(
    source: RevisionStore,
    stations: Iterable[Station | str],
    initial: Iterable[RationalInput],
    routes: Iterable[RouteRule],
) -> str:
    """Append a full revision and return its durable identity."""
    revision = build_revision(f'rev-{uuid4().hex}', stations, initial, routes)
    source.append(revision)
    return revision.revision_id
