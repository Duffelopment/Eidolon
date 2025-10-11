import base64
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import cv2
import mediapipe as mp
import numpy as np
import pyttsx3
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency guard
    OpenAI = None  # type: ignore

from sentence_transformers import SentenceTransformer

APP_ROOT = Path(__file__).parent
MODELS_DIR = APP_ROOT / "models"
VOICES_DIR = APP_ROOT / "voices"
USER_DATA_PATH = MODELS_DIR / "user_data.json"

MODELS_DIR.mkdir(exist_ok=True)
VOICES_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
CORS(app)

mp_face_mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1)

def _load_engine() -> pyttsx3.Engine:
    engine = pyttsx3.init()
    engine.setProperty("rate", 165)
    engine.setProperty("volume", 0.9)
    return engine


_tts_engine: Optional[pyttsx3.Engine] = None
_sentence_model: Optional[SentenceTransformer] = None


def get_sentence_model() -> SentenceTransformer:
    global _sentence_model
    if _sentence_model is None:
        _sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _sentence_model


def load_user_data() -> Dict[str, Any]:
    if USER_DATA_PATH.exists():
        with USER_DATA_PATH.open("r", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                pass
    return {
        "embeddings": [],
        "transcripts": [],
        "gestures": [],
        "voice_samples": [],
        "last_updated": None,
    }


def save_user_data(data: Dict[str, Any]) -> None:
    USER_DATA_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def store_voice_sample(file_storage) -> str:
    timestamp = int(time.time() * 1000)
    extension = Path(file_storage.filename or "sample.webm").suffix or ".webm"
    filename = f"sample_{timestamp}{extension}"
    save_path = VOICES_DIR / filename
    file_storage.save(save_path)
    return filename


def extract_facial_metrics(video_path: Path) -> Dict[str, float]:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        return {"confidence": 0.0, "mean_mouth_aspect": 0.0, "frame_count": 0}

    total_mouth_aspect = 0.0
    frames = 0

    while True:
        ret, frame = capture.read()
        if not ret:
            break
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = mp_face_mesh.process(rgb_frame)
        if results.multi_face_landmarks:
            frames += 1
            landmarks = results.multi_face_landmarks[0].landmark
            # Simple mouth openness metric using selected landmarks.
            top = np.array([landmarks[13].x, landmarks[13].y])
            bottom = np.array([landmarks[14].x, landmarks[14].y])
            left = np.array([landmarks[78].x, landmarks[78].y])
            right = np.array([landmarks[308].x, landmarks[308].y])
            vertical = np.linalg.norm(top - bottom)
            horizontal = np.linalg.norm(left - right) + 1e-6
            total_mouth_aspect += vertical / horizontal

    capture.release()

    if frames == 0:
        return {"confidence": 0.0, "mean_mouth_aspect": 0.0, "frame_count": 0}

    return {
        "confidence": min(1.0, frames / 30.0),
        "mean_mouth_aspect": total_mouth_aspect / frames,
        "frame_count": frames,
    }


def compute_embedding(text: str) -> Dict[str, Any]:
    model = get_sentence_model()
    embedding = model.encode(text).tolist()
    return {"text": text, "vector": embedding}


def generate_openai_response(prompt: str, persona: Optional[str] = None) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        persona_prefix = f" as {persona}" if persona else ""
        return f"I am a memory of you{persona_prefix}, reflecting: {prompt}"

    client = OpenAI(api_key=api_key)
    system_prompt = (
        "You are the voice of an evolving digital portrait that reflects the user's tone, "
        "memories, and mannerisms in a poetic yet concise way."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Persona hints: {persona or 'unknown'}\n"
                f"Prompt from the user: {prompt}"
            ),
        },
    ]
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=messages,
    )
    return response.output_text


def synthesize_speech(text: str) -> Optional[str]:
    global _tts_engine
    try:
        if _tts_engine is None:
            _tts_engine = _load_engine()
        timestamp = int(time.time() * 1000)
        output_path = VOICES_DIR / f"response_{timestamp}.mp3"
        _tts_engine.save_to_file(text, str(output_path))
        _tts_engine.runAndWait()
        if output_path.exists():
            with output_path.open("rb") as audio_file:
                encoded = base64.b64encode(audio_file.read()).decode("utf-8")
            return encoded
    except Exception:
        pass
    return None


@app.route("/")
def index() -> str:
    return render_template("index.html", project_name=os.environ.get("PROJECT_NAME", "Eidolon"))


@app.route("/api/learn", methods=["POST"])
def api_learn():
    if "media" not in request.files:
        return jsonify({"error": "No media provided"}), 400

    media_file = request.files["media"]
    transcript = request.form.get("transcript", "")
    amplitude = request.form.get("amplitude")

    filename = store_voice_sample(media_file)
    saved_path = VOICES_DIR / filename
    metrics = extract_facial_metrics(saved_path)

    data = load_user_data()
    if transcript:
        embedding = compute_embedding(transcript)
        data["embeddings"].append(embedding)
        data["transcripts"].append(transcript)
    data["gestures"].append({
        "timestamp": int(time.time()),
        "metrics": metrics,
        "amplitude_hint": float(amplitude) if amplitude else None,
    })
    data["voice_samples"].append(filename)
    data["last_updated"] = int(time.time())
    save_user_data(data)

    return jsonify({
        "status": "learned",
        "voice_sample": filename,
        "metrics": metrics,
        "transcript_captured": bool(transcript),
    })


@app.route("/api/respond", methods=["POST"])
def api_respond():
    payload = request.get_json(force=True)
    prompt = payload.get("prompt", "")
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    data = load_user_data()
    persona = " ".join(data.get("transcripts", [])[-3:]) if data.get("transcripts") else None
    response_text = generate_openai_response(prompt, persona)
    audio_base64 = synthesize_speech(response_text)

    return jsonify({
        "text": response_text,
        "audio": audio_base64,
        "persona_hint": persona,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("MODE") == "development")
