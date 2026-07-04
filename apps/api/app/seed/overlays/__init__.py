"""Hand-curated course knowledge: CNF prereqs, categories, career tags,
workload. Authoritative over any scraped source; the loader never lets
snapshots overwrite these fields."""

from app.seed.overlays.core import CORE_COURSES
from app.seed.overlays.cs import CS_COURSES
from app.seed.overlays.econ import ECON_COURSES
from app.seed.overlays.ms import MS_COURSES

ALL_CURATED: list[dict] = [*CORE_COURSES, *CS_COURSES, *ECON_COURSES, *MS_COURSES]
CURATED: dict[str, dict] = {c["code"]: c for c in ALL_CURATED}
