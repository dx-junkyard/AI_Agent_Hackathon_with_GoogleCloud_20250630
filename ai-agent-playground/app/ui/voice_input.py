import logging
import os
import tempfile

import streamlit as st
from audiorecorder import audiorecorder
from dotenv import load_dotenv
from openai import OpenAI
from pydub import AudioSegment

logger = logging.getLogger(__name__)

# Load environment variables from .env if available
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


class VoiceInput:
    """Handle voice recording and speech recognition using Whisper API."""

    @staticmethod
    def record_audio() -> AudioSegment:
        """Render the audio recorder widget and return the recorded segment."""
        try:
            audio = audiorecorder(
                "🎤",
                "録音中",
                start_style={
                    "background-color": "#eee",
                    "border": "1px solid #ccc",
                    "border-radius": "50%",
                },
                stop_style={"background-color": "#fdd"},
                key="voice_recorder",
            )
        except FileNotFoundError:
            st.error("ffmpeg が見つかりません。Docker イメージを再ビルドしてください")
            return AudioSegment.empty()
        except Exception as e:
            st.error(f"録音エラー: {e}")
            return AudioSegment.empty()
        return audio

    @staticmethod
    def transcribe(audio: AudioSegment) -> str:
        """Transcribe a recorded AudioSegment using OpenAI Whisper."""
        if len(audio) == 0:
            return ""
        audio = audio.set_channels(1).set_frame_rate(16000)
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            audio.export(tmp.name, format="wav")
            tmp.seek(0)
            with st.spinner("音声認識中..."):
                try:
                    with open(tmp.name, "rb") as f:
                        result = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=f,
                            language="ja",
                        )
                    text = result.text
                except Exception as e:
                    st.error(f"音声認識失敗: {e}")
                    logger.error("Whisper API error: %s", e)
                    return ""
        logger.info(f"Recognized voice text: {text}")
        return text.strip()

    def recognize_voice(self) -> str:
        """Record audio via widget then transcribe it."""
        audio = self.record_audio()
        return self.transcribe(audio)
