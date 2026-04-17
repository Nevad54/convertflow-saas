import * as THREE from "https://unpkg.com/three@0.160.0/build/three.module.js";

export { THREE };

export function createGlowSprite({
  inner = "rgba(232,168,56,0.24)",
  middle = "rgba(212,74,26,0.1)",
  outer = "rgba(0,0,0,0)",
  scale = 12
} = {}) {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 256;
  const ctx = canvas.getContext("2d");
  const gradient = ctx.createRadialGradient(128, 128, 0, 128, 128, 128);
  gradient.addColorStop(0, inner);
  gradient.addColorStop(0.34, middle);
  gradient.addColorStop(1, outer);
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 256, 256);
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
    map: new THREE.CanvasTexture(canvas),
    transparent: true,
    blending: THREE.AdditiveBlending
  }));
  sprite.scale.set(scale, scale, 1);
  return sprite;
}

export function bindPulseSelectors(selectors, pulse, value = 0.3) {
  document.querySelectorAll(selectors).forEach((node) => {
    node.addEventListener("pointerenter", () => pulse(value));
    node.addEventListener("focus", () => pulse(Math.max(0.18, value - 0.06)), true);
  });
}

export function bindFocusSelectors(selectors, setFocus, value = 0.16, resetFocus) {
  document.querySelectorAll(selectors).forEach((node) => {
    node.addEventListener("pointerenter", () => setFocus(value));
    node.addEventListener("pointerleave", () => resetFocus?.());
    node.addEventListener("focus", () => setFocus(value), true);
    node.addEventListener("blur", () => resetFocus?.(), true);
  });
}

export function bindClickPulse(selectors, pulse, value = 0.4) {
  document.addEventListener("click", (event) => {
    if (event.target.closest(selectors)) {
      pulse(value);
    }
  });
}

export function observeSectionDepth({
  sections,
  state,
  pulse,
  setFocus,
  thresholds = [0.2, 0.45, 0.7],
  activeRatio = 0.45,
  pulseBase = 0.12,
  pulseStep = 0.035,
  focusBase = 0.1,
  focusStep = 0.02,
  focusCap = 0.22
}) {
  if (!sections?.length || !("IntersectionObserver" in window)) {
    return null;
  }

  const observer = new IntersectionObserver((entries) => {
    let strongest = 0;
    let depth = 0;
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const sectionDepth = sections.indexOf(entry.target);
      if (entry.intersectionRatio >= strongest) {
        strongest = entry.intersectionRatio;
        depth = sectionDepth;
      }
    });
    state.targetScrollDepth = depth;
    if (strongest > activeRatio) {
      pulse(pulseBase + depth * pulseStep);
      setFocus(Math.min(focusBase + depth * focusStep, focusCap));
    }
  }, { threshold: thresholds });

  sections.forEach((section) => observer.observe(section));
  return observer;
}

export function bindScrollDepth(state, maxDepth = 5) {
  window.addEventListener("scroll", () => {
    const maxScroll = Math.max(document.documentElement.scrollHeight - window.innerHeight, 1);
    const progress = Math.min(window.scrollY / maxScroll, 1);
    state.targetScrollDepth = progress * maxDepth;
  }, { passive: true });
}

