import "fake-indexeddb/auto";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  clearHistory,
  deleteSpeech,
  deleteTranscription,
  getHistory,
  saveSpeech,
  saveTranscription,
} from "./speechHistory";

const DATABASE_NAME = "pelocal-speech-history";

function deleteDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.deleteDatabase(DATABASE_NAME);
    request.onsuccess = resolve;
    request.onerror = () => reject(request.error);
    request.onblocked = () => reject(new Error("database delete was blocked"));
  });
}

function transcriptionRecord(id = "transcription-1") {
  return {
    id,
    filename: "sample.webm",
    audioBlob: new Blob(["audio"], { type: "audio/webm" }),
    text: "hello",
    language: "en",
    languageProbability: 0.9,
    duration: 1.2,
    sequence: 0,
    createdAt: Date.now(),
  };
}

function speechRecord(id = "speech-1") {
  return {
    id,
    text: "hello",
    audioBlob: new Blob(["mp3"], { type: "audio/mpeg" }),
    voice: "en-US-AvaNeural",
    createdAt: Date.now(),
  };
}

describe("speech history IndexedDB storage", () => {
  beforeEach(async () => {
    await deleteDatabase();
  });

  afterEach(async () => {
    await deleteDatabase();
  });

  it("creates both stores and saves records only after commit/read-back", async () => {
    const transcription = transcriptionRecord();
    const speech = speechRecord();

    await expect(saveTranscription(transcription)).resolves.toMatchObject({ id: transcription.id });
    await expect(saveSpeech(speech)).resolves.toMatchObject({ id: speech.id });

    const history = await getHistory();
    expect(history.transcriptions).toHaveLength(1);
    expect(history.speech).toHaveLength(1);
    expect(history.transcriptions[0].audioBlob).toBeInstanceOf(Blob);
    expect(history.speech[0].audioBlob).toBeInstanceOf(Blob);
  });

  it("restores records in newest-first order", async () => {
    const older = { ...transcriptionRecord("older"), createdAt: 1 };
    const newer = { ...transcriptionRecord("newer"), createdAt: 2 };
    await saveTranscription(older);
    await saveTranscription(newer);

    const history = await getHistory();
    expect(history.transcriptions.map((record) => record.id)).toEqual(["newer", "older"]);
  });

  it("deletes individual records and clears both stores", async () => {
    await saveTranscription(transcriptionRecord());
    await saveSpeech(speechRecord());

    await deleteTranscription("transcription-1");
    await deleteSpeech("speech-1");
    expect((await getHistory()).transcriptions).toHaveLength(0);
    expect((await getHistory()).speech).toHaveLength(0);

    await saveTranscription(transcriptionRecord("another"));
    await saveSpeech(speechRecord("another-speech"));
    await clearHistory();
    expect(await getHistory()).toEqual({ transcriptions: [], speech: [] });
  });

  it("rejects when IndexedDB is unavailable", async () => {
    const originalIndexedDb = globalThis.indexedDB;
    try {
      delete globalThis.indexedDB;
      await expect(getHistory()).rejects.toThrow("IndexedDB is unavailable");
    } finally {
      globalThis.indexedDB = originalIndexedDb;
    }
  });

  it("reports quota failures instead of claiming a record was saved", async () => {
    const originalPut = IDBObjectStore.prototype.put;
    IDBObjectStore.prototype.put = () => {
      throw new DOMException("storage full", "QuotaExceededError");
    };
    try {
      await expect(saveSpeech(speechRecord())).rejects.toThrow("Browser storage is full");
    } finally {
      IDBObjectStore.prototype.put = originalPut;
    }
  });
});
