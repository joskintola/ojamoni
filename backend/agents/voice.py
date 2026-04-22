"""
Voice agent for OjaMoni — transcribes audio using Claude API only.
No OpenAI Whisper. No external LLM APIs. Claude handles everything.
"""

import anthropic
import base64
import os
import json
from dotenv import load_dotenv
from backend.agents.ingestion import extract_financial_data, format_response_for_trader

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def get_audio_media_type(file_path: str) -> str:
    """
    Detect audio format from file extension.
    Supported: mp3, wav, ogg, m4a, webm, mp4
    """
    ext = os.path.splitext(file_path)[1].lower()
    media_types = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
        ".mp4": "audio/mp4",
        ".webm": "audio/webm",
        ".aac": "audio/aac",
        ".flac": "audio/flac",
    }
    return media_types.get(ext, "audio/mpeg")


def encode_audio(audio_path: str) -> str:
    """Convert audio file to base64 string for Claude API."""
    with open(audio_path, "rb") as audio_file:
        return base64.standard_b64encode(audio_file.read()).decode("utf-8")


def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe audio using Claude API directly.
    Handles Nigerian English, Pidgin, Yoruba-accented speech, and mixed languages.
    """
    print(f"🎙️ Transcribing audio with Claude: {audio_path}")

    audio_data = encode_audio(audio_path)
    media_type = get_audio_media_type(audio_path)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "You are transcribing a voice note from a Nigerian market trader. "
                            "The speaker may use Nigerian English, Pidgin English, or a mix of both. "
                            "Transcribe exactly what was said as accurately as possible. "
                            "Preserve Pidgin words and phrases as spoken (e.g., 'e don do', 'I sell am', 'dem buy'). "
                            "Return ONLY the transcription text, nothing else."
                        ),
                    },
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": audio_data,
                        },
                    },
                ],
            }
        ],
    )

    transcript = response.content[0].text.strip()
    print(f"📝 Transcribed: {transcript}")
    return transcript


def process_voice_note(audio_path: str, trader_name: str):
    """
    Full pipeline: audio file → Claude transcription → financial extraction → formatted reply.
    Returns (data, reply) tuple.
    data is None if no financial info was found.
    """

    # Step 1: Transcribe with Claude
    transcript = transcribe_audio(audio_path)

    if not transcript:
        return None, (
            "Sorry, I couldn't understand that voice note. "
            "Please try again or type your sales. 🙏"
        )

    # Step 2: Add context so Claude knows this came from speech
    enriched_input = (
        f"This is a transcription of a voice note from a Nigerian trader. "
        f"The speech may be informal, in Pidgin English, or imprecise. "
        f"Extract whatever financial information you can find.\n\n"
        f'Transcription: "{transcript}"'
    )

    # Step 3: Extract financial data
    data = extract_financial_data(text_input=enriched_input)

    # Step 4: Format the reply
    reply = format_response_for_trader(data, trader_name)

    # Prepend transcript so trader knows OjaMoni understood them
    full_reply = (
        f"🎙️ *I heard you say:*\n"
        f"_{transcript}_\n\n"
        f"{reply}"
    )

    return data, full_reply


def process_voice_note_with_image(audio_path: str, image_path: str, trader_name: str):
    """
    Handles when a trader sends BOTH a voice note AND a photo of their records.
    Claude uses both inputs together for the most complete financial picture.
    """

    # Transcribe voice note
    transcript = transcribe_audio(audio_path)

    # Combine voice context with image
    enriched_input = (
        f"The trader sent a photo of their sales record AND explained it in a voice note.\n\n"
        f'Voice note transcription: "{transcript}"\n\n'
        f"Use both the image and the voice note to extract the most complete "
        f"financial picture possible."
    )

    # Pass both to ingestion agent
    data = extract_financial_data(
        text_input=enriched_input,
        image_path=image_path,
    )

    reply = format_response_for_trader(data, trader_name)

    full_reply = (
        f"📸🎙️ *Got your photo and voice note!*\n"
        f'_You said: "{transcript}"_\n\n'
        f"{reply}"
    )

    return data, full_reply