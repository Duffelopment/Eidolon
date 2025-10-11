const portraitCanvas = document.getElementById("portrait-canvas");
const portraitCtx = portraitCanvas.getContext("2d");
const learnBtn = document.getElementById("learn-btn");
const talkBtn = document.getElementById("talk-btn");
const statusEl = document.getElementById("status");
const liveVideo = document.getElementById("live-video");
const responseAudio = document.getElementById("response-audio");

const portraitState = {
  hue: 190,
  amplitude: 0,
  targetAmplitude: 0,
  shimmer: 0,
  listening: false,
  speaking: false,
  lastWave: 0,
};

function setStatus(message, tone = "info") {
  statusEl.textContent = message;
  const tones = {
    info: "text-slate-400",
    success: "text-emerald-300",
    warning: "text-amber-300",
    error: "text-rose-300",
  };
  statusEl.className = `max-w-xl text-sm transition ${tones[tone] || tones.info}`;
}

function resizeCanvas() {
  const frame = portraitCanvas.parentElement;
  portraitCanvas.width = frame.clientWidth;
  portraitCanvas.height = frame.clientHeight;
}

window.addEventListener("resize", resizeCanvas);
resizeCanvas();

function drawPortrait(timestamp) {
  const ctx = portraitCtx;
  const { width, height } = portraitCanvas;
  const gradient = ctx.createRadialGradient(
    width / 2,
    height / 2,
    Math.min(width, height) * 0.1,
    width / 2,
    height / 2,
    Math.max(width, height)
  );
  const amp = portraitState.amplitude;
  gradient.addColorStop(0, `rgba(165, 243, 252, ${0.55 + amp * 0.4})`);
  gradient.addColorStop(0.45, `rgba(59, 130, 246, ${0.25 + amp * 0.25})`);
  gradient.addColorStop(1, "rgba(15, 23, 42, 0.9)");

  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  const orbCount = 3;
  for (let i = 0; i < orbCount; i += 1) {
    const phase = timestamp * 0.0002 + i * 2;
    const radius = (Math.min(width, height) * 0.15) * (1 + amp * 0.6);
    const x = width / 2 + Math.cos(phase) * (width * 0.18 + amp * 60);
    const y = height / 2 + Math.sin(phase * 1.4) * (height * 0.12 + amp * 45);
    const radial = ctx.createRadialGradient(x, y, radius * 0.1, x, y, radius);
    radial.addColorStop(0, `rgba(236, 233, 255, ${0.7 - i * 0.15})`);
    radial.addColorStop(1, `rgba(56, 189, 248, ${0.05})`);
    ctx.globalCompositeOperation = "lighter";
    ctx.fillStyle = radial;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.globalCompositeOperation = "source-over";

  const waveHeight = amp * 120 + (portraitState.speaking ? 35 : 12);
  const segments = 200;
  ctx.beginPath();
  for (let i = 0; i <= segments; i += 1) {
    const t = i / segments;
    const noise = Math.sin(timestamp * 0.001 + t * 10) * amp * 30;
    const x = t * width;
    const y = height / 2 + Math.sin(t * Math.PI * 2 + timestamp * 0.0015) * waveHeight + noise;
    ctx.lineTo(x, y);
  }
  ctx.strokeStyle = `rgba(129, 140, 248, ${0.35 + amp * 0.4})`;
  ctx.lineWidth = 2 + amp * 8;
  ctx.shadowBlur = 40 + amp * 100;
  ctx.shadowColor = "rgba(94, 234, 212, 0.35)";
  ctx.stroke();
  ctx.shadowBlur = 0;

  portraitState.amplitude += (portraitState.targetAmplitude - portraitState.amplitude) * 0.08;
  portraitState.targetAmplitude *= 0.94;

  requestAnimationFrame(drawPortrait);
}

requestAnimationFrame(drawPortrait);

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function bestMimeType(preferences) {
  for (const type of preferences) {
    if (MediaRecorder.isTypeSupported(type)) {
      return type;
    }
  }
  return "video/webm";
}

function monitorAmplitude(stream) {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) {
    return () => Promise.resolve(0);
  }
  const audioCtx = new AudioContextClass();
  const analyser = audioCtx.createAnalyser();
  analyser.fftSize = 512;
  const buffer = new Float32Array(analyser.fftSize);
  const source = audioCtx.createMediaStreamSource(stream);
  source.connect(analyser);
  let running = true;
  let sum = 0;
  let count = 0;

  const tick = () => {
    if (!running) {
      return;
    }
    analyser.getFloatTimeDomainData(buffer);
    let rmsSum = 0;
    for (let i = 0; i < buffer.length; i += 1) {
      rmsSum += buffer[i] * buffer[i];
    }
    const rms = Math.sqrt(rmsSum / buffer.length);
    sum += rms;
    count += 1;
    portraitState.targetAmplitude = Math.max(rms * 2, portraitState.targetAmplitude * 0.96);
    requestAnimationFrame(tick);
  };
  tick();

  return async () => {
    running = false;
    try {
      await audioCtx.close();
    } catch (error) {
      console.warn("Audio context close failed", error);
    }
    return count ? sum / count : 0;
  };
}

