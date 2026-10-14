"""Cache/provenance contracts with stubbed CLI outputs; no model or video renders."""
from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pytest

from astromotion.config import Config, Separation
from astromotion.imaging import load_image, save_png, save_tiff
import astromotion.cli as cli
import astromotion.pipeline as pipeline
from astromotion.starnet_cache import (
    MANIFEST, STARLESS, cache_identity, file_checksum, load_cached_starless, save_cache_manifest,
)


@pytest.fixture
def cached_scene(tmp_path):
    executable = tmp_path / 'StarNet2' / 'bin' / 'starnet2.exe'
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b'test CLI identity, never executed')
    model = executable.parent / 'model.onnx'
    model.write_bytes(b'test model identity')
    input_path = tmp_path / 'original.png'
    image = np.full((48, 64, 3), .2, np.float32)
    save_png(input_path, image)
    image = load_image(input_path)
    cfg = Separation(executable=str(executable))
    workspace = tmp_path / 'preview_assets'
    workspace.mkdir()
    save_tiff(workspace / STARLESS, image * .9)
    identity = cache_identity(input_path, image, cfg, 3200)
    save_cache_manifest(workspace, identity)
    return input_path, image, cfg, workspace, identity, model


def test_matching_cache_returns_unmodified_working_pixels(cached_scene):
    _, _, _, workspace, identity, _ = cached_scene
    cached = load_cached_starless(workspace, identity)
    np.testing.assert_array_equal(cached, load_image(workspace / STARLESS))
    assert not list(workspace.glob('*.tmp'))


@pytest.mark.parametrize('change', ['source_file', 'work_pixels', 'work_limit', 'stride', 'mode', 'arguments', 'executable', 'model'])
def test_changed_inference_inputs_invalidate_cache(cached_scene, change):
    input_path, image, cfg, workspace, identity, model = cached_scene
    work_limit = 3200
    if change == 'source_file':
        save_png(input_path, image * .8)
    elif change == 'work_pixels':
        image = image * .8
    elif change == 'work_limit':
        work_limit = 1600
    elif change == 'stride':
        cfg = replace(cfg, stride=128)
    elif change == 'mode':
        cfg = replace(cfg, mode='legacy')
    elif change == 'arguments':
        cfg = replace(cfg, extra_args=['--different-inference-option'])
    elif change == 'executable':
        Path(cfg.executable).write_bytes(b'changed CLI')
    elif change == 'model':
        model.write_bytes(b'changed model')
    changed = cache_identity(input_path, image, cfg, work_limit)
    assert changed != identity and load_cached_starless(workspace, changed) is None


@pytest.mark.parametrize('equals_form', [False, True])
def test_model_file_argument_outside_cli_folder_is_fingerprinted(cached_scene, tmp_path, equals_form):
    input_path, image, cfg, workspace, _, _ = cached_scene
    external = tmp_path / 'external-model.data'
    external.write_bytes(b'original external model')
    cfg = replace(cfg, extra_args=[f'--model={external}'] if equals_form else ['--model', str(external)])
    identity = cache_identity(input_path, image, cfg, 3200)
    save_cache_manifest(workspace, identity)
    external.write_bytes(b'updated external model')
    assert load_cached_starless(workspace, cache_identity(input_path, image, cfg, 3200)) is None


@pytest.mark.parametrize('damage', ['missing_manifest', 'invalid_json', 'wrong_source', 'unknown_version', 'modified_tiff', 'missing_tiff', 'wrong_shape', 'unreadable_tiff'])
def test_missing_or_damaged_cache_is_a_miss(cached_scene, damage):
    _, _, _, workspace, identity, _ = cached_scene
    path = workspace / MANIFEST
    if damage == 'missing_manifest':
        path.unlink()
    elif damage == 'invalid_json':
        path.write_text('{broken')
    elif damage in ('wrong_source', 'unknown_version'):
        manifest = json.loads(path.read_text())
        manifest['source' if damage == 'wrong_source' else 'version'] = 'unverified'
        path.write_text(json.dumps(manifest))
    elif damage == 'modified_tiff':
        save_tiff(workspace / STARLESS, np.full((48, 64, 3), .1, np.float32))
    elif damage == 'missing_tiff':
        (workspace / STARLESS).unlink()
    else:
        if damage == 'wrong_shape':
            save_tiff(workspace / STARLESS, np.full((16, 16, 3), .1, np.float32))
        else:
            (workspace / STARLESS).write_bytes(b'not a readable TIFF')
        # Exercise decoded-shape/readability checks after a matching checksum.
        manifest = json.loads(path.read_text())
        manifest['starless_sha256'] = file_checksum(workspace / STARLESS)
        path.write_text(json.dumps(manifest))
    assert load_cached_starless(workspace, identity) is None


