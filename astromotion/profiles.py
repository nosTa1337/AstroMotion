"""Small, reproducible variations of the three clean star-flight profiles."""
from dataclasses import replace
import secrets

import numpy as np

from .config import Config


def resolve_profile_variation(cfg: Config) -> Config:
    """Resolve once per render; keep reusable wizard/config values untouched."""
    if cfg.profile == "custom" or not cfg.profile_variation:
        return cfg
    seed = cfg.profile_seed if cfg.profile_seed is not None else secrets.randbits(32)
    rng = np.random.default_rng(seed)
    direction = int(rng.choice([-1, 1]))
    motion = replace(cfg.motion,
        zoom=min(.5, cfg.motion.zoom * rng.uniform(.94, 1.06)),
        rotation_deg=float(np.clip(cfg.motion.rotation_deg * direction * rng.uniform(.9, 1.1), -10, 10)))
    stars = replace(cfg.starfield,
        count=int(np.clip(round(cfg.starfield.count * rng.uniform(.9, 1.1)), 1, 20000)),
        drift_x=float(np.clip(cfg.starfield.drift_x * direction * rng.uniform(.9, 1.1), -.5, .5)),
        drift_y=float(np.clip(cfg.starfield.drift_y * int(rng.choice([-1, 1])) * rng.uniform(.9, 1.1), -.5, .5)),
        rotation_deg=float(np.clip(cfg.starfield.rotation_deg * direction * rng.uniform(.9, 1.1), -15, 15)))
    result = replace(cfg, profile_seed=seed, motion=motion, starfield=stars)
    result.validate()
    return result
