# Bengali Text to Audio

A small Flask web application that lets a user upload a UTF-8 `.txt` file, convert it to Bengali speech using Sarvam AI, and download a combined `.wav` file.

## Features

- Browser-based upload and conversion UI
- Bengali (`bn-IN`) TTS using `bulbul:v3`
- Long text split into smaller API requests
- WAV audio chunks combined in memory
- API key read from `SARVAM_API_KEY` environment variable
- No intentional permanent storage of uploads or output audio
- 5 MB upload limit

## Run locally

Python 3.11 or 3.12 is recommended for widest compatibility.

```bash
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# On Windows: .venv\Scripts\activate
pip install -r requirements.txt
export SARVAM_API_KEY="YOUR_REAL_API_KEY"
python app.py
```

Open http://127.0.0.1:5000.

On Windows PowerShell, set the key for the current session with:

```powershell
$env:SARVAM_API_KEY="YOUR_REAL_API_KEY"
```

## Deploy using GitHub + Render

1. Create a **private GitHub repository** and upload these project files.
2. Do not commit a real API key, `.env` file, or private text/audio files.
3. Sign in to Render and choose **New + → Blueprint** (or create a Web Service).
4. Connect the GitHub repository. Render detects `render.yaml`.
5. When prompted, add `SARVAM_API_KEY` in the service environment settings. Do not put the key in `render.yaml`.
6. Deploy. Open the generated Render URL.

If creating the service manually:
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Add environment variable `SARVAM_API_KEY` with your real key.

## Important notes

- Sarvam API access and sufficient account credits are required. An HTTP 402 / insufficient credits response must be resolved in the Sarvam account; deploying the app does not add credits.
- Confirm that `shreya` and any other listed speaker names are supported for `bulbul:v3` and `bn-IN` in your Sarvam account/API version. If not, change the choices in `templates/index.html` and the allowed-speaker set in `app.py` to supported values.
- The upload limit is 5 MB. Very long conversions can take time and may hit provider request, duration, or hosting time limits.
- Audio is held in memory while processing. The app does not intentionally write the uploaded text or generated WAV to disk, but the hosting provider may retain operational logs. Avoid uploading sensitive text.
- This is a starter app. For a public service, add rate limiting, authentication, usage limits, and clearer quota handling before sharing it widely.