class BeforeAnimation(Exception):
    pass


@pytest.fixture
def separation_only_pipeline(tmp_path, monkeypatch):
    # A source larger than work_long_edge catches the old --starless size mismatch.
    source = tmp_path / 'large original.png'
    save_png(source, np.full((1024, 1536, 3), .2, np.float32))
    executable = tmp_path / 'bin' / 'starnet2.exe'
    executable.parent.mkdir()
    executable.write_bytes(b'CLI fixture')
    cfg = Config(work_long_edge=768, save_layers=False,
                 separation=Separation(executable=str(executable)))
    calls, layers_seen = [], []

    def stub_cli(image, separation, workspace):
        calls.append(image.shape)
        save_tiff(workspace / STARLESS, image * .9)
        return load_image(workspace / STARLESS)

    def stop_before_animation(layers, *args):
        layers_seen.append(layers.nebula.copy())
        raise BeforeAnimation

    monkeypatch.setattr(pipeline, 'resolve_binary', lambda value: value)
    monkeypatch.setattr(pipeline, 'run_starnet', stub_cli)
    monkeypatch.setattr(pipeline, 'Animator', stop_before_animation)
    return source, cfg, calls, layers_seen


def test_preview_to_full_and_same_output_rerender_skip_cli_at_working_size(separation_only_pipeline, tmp_path):
    source, cfg, calls, layers_seen = separation_only_pipeline
    preview = tmp_path / 'photo_preview.mp4'
    cache = tmp_path / 'photo_preview_assets'
    with pytest.raises(BeforeAnimation):
        pipeline.render(source, preview, replace(cfg, resolution='360p'))
    with pytest.raises(BeforeAnimation):
        pipeline.render(source, tmp_path / 'photo.mp4', cfg, starnet_cache=cache)
    with pytest.raises(BeforeAnimation):
        pipeline.render(source, preview, replace(cfg, resolution='360p'))
    assert calls == [(512, 768, 3)]
    np.testing.assert_array_equal(layers_seen[0], layers_seen[1])
    np.testing.assert_array_equal(layers_seen[0], layers_seen[2])
    assert not list(tmp_path.glob('*.mp4'))


def test_invalid_preview_cache_calls_starnet_again(separation_only_pipeline, tmp_path):
    source, cfg, calls, _ = separation_only_pipeline
    cache = tmp_path / 'photo_preview_assets'
    with pytest.raises(BeforeAnimation):
        pipeline.render(source, tmp_path / 'photo_preview.mp4', replace(cfg, resolution='360p'))
    (cache / STARLESS).write_bytes(b'partial/corrupted output')
    with pytest.raises(BeforeAnimation):
        pipeline.render(source, tmp_path / 'photo.mp4', cfg, starnet_cache=cache)
    assert len(calls) == 2
    assert (tmp_path / 'photo_assets' / MANIFEST).is_file()


@pytest.mark.parametrize('failure', ['cli', 'layer_qa'])
def test_failed_cli_or_layer_qa_cannot_publish_or_inherit_a_manifest(separation_only_pipeline, tmp_path, monkeypatch, failure):
    source, cfg, calls, _ = separation_only_pipeline
    output = tmp_path / 'photo.mp4'
    workspace = tmp_path / 'photo_assets'
    with pytest.raises(BeforeAnimation):
        pipeline.render(source, output, cfg)
    assert (workspace / MANIFEST).is_file()

    def failed_cli(image, separation, workspace):
        if failure == 'cli':
            (workspace / STARLESS).write_bytes(b'partial output')
            raise RuntimeError('CLI failed')
        save_tiff(workspace / STARLESS, image)
        return image

    monkeypatch.setattr(pipeline, 'run_starnet', failed_cli)
    changed = replace(cfg, separation=replace(cfg.separation, stride=128))
    with pytest.raises(RuntimeError if failure == 'cli' else ValueError):
        pipeline.render(source, output, changed)
    assert not (workspace / MANIFEST).exists()
    assert not output.exists()


def test_cli_passes_cache_as_processed_separation_without_using_starless(monkeypatch, tmp_path):
    recorded = []

    def record(image, output, cfg, starless, *args, **kwargs):
        recorded.append((starless, kwargs))

    monkeypatch.setattr(cli, 'render', record)
    cache = tmp_path / 'preview_assets'
    assert cli.main(['--input', str(tmp_path / 'photo.jpg'), '--starnet-cache', str(cache)]) == 0
    assert recorded == [(None, {'starnet_cache': cache})]


def test_external_starless_and_working_cache_are_mutually_exclusive():
    with pytest.raises(SystemExit) as exc:
        cli.main(['--starless', 'original-size.tif', '--starnet-cache', 'preview_assets'])
    assert exc.value.code == 2
