import { mountToolScenePreset } from "/static/tool-scene-presets.js";

document.querySelectorAll("[data-tool-scene]").forEach((canvas) => {
  const name = canvas.dataset.toolScene;
  if (!name) return;
  mountToolScenePreset(name, { canvasId: canvas.id });
});
