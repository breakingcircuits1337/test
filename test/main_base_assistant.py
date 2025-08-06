from RealtimeSTT import AudioToTextRecorder
from typing import List
from modules.assistant_config import get_config
from modules.base_assistant import PlainAssistant
from modules.utils import create_session_logger_id, setup_logging
import typer
import logging

app = typer.Typer()


@app.command()
def ping():
    print("pong")


@app.command()
def chat():
    """Start a chat session with the plain assistant using voice input and wake-word."""
    from modules.voice_listener import VoiceListener
    # Create session and logging
    session_id = create_session_logger_id()
    logger = setup_logging(session_id)
    logger.info(f"🚀 Starting chat session {session_id}")

    # Create assistant, pass interrupt_flag
    listener = None
    try:
        # We'll pass the listener's interrupt_flag so TTS can be interrupted by voice
        def voice_callback(text):
            # You can add exit/quit check here if desired
            if text.strip().lower() in ["exit", "quit"]:
                logger.info("👋 Exiting chat session")
                if listener:
                    listener.stop()
                return False
            response = assistant.process_text(text)
            logger.info(f"🤖 Response: {response}")
            return True

        listener = VoiceListener(callback=None)  # assign callback after assistant instantiation
        assistant = PlainAssistant(logger, session_id, interrupt_flag=listener.interrupt_flag)
        listener.callback = voice_callback

        print("🎤 Say 'Ada' to begin speaking. (Ctrl+C to quit)")
        listener.start()
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("👋 Session ended by user")
    except Exception as e:
        logger.error(f"❌ Error occurred: {str(e)}")
        raise
    finally:
        if listener:
            listener.stop()


if __name__ == "__main__":
    app()
