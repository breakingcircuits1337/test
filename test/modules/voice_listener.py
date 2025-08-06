import threading
import queue
import logging
import time

try:
    import sounddevice as sd
    import numpy as np
    import pvporcupine
    PORCUPINE_AVAILABLE = True
except ImportError:
    PORCUPINE_AVAILABLE = False

try:
    from RealtimeSTT import AudioToTextRecorder
except ImportError:
    AudioToTextRecorder = None

class VoiceListener:
    def __init__(self, wake_word="ada", callback=None, silence_sec=1.2, vad_amplitude=0.03):
        self.wake_word = wake_word
        self.callback = callback
        self.silence_sec = silence_sec
        self.vad_amplitude = vad_amplitude
        self.interrupt_flag = threading.Event()
        self._thread = None
        self._running = threading.Event()
        self.logger = logging.getLogger("VoiceListener")
        self._porcupine = None
        self._stream = None

    def start(self):
        if not PORCUPINE_AVAILABLE or AudioToTextRecorder is None:
            self.logger.warning("pvporcupine or dependencies not available. Falling back to naive wake-word mode.")
            return self._fallback_loop()
        self._running.set()
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running.clear()
        self.interrupt_flag.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        if self._stream:
            try:
                self._stream.close()
            except Exception:
                pass
        if self._porcupine:
            self._porcupine.delete()

    def _listen_loop(self):
        """ Main loop: wake-word detection -> record -> callback -> repeat """
        try:
            self._porcupine = pvporcupine.create(keywords=[self.wake_word])
            sample_rate = self._porcupine.sample_rate
            frame_length = self._porcupine.frame_length
            self.logger.info(f"Porcupine initialized (wake word: {self.wake_word}). Listening...")

            with sd.InputStream(channels=1, samplerate=sample_rate, blocksize=frame_length, dtype="int16") as stream:
                self._stream = stream
                while self._running.is_set():
                    pcm = stream.read(frame_length)[0].flatten()
                    result = self._porcupine.process(pcm)
                    if result >= 0:
                        self.logger.info("Wake word detected, starting speech recognition.")
                        self._handle_speech(stream, sample_rate)
                        self.logger.info("Returned to wake-word listening.")

        except Exception as e:
            self.logger.warning(f"Porcupine error: {e}. Falling back to naive mode.")
            self._fallback_loop()

    def _handle_speech(self, stream, sample_rate):
        """Record speech until VAD detects silence, then call callback."""
        frames = []
        last_voice = time.time()
        silence_limit = self.silence_sec
        vad_thresh = self.vad_amplitude
        self.interrupt_flag.clear()

        def _audio_callback(indata, frames_count, time_info, status):
            nonlocal last_voice
            audio = np.abs(indata)
            if np.max(audio) > vad_thresh:
                last_voice = time.time()
            frames.append(indata.copy())
        # Use sounddevice for VAD, then pass to RealtimeSTT for transcription
        with sd.InputStream(channels=1, samplerate=sample_rate, callback=_audio_callback):
            while time.time() - last_voice < silence_limit:
                if not self._running.is_set():
                    return
                time.sleep(0.1)
        # Convert frames to bytes for AudioToTextRecorder (optional, as fallback)
        if AudioToTextRecorder is not None:
            rec = AudioToTextRecorder(spinner=False, model="tiny.en", language="en", print_transcription_time=False)
            rec.start()
            # Let RealtimeSTT record until silence
            transcript = rec.text(lambda text: text, stop_on_silence=True, silence_time=silence_limit)
            rec.stop()
        else:
            self.logger.warning("RealtimeSTT not installed; skipping transcription.")
            transcript = ""
        if self.callback and transcript:
            self.callback(transcript)

    def _fallback_loop(self):
        """Fallback: naive loop with manual wake-word and text input."""
        self.logger.warning("Fallback: naive mode. Type 'ada: <command>' to simulate voice input.")
        while True:
            try:
                raw = input("You (simulate voice): ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nExiting fallback voice loop.")
                break
            if self.wake_word in raw.lower():
                cmd = raw.lower().split(self.wake_word, 1)[-1].strip(":, ")
                if self.callback:
                    self.callback(cmd)