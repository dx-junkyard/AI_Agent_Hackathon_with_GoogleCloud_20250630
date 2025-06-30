import os
import requests
import streamlit as st
from dotenv import load_dotenv
from typing import Optional


load_dotenv()


class AudioOutput:
    """Generate speech using VOICEVOX engine and play it."""

    def __init__(self, base_url: str = None, speaker: Optional[int] = None, speed: Optional[float] = None) -> None:
        self.base_url = base_url or os.environ.get("VOICEVOX_URL", "http://voicevox:50021")
        env_speaker = os.environ.get("VOICEVOX_SPEAKER")
        self.speaker = speaker if speaker is not None else int(env_speaker) if env_speaker is not None else 1
        env_speed = os.environ.get("VOICEVOX_SPEED")
        self.speed = speed if speed is not None else float(env_speed) if env_speed is not None else 1.0

    def _synthesize(self, text: str) -> bytes:
        """Request VOICEVOX to synthesize speech and return WAV bytes."""
        query = requests.post(
            f"{self.base_url}/audio_query",
            params={"speaker": self.speaker, "text": text},
        )
        query.raise_for_status()
        query_data = query.json()
        query_data["speedScale"] = self.speed
        synthesis = requests.post(
            f"{self.base_url}/synthesis",
            params={"speaker": self.speaker},
            json=query_data,
        )
        synthesis.raise_for_status()
        return synthesis.content

    def speak(self, text: str) -> None:
        if not text:
            return
        try:
            audio = self._synthesize(text)
            st.audio(audio, format="audio/wav", autoplay=True)
        except Exception as e:
            st.error(f"音声生成失敗: {e}")
