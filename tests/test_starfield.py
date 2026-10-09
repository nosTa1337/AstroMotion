from pathlib import Path

import numpy as np
import pytest

from astromotion.animation import Animator
from astromotion.config import Motion, Starfield, load_config
from astromotion.separation import Layers
from astromotion.starfield import PerspectiveStars


def field(cfg=None):
    nebula = np.full((120, 120, 3), [.8, .1, .05], np.float32)
    stars = np.zeros_like(nebula)
    for y in range(15, 106, 15):
        for x in range(15, 106, 15):
            stars[y, x] = [.9, .85, .8]
    layers = Layers(nebula, stars, "screen", {})
    camera = Animator(layers, (120, 120), Motion(zoom=0, rotation_deg=0,
                      pan_x=0, pan_y=0, parallax=0))
    return PerspectiveStars(layers, camera, cfg or Starfield(enabled=True), 30)


def test_forward_and_lateral_motion_depend_on_individual_depth():
    p = field(Starfield(travel=.2, drift_x=.1, drift_y=0, rotation_deg=0))
    p.initial_z[:2] = [.5, 2]
    p.world_xy[:2] = [[.03, .04], [.03, .04]]
    before, _, _, _ = p.project(0)
    after, _, _, _ = p.project(1)
    # The same world position projects differently at different distances.
    # Approaching the near star causes much more vertical expansion.
    assert (after[0, 1] - before[0, 1]) > 10 * (after[1, 1] - before[1, 1])
    # Isolate translation: a lateral camera move causes larger foreground drift.
    p.cfg.travel = 0
    static, _, _, _ = p.project(1)
    p.cfg.travel = .2
    p.world_xy[:2] = 0
    moved, _, _, _ = p.project(1)
    displacement = np.abs(moved[:2, 0] - p.center[0])
    assert displacement[0] > 5 * displacement[1]
    assert np.isfinite(static).all()


def test_foreground_core_covers_red_nebula_and_is_depth_sorted():
    p = field(Starfield(travel=0, rotation_deg=0, shutter=0))
    p.initial_z[:] = 2
    p.world_xy[:] = 20  # move other stars outside the field of view
    p.world_xy[:2] = 0
    # Near white star must win even though the farther blue star is last in
    # source order; this tests ordering and foreground alpha-over together.
    p.initial_z[:2] = [.35, 1.5]
    p.colors[:2] = [[1, 1, 1], [0, 0, 1]]
    p.brightness[:2] = 1
    red_nebula = np.full((120, 120, 3), [.8, .1, .05], np.float32)
    unchanged = red_nebula.copy()
    output = p.composite(red_nebula, 0, 12)
    assert output[60, 60].min() > .97
    np.testing.assert_array_equal(red_nebula, unchanged)


def test_reproducible_depths_and_continuous_finite_recycling():
    a, b = field(), field()
    np.testing.assert_array_equal(a.initial_z, b.initial_z)
    np.testing.assert_array_equal(a.world_xy, b.world_xy)
    a.cfg.travel = 12
    for t in np.linspace(0, 1, 30):
        xy, z, _, _ = a.project(float(t))
        assert np.isfinite(xy).all() and np.isfinite(z).all()
        assert z.min() >= a.cfg.near and z.max() <= a.cfg.far
        output = a.composite(np.zeros((120, 120, 3), np.float32), float(t), 12)
        assert np.isfinite(output).all() and output.min() >= 0 and output.max() <= 1


def test_immersive_profile_keeps_nebula_stationary():
    cfg = load_config(Path(__file__).parents[1] / "configs" / "immersive.yaml")
    source = np.full((120, 120, 3), .1, np.float32)
    a = Animator(Layers(source, source, "screen", {}), (120, 120), cfg.motion)
    np.testing.assert_array_equal(a.matrix(0), a.matrix(1))
    assert cfg.starfield.enabled
    with pytest.raises(ValueError):
        load_config(overrides={"starfield": {"near": 4, "far": 3}})


def test_missing_reliable_star_cores_fails_explicitly():
    p = np.zeros((120, 120, 3), np.float32)
    layers = Layers(p, p, "screen", {})
    with pytest.raises(ValueError, match="Sternkerne"):
        PerspectiveStars(layers, Animator(layers, (120, 120), Motion()), Starfield(), 30)
