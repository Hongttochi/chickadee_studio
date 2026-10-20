const { contextBridge, ipcRenderer } = require("electron");
async function invoke(channel, ...args) {
  try {
    return await ipcRenderer.invoke(channel, ...args);
  } catch (error) {
    throw new Error(
      error.message.replace(
        /^Error invoking remote method '[^']+': (?:Error: )?/,
        "",
      ),
    );
  }
}
contextBridge.exposeInMainWorld(
  "chickadee",
  Object.freeze({
    state: () => invoke("desktop:state"),
    start: (options) => invoke("desktop:start", options),
    stop: () => invoke("desktop:stop"),
    pause: () => invoke("desktop:pause"),
    resume: () => invoke("desktop:resume"),
    capabilities: () => invoke("desktop:capabilities"),
    preferences: (value) => invoke("desktop:preferences", value),
    review: (value) => invoke("desktop:review", value),
    load: () => invoke("desktop:load"),
    history: (id) => invoke("desktop:history", id),
    exportCSV: () => invoke("desktop:export"),
    chooseFolder: () => invoke("desktop:choose-folder"),
    openFolder: () => invoke("desktop:open-folder"),
    saveWorkflow: (value) => invoke("desktop:save-workflow", value),
    exportWorkflow: (value) => invoke("desktop:export-workflow", value),
    loadWorkflow: () => invoke("desktop:load-workflow"),
    copy: (text) => invoke("desktop:copy", text),
    onEvent: (callback) => {
      const listener = (_event, value) => callback(value);
      ipcRenderer.on("desktop:event", listener);
      return () => ipcRenderer.removeListener("desktop:event", listener);
    },
  }),
);
