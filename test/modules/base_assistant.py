from typing import List, Dict
import logging
import os
from modules.deepseek import conversational_prompt as deepseek_conversational_prompt
from modules.ollama import conversational_prompt as ollama_conversational_prompt

# New LLM provider imports, guarded
try:
    from modules.gemini import conversational_prompt as gemini_conversational_prompt
except ImportError:
    gemini_conversational_prompt = None
try:
    from modules.mistral import conversational_prompt as mistral_conversational_prompt
except ImportError:
    mistral_conversational_prompt = None
try:
    from modules.groq import conversational_prompt as groq_conversational_prompt
except ImportError:
    groq_conversational_prompt = None
from modules.utils import build_file_name_session
from RealtimeTTS import TextToAudioStream, SystemEngine
from elevenlabs import play
from elevenlabs.client import ElevenLabs
import pyttsx3
import time
from modules.assistant_config import get_config


class PlainAssistant:
    def __init__(self, logger: logging.Logger, session_id: str, interrupt_flag=None):
        self.logger = logger
        self.session_id = session_id
        self.conversation_history = []

        # Get voice configuration
        self.voice_type = get_config("base_assistant.voice")
        self.elevenlabs_voice = get_config("base_assistant.elevenlabs_voice")
        self.brain = get_config("base_assistant.brain")
        self.interrupt_flag = interrupt_flag  # For TTS interruption

        # Initialize appropriate TTS engine
        self.engine = None
        if self.voice_type == "elevenlabs":
            try:
                self.logger.info("🔊 Initializing ElevenLabs TTS engine")
                api_key = os.getenv("ELEVEN_API_KEY")
                if not api_key:
                    raise ValueError("ELEVEN_API_KEY is not set.")
                self.elevenlabs_client = ElevenLabs(api_key=api_key)
            except Exception as e:
                self.logger.warning(f"⚠️ ElevenLabs unavailable ({e}); falling back to local TTS.")
                self.voice_type = "local"
                self._ensure_local_tts_initialized()
        elif self.voice_type == "local":
            self._ensure_local_tts_initialized()
        elif self.voice_type == "realtime-tts":
            self.logger.info("🔊 Initializing RealtimeTTS engine")
            self.engine = SystemEngine()
            self.stream = TextToAudioStream(
                self.engine, frames_per_buffer=256, playout_chunk_size=1024
            )
        else:
            raise ValueError(f"Unsupported voice type: {self.voice_type}")

        self._tts_thread = None  # For TTS interruption

    def _ensure_local_tts_initialized(self):
        if not hasattr(self, "engine") or self.engine is None:
            import pyttsx3
            self.logger.info("🔊 Initializing local TTS engine (fallback)")
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", 150)
            self.engine.setProperty("volume", 1.0)

    def process_text(self, text: str) -> str:
        """Process text input and generate response"""
        try:
            # Check if text matches our last response
            if (
                self.conversation_history
                and text.strip().lower()
                in self.conversation_history[-1]["content"].lower()
            ):
                self.logger.info("🤖 Ignoring own speech input")
                return ""

            # Add user message to conversation history
            self.conversation_history.append({"role": "user", "content": text})

            # Generate response using configured brain
            self.logger.info(f"🤖 Processing text with {self.brain}...")
            # Routing based on self.brain
            if self.brain.startswith("ollama:"):
                model_no_prefix = ":".join(self.brain.split(":")[1:])
                response = ollama_conversational_prompt(
                    self.conversation_history, model=model_no_prefix
                )
            elif self.brain.startswith("gemini"):
                if gemini_conversational_prompt is None:
                    raise ImportError("Gemini provider not available (missing dependency).")
                response = gemini_conversational_prompt(self.conversation_history)
            elif self.brain.startswith("mistral"):
                if mistral_conversational_prompt is None:
                    raise ImportError("Mistral provider not available (missing dependency).")
                response = mistral_conversational_prompt(self.conversation_history)
            elif self.brain.startswith("groq"):
                if groq_conversational_prompt is None:
                    raise ImportError("Groq provider not available (missing dependency).")
                response = groq_conversational_prompt(self.conversation_history)
            else:
                response = deepseek_conversational_prompt(self.conversation_history)

            # Add assistant response to history
            self.conversation_history.append({"role": "assistant", "content": response})

            # Speak the response
            self.speak(response)

            return response

        except Exception as e:
            self.logger.error(f"❌ Error occurred: {str(e)}")
            raise

    def speak(self, text: str):
        """Convert text to speech using configured engine, with interruption support."""
        self.logger.info(f"🔊 Speaking: {text}")
        if self.voice_type == "local":
            self._ensure_local_tts_initialized()
            def tts_func():
                try:
                    self.engine.say(text)
                    self.engine.runAndWait()
                except Exception as e:
                    self.logger.error(f"❌ Local TTS error: {e}")
            self._tts_thread = threading.Thread(target=tts_func)
            self._tts_thread.start()
            # Interruption monitoring
            while self._tts_thread.is_alive():
                if self.interrupt_flag and self.interrupt_flag.is_set():
                    self.logger.info("🔊 TTS interrupted by user speech.")
                    try:
                        self.engine.stop()
                    except Exception:
                        pass
                    break
                time.sleep(0.2)
            self._tts_thread.join(timeout=0.1)
        elif self.voice_type == "realtime-tts":
            def tts_func():
                try:
                    self.stream.feed(text)
                    self.stream.play()
                except Exception as e:
                    self.logger.error(f"❌ RealtimeTTS error: {e}")
            self._tts_thread = threading.Thread(target=tts_func)
            self._tts_thread.start()
            while self._tts_thread.is_alive():
                if self.interrupt_flag and self.interrupt_flag.is_set():
                    self.logger.info("🔊 RealtimeTTS interrupted by user speech.")
                    try:
                        self.stream.stop()
                    except Exception:
                        pass
                    break
                time.sleep(0.2)
            self._tts_thread.join(timeout=0.1)
        elif self.voice_type == "elevenlabs":
            def tts_func():
                try:
                    # Stream in chunks for interruption
                    audio_stream = self.elevenlabs_client.generate(
                        text=text,
                        voice=self.elevenlabs_voice,
                        model="eleven_turbo_v2",
                        stream=True,
                    )
                    for chunk in audio_stream:
                        if self.interrupt_flag and self.interrupt_flag.is_set():
                            self.logger.info("🔊 ElevenLabs TTS interrupted by user speech.")
                            break
                        play(chunk)
                except Exception as e:
                    self.logger.warning(f"⚠️ ElevenLabs TTS failed ({e}); falling back to local TTS.")
                    self.voice_type = "local"
                    self._ensure_local_tts_initialized()
                    try:
                        self.engine.say(text)
                        self.engine.runAndWait()
                    except Exception as e2:
                        self.logger.error(f"❌ Local TTS error (fallback): {e2}")
            self._tts_thread = threading.Thread(target=tts_func)
            self._tts_thread.start()
            while self._tts_thread.is_alive():
                if self.interrupt_flag and self.interrupt_flag.is_set():
                    break
                time.sleep(0.2)
            self._tts_thread.join(timeout=0.1)
        self.logger.info(f"🔊 Spoken: {text}")
