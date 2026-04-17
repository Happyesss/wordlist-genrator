import { DEFAULT_LIST_SIZE, MAX_RANDOM_COUNT } from "./constants.js";
import {
  clampNumber,
  normalizedField,
  normalizeDobList,
  normalizePhoneList,
  sanitizeSize
} from "./utils.js";
import { generateWordlist } from "./generator.js";
import {
  downloadWordlist,
  setBusyState,
  setProgress,
  updateOutputUI
} from "./ui.js";

const refs = {
  form: document.getElementById("generator-form"),
  ownerNames: document.getElementById("ownerNames"),
  lastNames: document.getElementById("lastNames"),
  familyNames: document.getElementById("familyNames"),
  petNames: document.getElementById("petNames"),
  phoneNumbers: document.getElementById("phoneNumbers"),
  location: document.getElementById("location"),
  interests: document.getElementById("interests"),
  exactDob: document.getElementById("exactDob"),
  listSizeInput: document.getElementById("listSize"),
  includeRouterDefaults: document.getElementById("includeRouterDefaults"),
  includeYears: document.getElementById("includeYears"),
  includeLeet: document.getElementById("includeLeet"),
  includeRandomNumbers: document.getElementById("includeRandomNumbers"),
  randomCount: document.getElementById("randomCount"),
  generateBtn: document.getElementById("generateBtn"),
  cancelBtn: document.getElementById("cancelBtn"),
  downloadBtn: document.getElementById("downloadBtn"),
  outputDownloadBtn: document.getElementById("outputDownloadBtn"),
  output: document.getElementById("output"),
  stats: document.getElementById("stats"),
  warnings: document.getElementById("warnings"),
  commonListsPopup: document.getElementById("commonListsPopup"),
  closeCommonListsBtn: document.getElementById("closeCommonListsBtn")
};

let activeWorker = null;

function collectInput() {
  const warnings = [];

  const owners = normalizedField(refs.ownerNames.value, warnings, "Owner names");
  const lastNames = normalizedField(refs.lastNames.value, warnings, "Last names");
  const family = normalizedField(refs.familyNames.value, warnings, "Family names");
  const pets = normalizedField(refs.petNames.value, warnings, "Pet names");
  const locations = normalizedField(refs.location.value, warnings, "Locations");
  const interests = normalizedField(refs.interests.value, warnings, "Interests");
  const phoneNumbers = normalizePhoneList(refs.phoneNumbers.value, warnings);
  const exactDob = normalizeDobList(refs.exactDob.value, warnings);

  const includeRandomNumbers = refs.includeRandomNumbers.checked;
  const randomCountRaw = Number(refs.randomCount.value);
  const randomCount = includeRandomNumbers
    ? clampNumber(Number.isFinite(randomCountRaw) ? Math.trunc(randomCountRaw) : 48, 0, MAX_RANDOM_COUNT)
    : 0;

  if (includeRandomNumbers && randomCount !== randomCountRaw) {
    warnings.push(`Random numeric count was adjusted to stay in the allowed range (0-${MAX_RANDOM_COUNT}).`);
  }

  const sizeInfo = sanitizeSize(refs.listSizeInput.value);
  if (sizeInfo.requestedRaw !== Number(refs.listSizeInput.value)) {
    warnings.push(`Invalid size input detected; defaulted to ${DEFAULT_LIST_SIZE}.`);
  }

  return {
    owners,
    lastNames,
    family,
    pets,
    phoneNumbers,
    locations,
    interests,
    exactDob,
    desiredSize: sizeInfo.requestedRaw,
    includeRouterDefaults: refs.includeRouterDefaults.checked,
    includeYears: refs.includeYears.checked,
    includeLeet: refs.includeLeet.checked,
    includeRandomNumbers,
    randomCount,
    warnings
  };
}

function handleGenerate() {
  const input = collectInput();
  if (typeof Worker !== "undefined") {
    runWorkerGeneration(input);
    return;
  }

  runInlineGeneration(input);
}