export function bindToolSceneInteractions(
  { pulse, state },
  {
    primarySelectors = ".action-strip button",
    uploadSelectors = ".upload--drop",
    fieldSelectors = ".field input, .field select, .field textarea",
    accentSelectors = ".tool-tip-pills span",
    primaryPulse = 0.4,
    uploadPulse = 0.34,
    fieldPulse = 0.2,
    accentPulse = 0.24
  } = {}
) {
  if (primarySelectors) {
    bindPulseSelectors(primarySelectors, pulse, primaryPulse);
    bindClickPulse(primarySelectors, pulse, Math.max(primaryPulse + 0.12, 0.52));
  }

  if (uploadSelectors) {
    bindPulseSelectors(uploadSelectors, pulse, uploadPulse);
    bindClickPulse(uploadSelectors, pulse, Math.max(uploadPulse + 0.1, 0.44));
    document.querySelectorAll(uploadSelectors).forEach((node) => {
      node.addEventListener("dragenter", () => {
        state.targetDrag = 1;
        pulse(Math.max(uploadPulse + 0.12, 0.48));
      });
      node.addEventListener("dragover", () => {
        state.targetDrag = 1;
      });
      node.addEventListener("dragleave", () => {
        state.targetDrag = 0;
      });
      node.addEventListener("drop", () => {
        state.targetDrag = 0;
        pulse(Math.max(uploadPulse + 0.14, 0.5));
      });
    });
  }

  if (fieldSelectors) {
    bindPulseSelectors(fieldSelectors, pulse, fieldPulse);
  }

  if (accentSelectors) {
    bindPulseSelectors(accentSelectors, pulse, accentPulse);
  }

  document.addEventListener("convertflow:tool-files-selected", (event) => {
    const count = Math.max(1, Number(event.detail?.count || 0));
    state.targetFocus = Math.max(state.targetFocus, 0.14);
    pulse(Math.min(0.24 + count * 0.06, 0.58));
  });

  document.addEventListener("convertflow:tool-submit", () => {
    state.targetFocus = Math.max(state.targetFocus, 0.22);
    pulse(0.62);
  });

  document.addEventListener("convertflow:tool-success", () => {
    state.targetFocus = Math.max(state.targetFocus, 0.18);
    state.targetSuccess = 1;
    state.targetError = 0;
    pulse(0.74);
  });

  document.addEventListener("convertflow:tool-error", () => {
    state.targetFocus = Math.max(state.targetFocus, 0.16);
    state.targetError = 1;
    state.targetSuccess = 0;
    pulse(0.52);
  });
}

export function mountScene({
  canvasId,
  pulseSelectors = "",
  pulseValue = 0.3,
  camera: cameraConfig = {},
  setup,
  frame
}) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return null;
  }

  try {
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.8));
    renderer.setSize(window.innerWidth, window.innerHeight);

    const scene = new THREE.Scene();
    const {
      fov = 44,
      near = 0.1,
      far = 100,
      position = [0, 0, 18]
    } = cameraConfig;
    const camera = new THREE.PerspectiveCamera(fov, window.innerWidth / window.innerHeight, near, far);
    camera.position.set(...position);

    const pointer = { x: 0, y: 0, tx: 0, ty: 0 };
    const state = {
      energy: 0,
      targetEnergy: 0,
      focus: 0,
      targetFocus: 0,
      drag: 0,
      targetDrag: 0,
      success: 0,
      targetSuccess: 0,
      error: 0,
      targetError: 0,
      scrollDepth: 0,
      targetScrollDepth: 0
    };

    window.addEventListener("mousemove", (event) => {
      pointer.tx = (event.clientX / window.innerWidth - 0.5) * 2;
      pointer.ty = (event.clientY / window.innerHeight - 0.5) * 2;
    }, { passive: true });

    function pulse(value) {
      state.targetEnergy = Math.max(state.targetEnergy, value);
    }

    if (pulseSelectors) {
      bindPulseSelectors(pulseSelectors, pulse, pulseValue);
    }

    const ctx = { THREE, canvas, renderer, scene, camera, pointer, state, pulse, data: {} };
    if (typeof setup === "function") {
      setup(ctx);
    }

    const clock = new THREE.Clock();
    function animate() {
      const elapsed = clock.getElapsedTime();
      pointer.x += (pointer.tx - pointer.x) * 0.05;
      pointer.y += (pointer.ty - pointer.y) * 0.05;
      state.targetEnergy *= 0.986;
      state.energy += (state.targetEnergy - state.energy) * 0.08;
      state.focus += (state.targetFocus - state.focus) * 0.08;
      state.drag += (state.targetDrag - state.drag) * 0.12;
      state.success += (state.targetSuccess - state.success) * 0.12;
      state.error += (state.targetError - state.error) * 0.14;
      state.targetDrag *= 0.94;
      state.targetSuccess *= 0.93;
      state.targetError *= 0.9;
      if (typeof frame === "function") {
        frame(ctx, elapsed);
      }
      renderer.render(scene, camera);
      window.requestAnimationFrame(animate);
    }

    animate();

    window.addEventListener("resize", () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    });

    return ctx;
  } catch (error) {
    console.error(`Scene failed to initialize for ${canvasId}.`, error);
    canvas.remove();
    return null;
  }
}

export function mountToolScene(options) {
  const {
    setup,
    toolUi = {},
    pulseSelectors = ".action-strip button, .upload--drop, .tool-tip-pills span",
    pulseValue = 0.3,
    ...rest
  } = options;

  return mountScene({
    ...rest,
    pulseSelectors,
    pulseValue,
    setup(ctx) {
      bindToolSceneInteractions(ctx, toolUi);
      setup?.(ctx);
    }
  });
}
