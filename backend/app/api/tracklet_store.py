"""Process-local store of built tracklets for the identify endpoint.

MVP only: in memory, lost on restart, not shared between workers. Keeps
the most recent `max_builds` builds (FIFO eviction).
"""

from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock

from app.models.observation import Observation
from app.models.pipeline_config import PipelineConfig
from app.models.tracklet import Tracklet


DEFAULT_MAX_BUILDS = 20


@dataclass(frozen=True)
class StoredTracklet:
    tracklet: Tracklet
    observations: list[Observation]
    config: PipelineConfig


class TrackletStore:
    def __init__(self, max_builds: int = DEFAULT_MAX_BUILDS) -> None:
        self._max_builds = max_builds
        self._builds: OrderedDict[str, dict[str, StoredTracklet]] = OrderedDict()
        self._lock = Lock()

    def add_build(
        self,
        build_id: str,
        tracklets: list[Tracklet],
        observations: list[Observation],
        config: PipelineConfig,
    ) -> None:
        entries = {
            tracklet.tracklet_id: StoredTracklet(tracklet, observations, config)
            for tracklet in tracklets
        }
        with self._lock:
            self._builds[build_id] = entries
            while len(self._builds) > self._max_builds:
                self._builds.popitem(last=False)

    def get(self, tracklet_id: str) -> StoredTracklet | None:
        with self._lock:
            for entries in self._builds.values():
                if tracklet_id in entries:
                    return entries[tracklet_id]
        return None


tracklet_store = TrackletStore()


def get_tracklet_store() -> TrackletStore:
    return tracklet_store
