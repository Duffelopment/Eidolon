# Eidolon – A Canvas That Remembers

Eidolon is a "living painting" that listens, watches, and learns from the people who stand before it. The installation blends computer vision, speech analysis, and generative AI to create an evolving portrait that echoes a visitor's tone, gestures, and presence.

## Features

- **Immersive portrait UI** rendered with Tailwind CSS and a custom canvas animation.
- **Learning sessions** that capture webcam and microphone streams, archive voice prints, and derive gesture metrics using MediaPipe and OpenCV.
- **Adaptive memory** backed by local JSON storage and semantic embeddings generated with Sentence Transformers.
- **Conversational responses** produced through the OpenAI Responses API with a text-to-speech fallback powered by `pyttsx3`.
- **Ambient playback** in the browser using the Web Audio API for generated speech.

## Project structure

```
workspace/Eidolon
├── app.py
├── models/
│   └── user_data.json          # created automatically after first learn session
├── voices/
├── requirements.txt
├── static/
│   ├── css/styles.css
│   └── js/app.js
├── templates/
│   └── index.html
└── README.md
```

## Environment setup

Install system dependencies and project libraries:

```bash
apt-get update -y && apt-get install -y ffmpeg libgl1
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

> The additional packages requested in the brief (`sounddevice`, `librosa`, `SpeechRecognition`, `tqdm`, `requests`, `pillow`) are included in `requirements.txt`.

## Configuration

Create a `.env` file or export the required environment variables before starting the server:

```
OPENAI_API_KEY=sk-xxxxx
PROJECT_NAME=Eidolon
MODE=development
```

If no `OPENAI_API_KEY` is provided, the portrait will respond with a deterministic offline fallback message and still synthesize voice locally when possible.

## Running the app

```bash
python app.py
```

Then open the interface at [http://localhost:8080](http://localhost:8080).

## Workflow

1. Click **Learn** to begin a 30 second capture. The portrait stores your recording, extracts facial metrics, and builds an embedding from the transcript.
2. Click **Talk** to share a new message. Eidolon generates a contextual reply and speaks back using synthesized audio.
3. Repeat the cycle to evolve the portrait's understanding over time.

## Notes & limitations

- MediaPipe processing expects files containing video frames. When only audio is available, the system gracefully records the voice sample without gesture data.
- `pyttsx3` relies on local drivers for speech synthesis; in headless environments the fallback may silently skip audio generation.
- Browser speech recognition uses the experimental Web Speech API and may not be available in every browser. Without it, prompts default to a silent reflection message.

## License

This repository is provided as an interactive prototype. Adapt and extend it to craft your own living artworks.