async function recordSession({ duration = 15000, statusLabel = "", video = true } = {}) {
  setStatus(statusLabel || "Capturing your presence…");
  const constraints = { audio: true, video };
  const stream = await navigator.mediaDevices.getUserMedia(constraints);
  liveVideo.srcObject = stream;
  liveVideo.muted = true;
  liveVideo.play().catch(() => {});
  liveVideo.classList.remove("hidden");

  const stopMonitor = monitorAmplitude(stream);

  const mimeType = bestMimeType([
    "video/webm;codecs=vp9,opus",
    "video/webm;codecs=vp8,opus",
    "video/mp4",
    "audio/webm",
  ]);

  const recorder = new MediaRecorder(stream, { mimeType });
  const chunks = [];
  recorder.ondataavailable = (event) => {
    if (event.data.size > 0) {
      chunks.push(event.data);
    }
  };

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition;
  let transcript = "";
  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        if (result.isFinal) {
          transcript += `${result[0].transcript} `;
        } else {
          interim += result[0].transcript;
        }
      }
      setStatus(`Listening… ${transcript || interim}`.trim());
    };
    recognition.onerror = (event) => {
      console.warn("Speech recognition error", event.error);
    };
    recognition.start();
  }

  portraitState.listening = true;
  recorder.start(250);
  await wait(duration);
  recorder.stop();

  const stopped = new Promise((resolve, reject) => {
    recorder.onstop = resolve;
    recorder.onerror = reject;
  });

  await stopped;

  portraitState.listening = false;
  if (recognition) {
    recognition.stop();
    await new Promise((resolve) => {
      recognition.onend = resolve;
      setTimeout(resolve, 1000);
    });
  }

  const blob = new Blob(chunks, { type: mimeType });

  const averageAmplitude = await stopMonitor();
  stream.getTracks().forEach((track) => track.stop());
  liveVideo.pause();
  liveVideo.srcObject = null;
  liveVideo.classList.add("hidden");

  return { blob, transcript: transcript.trim(), amplitude: averageAmplitude };
}

async function sendLearnSession() {
  try {
    learnBtn.disabled = true;
    talkBtn.disabled = true;
    portraitState.listening = true;
    const session = await recordSession({ duration: 30000, statusLabel: "Learning your tone…" });
    setStatus("Encoding your essence…");

    const formData = new FormData();
    formData.append("media", session.blob, "learn_session.webm");
    if (session.transcript) {
      formData.append("transcript", session.transcript);
    }
    if (session.amplitude) {
      formData.append("amplitude", session.amplitude.toString());
    }

    const response = await fetch("/api/learn", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Learn failed: ${response.status}`);
    }

    const payload = await response.json();
    portraitState.targetAmplitude = 0.5;
    setStatus(
      payload.transcript_captured
        ? "The portrait has learned your cadence."
        : "The portrait has archived your presence."
    , "success");
  } catch (error) {
    console.error(error);
    setStatus("Learning failed. Please try again.", "error");
  } finally {
    portraitState.listening = false;
    learnBtn.disabled = false;
    talkBtn.disabled = false;
  }
}

async function sendTalkSession() {
  try {
    learnBtn.disabled = true;
    talkBtn.disabled = true;
    portraitState.listening = true;
    const session = await recordSession({ duration: 12000, statusLabel: "Listening to you…", video: true });
    const prompt = session.transcript || "A silent gaze";
    setStatus("Summoning a response…");

    const response = await fetch("/api/respond", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, amplitude: session.amplitude }),
    });

    if (!response.ok) {
      throw new Error(`Respond failed: ${response.status}`);
    }

    const payload = await response.json();
    portraitState.speaking = true;
    portraitState.targetAmplitude = 0.8;
    setStatus(payload.text, "success");

    if (payload.audio) {
      responseAudio.src = `data:audio/mp3;base64,${payload.audio}`;
      await responseAudio.play().catch((error) => {
        console.warn("Playback failed", error);
      });
    }

    await wait(2000);
  } catch (error) {
    console.error(error);
    setStatus("The portrait could not respond. Please try again.", "error");
  } finally {
    portraitState.speaking = false;
    portraitState.listening = false;
    learnBtn.disabled = false;
    talkBtn.disabled = false;
  }
}

learnBtn.addEventListener("click", () => {
  sendLearnSession();
});

talkBtn.addEventListener("click", () => {
  sendTalkSession();
});

setStatus("Invite the portrait to listen or speak.");
