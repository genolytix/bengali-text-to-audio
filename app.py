import base64
import io
import os
import re

from flask import Flask, render_template, request, send_file, jsonify
from sarvamai import SarvamAI
from pydub import AudioSegment

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload limit

MAX_CHARS_PER_CHUNK = 2000
DEFAULT_MODEL = "bulbul:v4-flash"
DEFAULT_LANGUAGE = "bn-IN"
DEFAULT_SPEAKER = "roopa_bn_conversational"


def split_text(text, max_chars=MAX_CHARS_PER_CHUNK):
    """Split text into chunks without intentionally dropping any text."""
    text = text.strip()
    if not text:
        return []

    # First split at paragraph boundaries, then sentence boundaries.
    pieces = re.split(r"(\n\s*\n|(?<=[।.!?])\s+)", text)
    units = []
    current = ""

    for piece in pieces:
        if not piece:
            continue
        if len(current) + len(piece) <= max_chars:
            current += piece
            continue

        if current.strip():
            units.append(current.strip())
            current = ""

        # If one segment is too large, split it at spaces.
        remaining = piece
        while len(remaining) > max_chars:
            cut = remaining.rfind(" ", 0, max_chars + 1)
            if cut <= 0:
                cut = max_chars
            units.append(remaining[:cut].strip())
            remaining = remaining[cut:].strip()

        current = remaining

    if current.strip():
        units.append(current.strip())

    # Safety filter for empty pieces.
    return [unit for unit in units if unit]


def make_audio(text, speaker=DEFAULT_SPEAKER):
    api_key = os.environ.get("SARVAM_API_KEY")
    if not api_key:
        raise RuntimeError(
            "The server is missing SARVAM_API_KEY. Add it to your hosting "
            "provider's environment variables."
        )

    client = SarvamAI(api_subscription_key=api_key)
    chunks = split_text(text)
    if not chunks:
        raise ValueError("The uploaded text file is empty.")

    combined = AudioSegment.empty()

    for index, chunk in enumerate(chunks, start=1):
        response = client.text_to_speech.convert(
            text=chunk,
            model=DEFAULT_MODEL,
            language_code=DEFAULT_LANGUAGE,
            speaker=speaker,
        )

        if not getattr(response, "audios", None):
            raise RuntimeError(
                f"Sarvam AI returned no audio for text segment {index}."
            )

        audio_bytes = base64.b64decode(response.audios[0])
        segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format="wav")

        if index > 1:
            combined += AudioSegment.silent(duration=250)
        combined += segment

    output = io.BytesIO()
    combined.export(output, format="wav")
    output.seek(0)
    return output, len(chunks), len(combined) / 1000


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/convert")
def convert():
    uploaded = request.files.get("text_file")
    speaker = request.form.get("speaker", DEFAULT_SPEAKER)

    allowed_speakers = {"shreya", "meera", "arvind", "manisha", "vidya", "arya"}
    if speaker not in allowed_speakers:
        speaker = DEFAULT_SPEAKER

    if uploaded is None or not uploaded.filename:
        return jsonify(error="Please choose a .txt file first."), 400

    if not uploaded.filename.lower().endswith(".txt"):
        return jsonify(error="Please upload a file with the .txt extension."), 400

    try:
        raw = uploaded.read()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("utf-8")

        if not text.strip():
            return jsonify(error="The uploaded text file is empty."), 400

        audio_stream, chunk_count, duration_seconds = make_audio(text, speaker)
        return send_file(
            audio_stream,
            mimetype="audio/wav",
            as_attachment=True,
            download_name="bengali_audio.wav",
        )

    except UnicodeDecodeError:
        return jsonify(
            error="Could not read this file as UTF-8. Please save it as UTF-8 and upload it again."
        ), 400
    except Exception as exc:
        message = str(exc)
        lower = message.lower()
        if "402" in message or "insufficient_quota" in lower or "no credits" in lower:
            return jsonify(
                error="Sarvam AI reports that there are not enough credits. Check your Sarvam account balance."
            ), 402
        app.logger.exception("Text-to-audio conversion failed")
        return jsonify(error=f"Conversion failed: {message}"), 500


@app.errorhandler(413)
def too_large(_error):
    return jsonify(error="File is too large. The maximum upload size is 5 MB."), 413


if __name__ == "__main__":
    # Local development only. In production, use the hosting provider's server.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
