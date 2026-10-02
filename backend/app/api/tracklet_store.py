"""Process-local store of built tracklets for the identify and review
ranking endpoints.

MVP only: in memory, lost on restart, not shared between workers. Keeps
the most recent `max_builds` builds (FIFO eviction).
"""

from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class StoredBuild:
    """One whole build: every tracklet in build order, plus the raw `sharp`
    of their detections (for the M1 review ranking)."""

    build_id: str
    tracklets: list[Tracklet]
    observations: list[Observation]
    config: PipelineConfig
    sharp_by_source_id: Mapping[str, float] = field(default_factory=dict)


class TrackletStore:
    def __init__(self, max_builds: int = DEFAULT_MAX_BUILDS) -> None:
        self._max_builds = max_builds
        self._builds: OrderedDict[str, StoredBuild] = OrderedDict()
        self._tracklets: dict[str, dict[str, StoredTracklet]] = {}
        self._lock = Lock()

    def add_build(
        self,
        build_id: str,
        tracklets: list[Tracklet],
        observations: list[Observation],
        config: PipelineConfig,
        sharp_by_source_id: Mapping[str, float] | None = None,
    ) -> None:
        build = StoredBuild(
            build_id, list(tracklets), observations, config, dict(sharp_by_source_id or {})
        )
        entries = {
            tracklet.tracklet_id: StoredTracklet(tracklet, observations, config)
            for tracklet in tracklets
        }
        with self._lock:
            self._builds[build_id] = build
            self._tracklets[build_id] = entries
            while len(self._builds) > self._max_builds:
                evicted, _ = self._builds.popitem(last=False)
                del self._tracklets[evicted]

    def get(self, tracklet_id: str) -> StoredTracklet | None:
        with self._lock:
            for build_id in self._builds:
                entries = self._tracklets[build_id]
                if tracklet_id in entries:
                    return entries[tracklet_id]
        return None

    def get_build(self, build_id: str) -> StoredBuild | None:
        with self._lock:
            return self._builds.get(build_id)


tracklet_store = TrackletStore()


def get_tracklet_store() -> TrackletStore:
    return tracklet_store
