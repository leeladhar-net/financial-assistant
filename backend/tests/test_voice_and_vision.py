import pytest
from app.integrations.voice_provider import VoiceProvider
from app.integrations.vision_provider import VisionProvider

@pytest.mark.asyncio
async def test_voice_transcription():
    voice_bytes = b"fake_audio_bytes"
    res = await VoiceProvider.transcribe_voice(voice_bytes)
    assert res.transcription_text is not None
    assert "Nvidia" in res.transcription_text
    assert res.detected_intent is not None

@pytest.mark.asyncio
async def test_vision_image_analysis():
    image_bytes = b"fake_chart_bytes"
    res = await VisionProvider.analyze_image(image_bytes)
    assert res.detected_type == "chart"
    assert len(res.key_insights) > 0
    assert "Financial Chart Analysis" in res.commentary
