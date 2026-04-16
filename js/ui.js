import { HARD_LIMIT } from "./constants.js";

export function setBusyState(refs, isBusy) {
  const state = typeof isBusy === "object"
    ? isBusy
    : { isBusy: Boolean(isBusy), canCancel: false };

  refs.generateBtn.disabled = state.isBusy;
  refs.cancelBtn.disabled = !state.canCancel;
  refs.downloadBtn.disabled = state.isBusy || !refs.output.value;
  refs.outputDownloadBtn.disabled = state.isBusy || !refs.output.value;
}

export function setProgress(refs, message) {
  refs.stats.textContent = message;
}

export function updateOutputUI(result, refs) {
  const {
    output,
    stats,
    warnings,
    downloadBtn,
    listSizeInput
  } = refs;

  output.value = result.passwords.join("\n");
  downloadBtn.disabled = result.passwords.length === 0;
  refs.outputDownloadBtn.disabled = result.passwords.length === 0;

  listSizeInput.max = String(HARD_LIMIT);
  if (Number(listSizeInput.value) > HARD_LIMIT) {
    listSizeInput.value = String(HARD_LIMIT);
  }

  let message = `Generated ${result.generatedCount} passwords. `;
  message += `Actual unique candidate patterns available: ${result.totalUnique}. `;

  if (result.clippedByLimit) {
    message += `Requested size exceeded hard limit (${result.hardLimit}); output clipped to ${result.hardLimit}. `;
  }

  if (result.clippedByCandidates) {
    message += `Requested size exceeded available candidate count; output clipped to ${result.totalUnique}. `;
  }

  if (!result.clippedByLimit && !result.clippedByCandidates) {
    message += `Output matches requested size.`;
  }

  stats.textContent = message.trim();

  warnings.innerHTML = "";
  const allWarnings = result.warnings || [];
  if (!allWarnings.length) {
    warnings.textContent = "No input warnings. Generation completed successfully.";
    return;
  }

  const list = document.createElement("ul");
  list.className = "warning-list";
  allWarnings.forEach((entry) => {
    const item = document.createElement("li");
    item.textContent = entry;
    list.appendChild(item);
  });
  warnings.appendChild(list);
}

export function downloadWordlist(text) {
  if (!text) return;

  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "target.txt";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
