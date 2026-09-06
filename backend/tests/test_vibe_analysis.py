from pathlib import Path

from app.vibe_analysis import AudioAnalysisError, VibeFeatures, analyze_audio

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "tiny_clip.wav"


def test_analyze_audio_returns_features_from_real_clip():
    clip_bytes = FIXTURE_PATH.read_bytes()

    features = analyze_audio(clip_bytes)

    assert isinstance(features, VibeFeatures)
    assert features.source == "librosa_fallback"
    assert 0.0 <= features.vibe_score <= 1.0
    assert 0.0 <= features.energy <= 1.0
    assert 0.0 <= features.brightness <= 1.0
    assert features.tempo_bpm >= 0.0


def test_analyze_audio_rejects_garbage_bytes():
    try:
        analyze_audio(b"not audio data")
        assert False, "expected AudioAnalysisError"
    except AudioAnalysisError:
        pass
