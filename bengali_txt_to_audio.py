import os
import re
import sys
import base64
import argparse
from io import BytesIO
from pathlib import Path

from sarvamai import SarvamAI
from pydub import AudioSegment


def read_text_file(txt_path):
    """Read a UTF-8 text file, supporting Bengali text."""
    path = Path(txt_path)

    if not path.exists():
        raise FileNotFoundError(f"Text file not found: {path}")

    if path.suffix.lower() != ".txt":
        raise ValueError("Input file must have a .txt extension.")

    # utf-8-sig also handles files saved with a UTF-8 BOM
    text = path.read_text(encoding="utf-8-sig")
    text = text.strip()

    if not text:
        raise ValueError("The text file is empty.")

    return text


def split_text(text, max_chars=2000):
    """Split text into manageable chunks without losing content."""
    chunks = []
    paragraphs = re.split(r"\n\s*\n", text)

    current = ""

    for paragraph in paragraphs:
        paragraph = paragraph.strip()

        if not paragraph:
            continue

        # Split oversized paragraphs into sentences
        sentences = re.split(r"(?<=[।!?])\s+", paragraph)

        for sentence in sentences:
            sentence = sentence.strip()

            if not sentence:
                continue

            # Break very long sentences at whitespace
            while len(sentence) > max_chars:
                split_at = sentence.rfind(" ", 0, max_chars + 1)

                if split_at <= 0:
                    split_at = max_chars

                piece = sentence[:split_at].strip()

                if piece:
                    if current:
                        chunks.append(current)
                        current = ""
                    chunks.append(piece)

                sentence = sentence[split_at:].strip()

            if not sentence:
                continue

            candidate = f"{current} {sentence}".strip()

            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = sentence

    if current:
        chunks.append(current)

    return chunks


def convert_txt_to_audio(
    txt_path,
    output_path,
    speaker="roopa_bn_conversational",
    language_code="bn-IN",
    model="bulbul:v4-flash",
):
    """Convert a Bengali TXT file to a WAV audio file."""

    api_key = os.getenv("SARVAM_API_KEY")

    if not api_key:
        raise RuntimeError(
            "SARVAM_API_KEY is not set. "
            "Set your Sarvam API key as an environment variable."
        )

    text = read_text_file(txt_path)
    chunks = split_text(text)

    print(f"Text file: {txt_path}")
    print(f"Total characters: {len(text)}")
    print(f"Total audio chunks: {len(chunks)}")

    client = SarvamAI(api_subscription_key=api_key)

    combined_audio = AudioSegment.empty()

    for index, chunk in enumerate(chunks, start=1):
        print(f"Converting chunk {index}/{len(chunks)}...")

        try:
            response = client.text_to_speech.convert(
                text=chunk,
                model=model,
                language_code=language_code,
                speaker=speaker,
            )

            # Decode the audio returned by the API
            audio_base64 = response.audios[0]
            audio_bytes = base64.b64decode(audio_base64)

            chunk_audio = AudioSegment.from_file(
                BytesIO(audio_bytes),
                format="wav",
            )

            # Add a short pause between chunks
            if index > 1:
                combined_audio += AudioSegment.silent(duration=300)

            combined_audio += chunk_audio

        except Exception as exc:
            message = str(exc)

            if "402" in message or "insufficient_quota" in message:
                raise RuntimeError(
                    "Sarvam AI credits are insufficient. "
                    "Check your account balance before retrying."
                ) from exc

            raise RuntimeError(
                f"Failed to convert chunk {index}: {message}"
            ) from exc

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    combined_audio.export(output_file, format="wav")

    print("\nConversion completed successfully.")
    print(f"Audio saved to: {output_file.resolve()}")
    print(f"Audio duration: {len(combined_audio) / 1000:.1f} seconds")


def main():
    parser = argparse.ArgumentParser(
        description="Convert a Bengali TXT file into audio using Sarvam AI."
    )

    parser.add_argument(
        "input",
        help="Path to the input TXT file",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="bengali_audio.wav",
        help="Output WAV filename (default: bengali_audio.wav)",
    )

    parser.add_argument(
        "--speaker",
        default="roopa_bn_conversational",
        help="Sarvam TTS speaker",
    )

    parser.add_argument(
        "--language",
        default="bn-IN",
        help="Language code (default: bn-IN)",
    )

    args = parser.parse_args()

    try:
        convert_txt_to_audio(
            txt_path=args.input,
            output_path=args.output,
            speaker=args.speaker,
            language_code=args.language,
        )
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
