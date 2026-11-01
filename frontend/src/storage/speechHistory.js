const DATABASE_NAME = "multilingual-speech-history";
const DATABASE_VERSION = 1;
const TRANSCRIPTIONS_STORE = "transcriptions";
const SPEECH_STORE = "speech";

function diagnostic(message, details = {}) {
  if (import.meta.env?.DEV) {
    console.debug(`[speech-history] ${message}`, details);
  }
}

function openDatabase() {
  if (!("indexedDB" in globalThis)) {
    return Promise.reject(new Error("IndexedDB is unavailable in this browser."));
  }

  return new Promise((resolve, reject) => {
    diagnostic("opening database", {
      origin: globalThis.location?.origin ?? "unknown",
      database: DATABASE_NAME,
      version: DATABASE_VERSION,
    });
    const request = globalThis.indexedDB.open(DATABASE_NAME, DATABASE_VERSION);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(TRANSCRIPTIONS_STORE)) {
        const store = database.createObjectStore(TRANSCRIPTIONS_STORE, { keyPath: "id" });
        store.createIndex("createdAt", "createdAt");
      }
      if (!database.objectStoreNames.contains(SPEECH_STORE)) {
        const store = database.createObjectStore(SPEECH_STORE, { keyPath: "id" });
        store.createIndex("createdAt", "createdAt");
      }
      diagnostic("database upgrade complete", {
        stores: Array.from(database.objectStoreNames),
      });
    };
    request.onsuccess = () => {
      diagnostic("database opened", {
        stores: Array.from(request.result.objectStoreNames),
      });
      resolve(request.result);
    };
    request.onerror = () => {
      diagnostic("database open failed", { error: request.error?.name });
      reject(request.error ?? new Error("Could not open local history storage."));
    };
    request.onblocked = () => {
      diagnostic("database open blocked");
      reject(new Error("Local history storage is blocked by another database connection."));
    };
  });
}

function transactionRequest(database, storeName, mode, operation, operationName) {
  return new Promise((resolve, reject) => {
    let result;
    let request;
    let settled = false;
    let transaction;
    try {
      transaction = database.transaction(storeName, mode);
      diagnostic("transaction started", { store: storeName, mode, operation: operationName });
      request = operation(transaction.objectStore(storeName));
    } catch (error) {
      reject(error);
      return;
    }

    request.onsuccess = () => {
      result = request.result;
    };
    request.onerror = () => {
      if (!settled) {
        settled = true;
        reject(request.error ?? new Error("Local history storage operation failed."));
      }
    };
    transaction.oncomplete = () => {
      diagnostic("transaction complete", { store: storeName, operation: operationName });
      if (!settled) {
        settled = true;
        resolve(result);
      }
    };
    transaction.onerror = () => {
      diagnostic("transaction error", {
        store: storeName,
        operation: operationName,
        error: transaction.error?.name,
      });
      if (!settled) {
        settled = true;
        reject(transaction.error ?? new Error("Local history storage transaction failed."));
      }
    };
    transaction.onabort = () => {
      diagnostic("transaction aborted", { store: storeName, operation: operationName });
      if (!settled) {
        settled = true;
        reject(new Error("Local history storage transaction was aborted."));
      }
    };
  });
}

function storageError(error) {
  if (error?.name === "QuotaExceededError") {
    return new Error("Browser storage is full. Delete some history and try again.");
  }
  return error instanceof Error ? error : new Error("Could not save local history.");
}

async function withDatabase(operation) {
  try {
    const database = await openDatabase();
    try {
      return await operation(database);
    } finally {
      database.close();
    }
  } catch (error) {
    throw storageError(error);
  }
}

async function saveAndVerify(storeName, record, recordType) {
  return withDatabase(async (database) => {
    diagnostic("save started", { recordType, id: record.id });
    await transactionRequest(
      database,
      storeName,
      "readwrite",
      (store) => store.put(record),
      `save:${recordType}`,
    );
    const saved = await transactionRequest(
      database,
      storeName,
      "readonly",
      (store) => store.get(record.id),
      `verify:${recordType}`,
    );
    if (!saved) {
      throw new Error(`Local ${recordType} history could not be verified after saving.`);
    }
    diagnostic("save verified", { recordType, id: record.id });
    return saved;
  });
}

export async function saveTranscription(record) {
  return saveAndVerify(TRANSCRIPTIONS_STORE, record, "transcription");
}

export async function saveSpeech(record) {
  return saveAndVerify(SPEECH_STORE, record, "speech");
}

export async function getHistory() {
  return withDatabase(async (database) => {
    const [transcriptions, speech] = await Promise.all([
      transactionRequest(database, TRANSCRIPTIONS_STORE, "readonly", (store) => store.getAll(), "load:transcriptions"),
      transactionRequest(database, SPEECH_STORE, "readonly", (store) => store.getAll(), "load:speech"),
    ]);
    diagnostic("history restored", {
      transcriptions: transcriptions.length,
      speech: speech.length,
    });
    return {
      transcriptions: transcriptions.sort((a, b) => b.createdAt - a.createdAt),
      speech: speech.sort((a, b) => b.createdAt - a.createdAt),
    };
  });
}

export async function deleteTranscription(id) {
  return withDatabase((database) =>
    transactionRequest(database, TRANSCRIPTIONS_STORE, "readwrite", (store) => store.delete(id), "delete:transcription"),
  );
}

export async function deleteSpeech(id) {
  return withDatabase((database) =>
    transactionRequest(database, SPEECH_STORE, "readwrite", (store) => store.delete(id), "delete:speech"),
  );
}

export async function clearHistory() {
  return withDatabase(async (database) => {
    await Promise.all([
      transactionRequest(database, TRANSCRIPTIONS_STORE, "readwrite", (store) => store.clear(), "clear:transcriptions"),
      transactionRequest(database, SPEECH_STORE, "readwrite", (store) => store.clear(), "clear:speech"),
    ]);
  });
}

export async function requestPersistentStorage() {
  if (!navigator.storage?.persist) return false;
  try {
    return await navigator.storage.persist();
  } catch {
    return false;
  }
}

export async function getStorageEstimate() {
  if (!navigator.storage?.estimate) return null;
  return navigator.storage.estimate();
}
