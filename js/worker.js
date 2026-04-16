import { generateWordlist } from "./generator.js";

const CHUNK_SIZE = 10000;

self.onmessage = (event) => {
  const { type, payload } = event.data || {};
  if (type !== "generate") return;

  try {
    self.postMessage({
      type: "progress",
      payload: { message: "Worker: generating candidate patterns..." }
    });

    const result = generateWordlist(payload);
    const passwords = result.passwords || [];

    self.postMessage({
      type: "progress",
      payload: { message: `Worker: preparing ${passwords.length} passwords for streaming...` }
    });

    for (let i = 0; i < passwords.length; i += CHUNK_SIZE) {
      const chunk = passwords.slice(i, i + CHUNK_SIZE);
      self.postMessage({
        type: "chunk",
        payload: { passwords: chunk }
      });
    }

    self.postMessage({
      type: "done",
      payload: {
        result: {
          ...result,
          passwords: []
        }
      }
    });
  } catch (error) {
    self.postMessage({
      type: "error",
      payload: {
        message: error instanceof Error ? error.message : "Unknown worker error"
      }
    });
  }
};
