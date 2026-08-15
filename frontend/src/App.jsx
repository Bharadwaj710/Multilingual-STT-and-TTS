import React, { useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const CHUNK_MS = 5000;

const LANGUAGE_OPTIONS = [
  { label: "Auto detect", value: "" },
  { label: "English", value: "en" },
  { label: "Hindi", value: "hi" },
  { label: "Marathi", value: "mr" },
  { label: "Tamil", value: "ta" },
  { label: "Telugu", value: "te" },
];

const TTS_VOICES = [
  { label: "Auto-Detect", value: "hi-IN-SwaraNeural" },
  { label: "English", value: "en-US-AvaNeural" },
  { label: "Marathi", value: "mr-IN-AarohiNeural" },
  { label: "Tamil", value: "ta-IN-PallaviNeural" },
  { label: "Telugu", value: "te-IN-ShrutiNeural" },
];

function App() {
  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const isRecordingRef = useRef(false);
  const chunkIdRef = useRef(0);
  const audioRef = useRef(null);
  const abortControllerRef = useRef(null);
  const activeTranscriptionsRef = useRef(0);
  const streamLockRef = useRef(false);
  
  const [isRecording, setIsRecording] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [isPreparing, setIsPreparing] = useState(false);
  const [modelReady, setModelReady] = useState(false);
  const [chunks, setChunks] = useState([]);
  const [language, setLanguage] = useState("");
  const [error, setError] = useState("");
  
  const [ttsVoice, setTtsVoice] = useState(TTS_VOICES[0].value);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [ttsError, setTtsError] = useState("");

  const mergedTranscript = chunks
    .map((chunk) => chunk.text)
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();


  async function prepareModel() {
    if (modelReady) return;

    setIsPreparing(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/model/warmup`, {
        method: "POST",
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || "Model warmup failed");
      }

      setModelReady(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not prepare transcription model");
      throw err;
    } finally {
      setIsPreparing(false);
    }
  }

  async function playTTS() {
    if (!mergedTranscript.trim()) return;
    
    // Clear any existing processes before starting a new one
    stopTTS();

    setIsSpeaking(true);
    setTtsError("");
    
    abortControllerRef.current = new AbortController();
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/speak`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: mergedTranscript, voice: ttsVoice }),
        signal: abortControllerRef.current.signal,
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || "TTS request failed");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      
      // If the user hit stop while we were generating the blob, cancel play
      if (abortControllerRef.current?.signal.aborted) return;
      
      audioRef.current = audio;
      
      audio.onended = () => {
        setIsSpeaking(false);
        audioRef.current = null;
      };
      audio.onerror = () => {
        if (!abortControllerRef.current?.signal.aborted) {
          setTtsError("Failed to play audio");
          setIsSpeaking(false);
        }
        audioRef.current = null;
      };
      await audio.play();
    } catch (err) {
      if (err.name !== "AbortError") {
        setTtsError(err instanceof Error ? err.message : "Unexpected TTS error");
        setIsSpeaking(false);
      }
    }
  }

  function stopTTS() {
    // 1. Cancel the fetch request if it's currently generating
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    
    // 2. Stop the actual audio element if it's currently playing
    if (audioRef.current) {
      // Catch DOMException on pause for uninitialized audio
      try {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      } catch (e) {}
      audioRef.current = null;
    }
    
    // 3. Reset UI state instantly
    setIsSpeaking(false);
  }

  async function sendChunk(blob) {
    if (blob.size < 1000) return;

    const formData = new FormData();
    formData.append("audio", blob, `chunk-${Date.now()}.webm`);
    if (language) formData.append("language", language);

    activeTranscriptionsRef.current += 1;
    setIsBusy(true);
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/transcribe`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || "Transcription request failed");
      }

      const data = await response.json();
      if (data.text?.trim() && !data.skipped) {
        setChunks((current) => [
          ...current,
          {
            id: chunkIdRef.current++,
            text: data.text.trim(),
            language: data.language,
            confidence: data.language_probability,
          },
        ]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected transcription error");
    } finally {
      activeTranscriptionsRef.current -= 1;
      if (activeTranscriptionsRef.current <= 0) {
        setIsBusy(false);
      }
    }
  }

  async function startRecording() {
    if (isRecordingRef.current || streamLockRef.current) return;
    
    streamLockRef.current = true;
    try {
      setError("");
      await prepareModel();
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      isRecordingRef.current = true;
      setIsRecording(true);
      recordSegment(stream);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Microphone permission failed");
    } finally {
      streamLockRef.current = false;
    }
  }

  function recordSegment(stream) {
    if (!isRecordingRef.current) return;

    const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    const parts = [];
    recorderRef.current = recorder;

    let timeoutId;

    recorder.ondataavailable = (event) => {
      if (event.data.size) parts.push(event.data);
    };

    recorder.onstop = () => {
      clearTimeout(timeoutId);
      const blob = new Blob(parts, { type: recorder.mimeType || "audio/webm" });
      void sendChunk(blob);

      if (isRecordingRef.current) {
        recordSegment(stream);
      }
    };

    recorder.start();
    timeoutId = window.setTimeout(() => {
      if (recorder.state === "recording") recorder.stop();
    }, CHUNK_MS);
  }

  function stopRecording() {
    isRecordingRef.current = false;
    recorderRef.current?.stop();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    recorderRef.current = null;
    streamRef.current = null;
    setIsRecording(false);
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">Multilingual STT and TTS</p>
        <h1>Multilingual speech to text, chunk by chunk.</h1>
        <p className="subcopy">
          Speak naturally in English, Hindi, or a mix of both. The browser sends short audio
          chunks to a FastAPI backend running an open-source Whisper model.
        </p>
        <div className="controls">
          <button
            className={isRecording ? "danger" : "primary"}
            onClick={isRecording ? stopRecording : startRecording}
            disabled={isPreparing}
          >
            {isPreparing ? "Preparing model..." : isRecording ? "Stop recording" : "Start recording"}
          </button>
          <button className="secondary" onClick={() => setChunks([])} disabled={!chunks.length}>
            Clear
          </button>
        </div>
        <label className="field">
          <span>Language hint</span>
          <select
            value={language}
            onChange={(event) => setLanguage(event.target.value)}
            disabled={isRecording}
          >
            {LANGUAGE_OPTIONS.map((option) => (
              <option key={option.value || "auto"} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <div className="status-row">
          <span className={isRecording ? "dot live" : "dot"} />
          <span>
            {isPreparing
              ? "Downloading/loading model on first run"
              : isRecording
                ? `Recording ${CHUNK_MS / 1000}s chunks`
                : isBusy 
                  ? "Finalizing background transcripts..."
                  : modelReady
                    ? "Model ready"
                    : "Idle"}
          </span>
          {isBusy && isRecording && <span>(Transcribing processing...)</span>}
        </div>
        {error && <p className="error">{error}</p>}
      </section>

      <section className="panel" aria-live="polite">
        <div className="panel-header">
          <h2>Transcript</h2>
          <span>{chunks.length} chunks</span>
        </div>
        {chunks.length ? (
          <>
            <article className="merged-card">
              <div className="merged-header">
                <span>Combined transcript / Text-To-Speech</span>
                <div className="tts-inline-controls">
                  <select
                    value={ttsVoice}
                    onChange={(e) => setTtsVoice(e.target.value)}
                    disabled={isSpeaking}
                    className="tts-voice-select"
                    title="Select Voice"
                  >
                    {TTS_VOICES.map((v) => (
                      <option key={v.value} value={v.value}>
                        {v.label}
                      </option>
                    ))}
                  </select>
                  <button
                    className={`tts-play-btn ${isSpeaking ? "stop" : "play"}`}
                    onClick={isSpeaking ? stopTTS : playTTS}
                    disabled={isPreparing}
                    title={isSpeaking ? "Stop playback" : "Play transcript aloud"}
                  >
                    {isSpeaking ? "⏹" : "▶"}
                  </button>
                </div>
              </div>
              <p>{mergedTranscript}</p>
              {ttsError && <p className="error" style={{ fontSize: "0.85rem", marginTop: "1rem" }}>{ttsError}</p>}
            </article>
            <div className="transcript">
              {chunks.map((chunk) => (
                <article key={chunk.id} className="chunk-card">
                  <p>{chunk.text}</p>
                  <small>
                    Chunk {chunk.id + 1} · {chunk.language || "auto"}{" "}
                    {typeof chunk.confidence === "number"
                      ? `(${Math.round(chunk.confidence * 100)}%)`
                      : ""}
                  </small>
                </article>
              ))}
            </div>
          </>
        ) : (
          <p className="empty">Start recording to see live chunk transcriptions here.</p>
        )}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
