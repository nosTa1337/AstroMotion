import wave

import numpy as np
import pytest

from astromotion.config import Audio, Starfield, load_config
from astromotion.music import synthesize_ambient
def test_ambient_accents_are_reproducible_audible_and_fade_cleanly(tmp_path):
    pcm = []
    for i, accents in enumerate((0., .45, .45)):
        path = tmp_path / f"{i}.wav"
        synthesize_ambient(path, 6, Audio(seed=73, accents=accents, harmony="floating"))
        with wave.open(str(path)) as wav:
            assert wav.getnframes() == 288000
            data = np.frombuffer(wav.readframes(wav.getnframes()), "<i2")
        assert not data[:2].any() and not data[-2:].any()
        assert np.abs(data).max() < 32767
        pcm.append(data)
    np.testing.assert_array_equal(pcm[1], pcm[2])
    assert np.sqrt(np.mean((pcm[0].astype(float) - pcm[1])**2)) > 30
    with pytest.raises(ValueError):
        load_config(overrides={"audio": {"accents": 1.1}})