function runInlineGeneration(input) {
  setBusyState(refs, { isBusy: true, canCancel: false });
  setProgress(refs, "Generating wordlist...");

  try {
    const result = generateWordlist(input);
    result.warnings = [...input.warnings, ...result.warnings];
    updateOutputUI(result, refs);
  } finally {
    setBusyState(refs, { isBusy: false, canCancel: false });
  }
}

function runWorkerGeneration(input) {
  if (activeWorker) {
    activeWorker.terminate();
    activeWorker = null;
  }

  setBusyState(refs, { isBusy: true, canCancel: true });
  refs.output.value = "";
  refs.downloadBtn.disabled = true;
  setProgress(refs, "Large generation detected. Worker started...");

  const worker = new Worker(new URL("./worker.js", import.meta.url), { type: "module" });
  activeWorker = worker;

  let streamedPasswords = [];
  let initialWarnings = [...input.warnings];
  let totalPasswords = 0;

  const formatPercent = (done, total) => {
    if (!total) return 0;
    return Math.min(100, Math.round((done / total) * 100));
  };

  worker.onmessage = (event) => {
    const { type, payload } = event.data || {};

    if (type === "progress") {
      const pct = Number.isFinite(payload.percent) ? Math.round(payload.percent) : null;
      setProgress(refs, pct === null ? payload.message : `${payload.message} (${pct}%)`);
      return;
    }

    if (type === "meta") {
      totalPasswords = Number(payload.totalPasswords) || 0;
      setProgress(refs, totalPasswords > 0
        ? `Preparing stream... 70% (0/${totalPasswords})`
        : "Preparing stream... 70%");
      return;
    }

    if (type === "chunk") {
      streamedPasswords = streamedPasswords.concat(payload.passwords);
      refs.output.value = streamedPasswords.join("\n");
      const basePercent = 70;
      const streamPercent = totalPasswords > 0 ? formatPercent(streamedPasswords.length, totalPasswords) : 0;
      const overallPercent = totalPasswords > 0
        ? Math.min(100, Math.round(basePercent + ((streamPercent / 100) * 30)))
        : null;
      if (overallPercent === null) {
        setProgress(refs, `Streaming results... ${streamedPasswords.length} passwords ready`);
      } else {
        setProgress(refs, `Streaming results... ${overallPercent}% (${streamedPasswords.length}/${totalPasswords})`);
      }
      return;
    }

    if (type === "done") {
      const result = {
        ...payload.result,
        passwords: streamedPasswords,
        warnings: [...initialWarnings, ...(payload.result.warnings || [])]
      };

      setProgress(refs, "Generation complete (100%)");
      updateOutputUI(result, refs);
      setBusyState(refs, { isBusy: false, canCancel: false });
      worker.terminate();
      activeWorker = null;
      return;
    }

    if (type === "error") {
      setProgress(refs, `Worker failed: ${payload.message}. Falling back to inline mode.`);
      worker.terminate();
      activeWorker = null;
      runInlineGeneration(input);
    }
  };

  worker.onerror = () => {
    setProgress(refs, "Worker crashed. Falling back to inline generation.");
    worker.terminate();
    activeWorker = null;
    runInlineGeneration(input);
  };

  worker.postMessage({ type: "generate", payload: input });
}

refs.generateBtn.addEventListener("click", handleGenerate);
refs.cancelBtn.addEventListener("click", () => {
  if (!activeWorker) return;
  activeWorker.terminate();
  activeWorker = null;
  setProgress(refs, "Generation canceled by user.");
  setBusyState(refs, { isBusy: false, canCancel: false });
});
if (refs.downloadBtn) {
  refs.downloadBtn.addEventListener("click", () => downloadWordlist(refs.output.value));
}
refs.outputDownloadBtn.addEventListener("click", () => downloadWordlist(refs.output.value));

if (refs.closeCommonListsBtn && refs.commonListsPopup) {
  refs.closeCommonListsBtn.addEventListener("click", () => {
    refs.commonListsPopup.classList.add("hidden");
  });
}

window.addEventListener("load", () => {
  handleGenerate();
});
