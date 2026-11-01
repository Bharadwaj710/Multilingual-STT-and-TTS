import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import {
  clearHistory,
  deleteSpeech,
  deleteTranscription,
  getHistory,
  getStorageEstimate,
  requestPersistentStorage,
  saveSpeech,
  saveTranscription,
} from "./storage/speechHistory";

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
  const nextSequenceRef = useRef(0);
  const nextDisplaySequenceRef = useRef(0);
  const pendingChunksRef = useRef(new Map());
  const audioRef = useRef(null);
  const audioUrlRef = useRef(null);
  const abortControllerRef = useRef(null);
  const transcriptionControllersRef = useRef(new Set());
  const isMountedRef = useRef(true);
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
  const [history, setHistory] = useState({ transcriptions: [], speech: [] });
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState("");
  const [storageNotice, setStorageNotice] = useState("");
  const objectUrlsRef = useRef(new Set());
  const persistedSequencesRef = useRef(new Set());

  useEffect(() => {
    let active = true;
    async function restoreHistory() {
      try {
        const restored = await getHistory();
        if (active) {
          setHistory(restored);
          persistedSequencesRef.current = new Set(
            restored.transcriptions.map((record) => record.sequence),
          );
        }
        await requestPersistentStorage();
        const estimate = await getStorageEstimate();
        if (active && estimate?.usage && estimate?.quota) {
          setStorageNotice("History is stored locally in this browser.");
        } else if (active) {
          setStorageNotice("History is stored locally in this browser.");
        }
      } catch (err) {
        if (active) {
          setHistoryError(err instanceof Error ? err.message : "Could not restore local history.");
        }
      } finally {
        if (active) setHistoryLoading(false);
      }
    }
    void restoreHistory();
    return () => {
      active = false;
      objectUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
      objectUrlsRef.current.clear();
    };
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      transcriptionControllersRef.current.forEach((controller) => controller.abort());
    };
  }, []);

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
    
    const controller = new AbortController();
    abortControllerRef.current = controller;
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/speak`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: mergedTranscript, voice: ttsVoice }),
        signal: controller.signal,
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || "TTS request failed");
      }
      const blob = await response.blob();
      if (controller.signal.aborted) {
        setIsSpeaking(false);
        return;
      }
      const speechRecord = {
        id: crypto.randomUUID(),
        text: mergedTranscript,
        audioBlob: blob,
        voice: ttsVoice,
        createdAt: Date.now(),
      };
      try {
        await saveSpeech(speechRecord);
        setHistory((current) => ({
          ...current,
          speech: [speechRecord, ...current.speech],
        }));
      } catch (storageErr) {
        setHistoryError(storageErr instanceof Error ? storageErr.message : "Could not save local speech history.");
      }
      const url = URL.createObjectURL(blob);
      objectUrlsRef.current.add(url);
      const audio = new Audio(url);
      audioUrlRef.current = url;
      
      audioRef.current = audio;
      
      audio.onended = () => {
        setIsSpeaking(false);
        audioRef.current = null;
        audioUrlRef.current = null;
        URL.revokeObjectURL(url);
        objectUrlsRef.current.delete(url);
      };
      audio.onerror = () => {
        if (!abortControllerRef.current?.signal.aborted) {
          setTtsError("Failed to play audio");
          setIsSpeaking(false);
        }
        audioRef.current = null;
        audioUrlRef.current = null;
        URL.revokeObjectURL(url);
        objectUrlsRef.current.delete(url);
      };
      await audio.play();
    } catch (err) {
      if (err.name !== "AbortError") {
        setTtsError(err instanceof Error ? err.message : "Unexpected TTS error");
        setIsSpeaking(false);
      }
    }
  }

  async function playStoredAudio(blob) {
    stopTTS();
    setIsSpeaking(true);
    setTtsError("");
    const url = URL.createObjectURL(blob);
    objectUrlsRef.current.add(url);
    const audio = new Audio(url);
    audioUrlRef.current = url;
    audioRef.current = audio;
    audio.onended = () => {
      setIsSpeaking(false);
      audioRef.current = null;
      audioUrlRef.current = null;
      URL.revokeObjectURL(url);
      objectUrlsRef.current.delete(url);
    };
    audio.onerror = () => {
      setTtsError("Failed to play stored audio");
      setIsSpeaking(false);
      audioRef.current = null;
      audioUrlRef.current = null;
      URL.revokeObjectURL(url);
      objectUrlsRef.current.delete(url);
    };
    try {
      await audio.play();
    } catch (err) {
      setIsSpeaking(false);
      audioRef.current = null;
      audioUrlRef.current = null;
      URL.revokeObjectURL(url);
      objectUrlsRef.current.delete(url);
      setTtsError(err instanceof Error ? err.message : "Failed to play stored audio");
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
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      objectUrlsRef.current.delete(audioUrlRef.current);
      audioUrlRef.current = null;
    }
    
    // 3. Reset UI state instantly
    setIsSpeaking(false);
  }

  function commitResolvedChunk(sequence, chunk) {
    if (sequence < nextDisplaySequenceRef.current || pendingChunksRef.current.has(sequence)) {
      return;
    }

    pendingChunksRef.current.set(sequence, chunk);
    const readyChunks = [];

    while (pendingChunksRef.current.has(nextDisplaySequenceRef.current)) {
      const nextChunk = pendingChunksRef.current.get(nextDisplaySequenceRef.current);
      pendingChunksRef.current.delete(nextDisplaySequenceRef.current);
      nextDisplaySequenceRef.current += 1;
      if (nextChunk) readyChunks.push(nextChunk);
    }

    if (readyChunks.length && isMountedRef.current) {
      setChunks((current) => {
        const displayedSequences = new Set(current.map((item) => item.sequence));
        return [...current, ...readyChunks.filter((item) => !displayedSequences.has(item.sequence))];
      });
    }
  }

  async function sendChunk(blob, sequence) {
    if (blob.size < 1000) {
      commitResolvedChunk(sequence, null);
      return;
    }

    const formData = new FormData();
    formData.append("audio", blob, `chunk-${Date.now()}.webm`);
    if (language) formData.append("language", language);
    formData.append("sequence", String(sequence));

    activeTranscriptionsRef.current += 1;
    if (isMountedRef.current) setIsBusy(true);
    const controller = new AbortController();
    transcriptionControllersRef.current.add(controller);
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/transcribe`, {
        method: "POST",
        body: formData,
        signal: controller.signal,
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || "Transcription request failed");
      }

      const data = await response.json();
      if (Number.isInteger(data.sequence) && data.sequence !== sequence) {
        throw new Error("Transcription response sequence did not match the recorded chunk");
      }
      const responseSequence = Number.isInteger(data.sequence) ? data.sequence : sequence;
      const transcriptChunk = data.text?.trim() && !data.skipped
        ? {
            id: responseSequence,
            sequence: responseSequence,
            text: data.text.trim(),
            language: data.language,
            confidence: data.language_probability,
          }
        : null;
      commitResolvedChunk(
        responseSequence,
        transcriptChunk,
      );
      if (
        transcriptChunk
        && !controller.signal.aborted
        && !persistedSequencesRef.current.has(responseSequence)
      ) {
        const record = {
          id: crypto.randomUUID(),
          filename: `chunk-${sequence}.webm`,
          audioBlob: blob,
          text: transcriptChunk.text,
          language: data.language,
          languageProbability: data.language_probability,
          duration: data.duration,
          sequence: responseSequence,
          createdAt: Date.now(),
        };
        try {
          await saveTranscription(record);
          persistedSequencesRef.current.add(responseSequence);
          if (isMountedRef.current) {
            setHistory((current) => ({
              ...current,
              transcriptions: [record, ...current.transcriptions],
            }));
          }
        } catch (storageErr) {
          if (isMountedRef.current) {
            setHistoryError(storageErr instanceof Error ? storageErr.message : "Could not save local history.");
          }
        }
      }
    } catch (err) {
      commitResolvedChunk(sequence, null);
      const isAbort = err instanceof Error && err.name === "AbortError";
      if (!isAbort && isMountedRef.current) {
        setError(err instanceof Error ? err.message : "Unexpected transcription error");
      }
    } finally {
      transcriptionControllersRef.current.delete(controller);
      activeTranscriptionsRef.current -= 1;
      if (activeTranscriptionsRef.current <= 0 && isMountedRef.current) {
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
      const sequence = nextSequenceRef.current++;
      void sendChunk(blob, sequence);

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

  function clearTranscript() {
    setChunks([]);
    pendingChunksRef.current.clear();
    // Ignore responses for requests that were already in flight when Clear was clicked.
    nextDisplaySequenceRef.current = nextSequenceRef.current;
  }

  async function removeTranscription(id) {
    try {
      await deleteTranscription(id);
      setHistory((current) => ({
        ...current,
        transcriptions: current.transcriptions.filter((record) => record.id !== id),
      }));
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "Could not delete history.");
    }
  }

  async function removeSpeech(id) {
    try {
      await deleteSpeech(id);
      setHistory((current) => ({
        ...current,
        speech: current.speech.filter((record) => record.id !== id),
      }));
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "Could not delete history.");
    }
  }

  async function removeAllHistory() {
    if (!window.confirm("Delete all locally stored transcription and speech history?")) return;
    try {
      await clearHistory();
      setHistory({ transcriptions: [], speech: [] });
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "Could not clear history.");
    }
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
          <button className="secondary" onClick={clearTranscript} disabled={!chunks.length}>
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

      <section className="panel history-panel" aria-live="polite">
        <div className="panel-header">
          <div>
            <h2>Local history</h2>
            <p className="local-storage-note">{storageNotice || "Stored only in this browser."}</p>
          </div>
          <button
            className="secondary compact-button"
            onClick={removeAllHistory}
            disabled={historyLoading || (!history.transcriptions.length && !history.speech.length)}
          >
            Clear all
          </button>
        </div>
        {historyError && <p className="error">{historyError}</p>}
        {historyLoading ? (
          <p className="empty">Loading saved history...</p>
        ) : !history.transcriptions.length && !history.speech.length ? (
          <p className="empty">No saved recordings or generated speech yet.</p>
        ) : (
          <div className="history-columns">
            <div>
              <h3>Transcriptions</h3>
              {history.transcriptions.length ? history.transcriptions.map((record) => (
                <article className="history-card" key={record.id}>
                  <div className="history-card-header">
                    <small>{new Date(record.createdAt).toLocaleString()}</small>
                    <button className="text-button" onClick={() => removeTranscription(record.id)}>Delete</button>
                  </div>
                  <p>{record.text}</p>
                  <small>
                    {record.language || "unknown"} · {record.filename}
                    {typeof record.languageProbability === "number"
                      ? ` · ${Math.round(record.languageProbability * 100)}% confidence`
                      : ""}
                  </small>
                  <button className="secondary compact-button" onClick={() => playStoredAudio(record.audioBlob)}>
                    Play original audio
                  </button>
                </article>
              )) : <p className="empty">No transcription history.</p>}
            </div>
            <div>
              <h3>Generated speech</h3>
              {history.speech.length ? history.speech.map((record) => (
                <article className="history-card" key={record.id}>
                  <div className="history-card-header">
                    <small>{new Date(record.createdAt).toLocaleString()}</small>
                    <button className="text-button" onClick={() => removeSpeech(record.id)}>Delete</button>
                  </div>
                  <p>{record.text}</p>
                  <small>{record.voice}</small>
                  <button className="secondary compact-button" onClick={() => playStoredAudio(record.audioBlob)}>
                    Play generated audio
                  </button>
                </article>
              )) : <p className="empty">No speech history.</p>}
            </div>
          </div>
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
