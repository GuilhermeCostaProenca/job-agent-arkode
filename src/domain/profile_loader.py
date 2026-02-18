from pathlib import Path

import yaml

from src.domain.models import CandidateProfile


def load_profile(path: Path) -> CandidateProfile:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return CandidateProfile.model_validate(data)
