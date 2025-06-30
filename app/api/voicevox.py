import os
import requests
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


def synthesize(text: str, base_url: str = None, speaker: Optional[int] = None, speed: Optional[float] = None) -> bytes:
    """Synthesize speech using VOICEVOX and return WAV audio bytes."""
    base_url = base_url or os.environ.get("VOICEVOX_URL", "http://voicevox:50021")
    if speaker is None:
        env_speaker = os.environ.get("VOICEVOX_SPEAKER")
        speaker = int(env_speaker) if env_speaker is not None else 1
    if speed is None:
        env_speed = os.environ.get("VOICEVOX_SPEED")
        speed = float(env_speed) if env_speed is not None else 1.0

    query = requests.post(
        f"{base_url}/audio_query",
        params={"speaker": speaker, "text": text},
    )
    query.raise_for_status()
    query_data = query.json()
    query_data["speedScale"] = speed

    synthesis = requests.post(
        f"{base_url}/synthesis",
        params={"speaker": speaker},
        json=query_data,
    )
    synthesis.raise_for_status()
    return synthesis.content
