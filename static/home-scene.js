import { THREE } from "/static/tool-scene.js";

const canvas = document.getElementById("scene3d");

if (canvas && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  try {
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 200);
    camera.position.set(0, 0, 24);

    const homeSceneState = window.homeSceneState || {
      converting: false,
      dragging: false,
      boost: 0
    };
    window.homeSceneState = homeSceneState;

    let scrollTarget = 0;
    let scrollCurrent = 0;
    window.addEventListener("scroll", () => {
      scrollTarget = window.scrollY;
    }, { passive: true });

    const mouse = { x: 0, y: 0, tx: 0, ty: 0 };
    window.addEventListener("mousemove", (event) => {
      mouse.tx = (event.clientX / window.innerWidth - 0.5) * 2;
      mouse.ty = (event.clientY / window.innerHeight - 0.5) * 2;
    }, { passive: true });

    function pulse(value = 0.6) {
      homeSceneState.boost = Math.max(homeSceneState.boost, value);
    }

    function bindPulse(selectors, value) {
      document.querySelectorAll(selectors).forEach((node) => {
        node.addEventListener("pointerenter", () => pulse(value));
        node.addEventListener("focus", () => pulse(Math.max(0.2, value - 0.08)), true);
        node.addEventListener("click", () => pulse(Math.min(value + 0.16, 0.95)));
      });
    }

    bindPulse(".hero-actions__primary", 0.56);
    bindPulse(".hero-actions__secondary", 0.28);
    bindPulse(".hero-stage-panel__routes a, .launch-route, .spotlight-card", 0.34);
    bindPulse(".filter-chip, .recent-tools__clear", 0.24);

    const toolSearch = document.getElementById("tool-search");
    if (toolSearch) {
      toolSearch.addEventListener("focus", () => pulse(0.4));
      toolSearch.addEventListener("input", () => pulse(0.18 + Math.min(toolSearch.value.length, 10) * 0.03));
    }

    const reactiveSections = Array.from(document.querySelectorAll(
      ".hero--home, .launch-panel, .spotlight, .tool-browser, .recent-tools, .favorites-tools, .activity-board, .saved-batches"
    ));

    if ("IntersectionObserver" in window && reactiveSections.length) {
      const observer = new IntersectionObserver((entries) => {
        let strongest = 0;
        let activeIndex = 0;
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          if (entry.intersectionRatio >= strongest) {
            strongest = entry.intersectionRatio;
            activeIndex = reactiveSections.indexOf(entry.target);
          }
        });
        if (strongest > 0.35) {
          pulse(0.12 + activeIndex * 0.05);
        }
      }, { threshold: [0.2, 0.45, 0.7] });

      reactiveSections.forEach((section) => observer.observe(section));
    }

    const cubeGroup = new THREE.Group();
    scene.add(cubeGroup);

    const GRID = 3;
    const GAP = 2.0;
    const BASE_SIZE = 0.85;
    const cubeData = [];

    const srcColor = new THREE.Color(0xe8a838);
    const tgtColor = new THREE.Color(0x2dd4a8);
    const dimSrc = new THREE.Color(0x3d2a0a);
    const dimTgt = new THREE.Color(0x0a2d22);

    for (let ix = 0; ix < GRID; ix++) {
      for (let iy = 0; iy < GRID; iy++) {
        for (let iz = 0; iz < GRID; iz++) {
          const gx = (ix - 1) * GAP;
          const gy = (iy - 1) * GAP;
          const gz = (iz - 1) * GAP;

          const jx = gx + (Math.random() - 0.5) * 0.3;
          const jy = gy + (Math.random() - 0.5) * 0.3;
          const jz = gz + (Math.random() - 0.5) * 0.3;
          const size = BASE_SIZE + (Math.random() - 0.5) * 0.25;

          const isSrc = ix < 2;
          const mainColor = isSrc ? srcColor : tgtColor;
          const dimColor = isSrc ? dimSrc : dimTgt;

          const dist = Math.sqrt(jx * jx + jy * jy + jz * jz);
          const bright = 1 - (dist / 4.5) * 0.6;

          const geometry = new THREE.BoxGeometry(size, size, size);
          const fillMat = new THREE.MeshBasicMaterial({
            color: dimColor.clone().lerp(mainColor, bright * 0.3),
            transparent: true,
            opacity: 0.05 + bright * 0.03
          });
          const fillMesh = new THREE.Mesh(geometry, fillMat);

          const wireMat = new THREE.MeshBasicMaterial({
            color: mainColor.clone().lerp(dimColor, 1 - bright),
            wireframe: true,
            transparent: true,
            opacity: 0.12 + bright * 0.18
          });
          const wireMesh = new THREE.Mesh(geometry.clone(), wireMat);
          wireMesh.scale.setScalar(1.03);

          const edges = new THREE.EdgesGeometry(geometry);
          const edgeMat = new THREE.LineBasicMaterial({
            color: mainColor,
            transparent: true,
            opacity: bright * 0.35
          });
          const edgeLines = new THREE.LineSegments(edges, edgeMat);

          const cube = new THREE.Group();
          cube.position.set(jx, jy, jz);
          cube.add(fillMesh, wireMesh, edgeLines);
          cubeGroup.add(cube);

          cubeData.push({
            obj: cube,
            wireMat,
            edgeMat,
            basePos: new THREE.Vector3(jx, jy, jz),
            rx: (Math.random() - 0.5) * 0.4,
            ry: (Math.random() - 0.5) * 0.6,
            rz: (Math.random() - 0.5) * 0.3,
            phase: Math.random() * Math.PI * 2,
            floatSpd: 0.3 + Math.random() * 0.4,
            floatAmp: 0.08 + Math.random() * 0.12
          });
        }
      }
    }

    const maxConnections = cubeData.length * 6;
    const connPos = new Float32Array(maxConnections * 6);
    const connGeo = new THREE.BufferGeometry();
    connGeo.setAttribute("position", new THREE.BufferAttribute(connPos, 3));
    const connMat = new THREE.LineBasicMaterial({
      color: 0xe8a838,
      transparent: true,
      opacity: 0.035
    });
    const connLines = new THREE.LineSegments(connGeo, connMat);
    scene.add(connLines);

    function updateConnections() {
      let idx = 0;
      const positions = connLines.geometry.attributes.position.array;
      for (let i = 0; i < cubeData.length && idx < maxConnections; i++) {
        for (let j = i + 1; j < cubeData.length && idx < maxConnections; j++) {
          const distance = cubeData[i].obj.position.distanceTo(cubeData[j].obj.position);
          if (distance < GAP * 1.3) {
            const a = cubeData[i].obj.position;
            const b = cubeData[j].obj.position;
            positions[idx * 6] = a.x;
            positions[idx * 6 + 1] = a.y;
            positions[idx * 6 + 2] = a.z;
            positions[idx * 6 + 3] = b.x;
            positions[idx * 6 + 4] = b.y;
            positions[idx * 6 + 5] = b.z;
            idx++;
          }
        }
      }
      for (let k = idx * 6; k < positions.length; k++) {
        positions[k] = 0;
      }
      connLines.geometry.attributes.position.needsUpdate = true;
      connLines.geometry.setDrawRange(0, idx * 2);
    }

    const dustVert = `
      attribute float aSize;
      varying vec3 vColor;
      void main() {
        vColor = color;
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        gl_PointSize = aSize * (150.0 / max(-mv.z, 0.5));
        gl_Position = projectionMatrix * mv;
      }
    `;
    const dustFrag = `
      varying vec3 vColor;
      void main() {
        float d = length(gl_PointCoord - vec2(0.5));
        if (d > 0.5) discard;
        float a = smoothstep(0.5, 0.02, d) * 0.4;
        gl_FragColor = vec4(vColor, a);
      }
    `;

    const dustCount = 400;
    const dP = new Float32Array(dustCount * 3);
    const dC = new Float32Array(dustCount * 3);
    const dS = new Float32Array(dustCount);
    const amberDust = new THREE.Color(0xe8a838);
    const tealDust = new THREE.Color(0x2dd4a8);
    const dimDust = new THREE.Color(0x2a2a30);

    for (let i = 0; i < dustCount; i++) {
      dP[i * 3] = (Math.random() - 0.5) * 80;
      dP[i * 3 + 1] = (Math.random() - 0.5) * 80;
      dP[i * 3 + 2] = (Math.random() - 0.5) * 60 - 10;
      const roll = Math.random();
      const color = roll < 0.12 ? amberDust : roll < 0.22 ? tealDust : dimDust;
      dC[i * 3] = color.r;
      dC[i * 3 + 1] = color.g;
      dC[i * 3 + 2] = color.b;
      dS[i] = Math.random() * 1.6 + 0.3;
    }

    const dustGeo = new THREE.BufferGeometry();
    dustGeo.setAttribute("position", new THREE.BufferAttribute(dP, 3));
    dustGeo.setAttribute("color", new THREE.BufferAttribute(dC, 3));
    dustGeo.setAttribute("aSize", new THREE.BufferAttribute(dS, 1));

    const dust = new THREE.Points(dustGeo, new THREE.ShaderMaterial({
      vertexShader: dustVert,
      fragmentShader: dustFrag,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      vertexColors: true
    }));
    scene.add(dust);

    function makeGlow(size, x, y, z, stops) {
      const glowCanvas = document.createElement("canvas");
      glowCanvas.width = 256;
      glowCanvas.height = 256;
      const ctx = glowCanvas.getContext("2d");
      const gradient = ctx.createRadialGradient(128, 128, 0, 128, 128, 128);
      stops.forEach(([offset, color]) => gradient.addColorStop(offset, color));
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, 256, 256);
      const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
        map: new THREE.CanvasTexture(glowCanvas),
        transparent: true,
        blending: THREE.AdditiveBlending
      }));
      sprite.scale.set(size, size, 1);
      sprite.position.set(x, y, z);
      scene.add(sprite);
      return sprite;
    }

    const glowSrc = makeGlow(14, -2, 0, -3, [
      [0, "rgba(232,168,56,0.2)"],
      [0.3, "rgba(212,74,26,0.06)"],
      [1, "rgba(0,0,0,0)"]
    ]);
    const glowTgt = makeGlow(14, 2, 0, -3, [
      [0, "rgba(45,212,168,0.15)"],
      [0.3, "rgba(20,120,90,0.04)"],
      [1, "rgba(0,0,0,0)"]
    ]);
    const glowCenter = makeGlow(10, 0, 0, -2, [
      [0, "rgba(200,180,120,0.12)"],
      [0.4, "rgba(140,100,60,0.03)"],
      [1, "rgba(0,0,0,0)"]
    ]);

    const clock = new THREE.Clock();
    let autoAngle = 0;

    function animate() {
      requestAnimationFrame(animate);

      const elapsed = clock.getElapsedTime();
      const dt = Math.min(clock.getDelta(), 0.05);

      scrollCurrent += (scrollTarget - scrollCurrent) * 0.06;
      mouse.x += (mouse.tx - mouse.x) * 0.04;
      mouse.y += (mouse.ty - mouse.y) * 0.04;

      homeSceneState.boost *= 0.95;
      const speedMul = (
        homeSceneState.converting ? 3.5 :
        homeSceneState.dragging ? 1.8 :
        1.0
      ) + homeSceneState.boost * 1.35;

      autoAngle += 0.15 * dt * speedMul;

      const scrollRotY = scrollCurrent * 0.004;
      const scrollRotX = scrollCurrent * 0.0015;

      cubeGroup.rotation.y = autoAngle + scrollRotY + mouse.x * 0.15;
      cubeGroup.rotation.x = Math.sin(autoAngle * 0.4) * 0.2 + scrollRotX - mouse.y * 0.1;
      cubeGroup.rotation.z = Math.sin(autoAngle * 0.25) * 0.08;

      cubeData.forEach((cube) => {
        const fy = Math.sin(elapsed * cube.floatSpd + cube.phase) * cube.floatAmp;
        const fx = Math.cos(elapsed * cube.floatSpd * 0.7 + cube.phase * 1.3) * cube.floatAmp * 0.5;
        cube.obj.position.set(cube.basePos.x + fx, cube.basePos.y + fy, cube.basePos.z);
        cube.obj.rotation.x += cube.rx * dt * speedMul;
        cube.obj.rotation.y += cube.ry * dt * speedMul;
        cube.obj.rotation.z += cube.rz * dt * speedMul;

        const targetWireOpacity = homeSceneState.converting ? 0.35 : 0.18 + homeSceneState.boost * 0.1;
        cube.wireMat.opacity += (targetWireOpacity - cube.wireMat.opacity) * 0.03;
        const targetEdgeOpacity = homeSceneState.converting ? 0.6 : 0.25 + homeSceneState.boost * 0.12;
        cube.edgeMat.opacity += (targetEdgeOpacity - cube.edgeMat.opacity) * 0.03;
      });

      updateConnections();

      camera.position.x = mouse.x * 1.2;
      camera.position.y = -mouse.y * 0.8;
      camera.lookAt(0, 0, 0);

      const glowPulse = homeSceneState.converting ? 1.5 : 1 + homeSceneState.boost * 0.4;
      const sourceScale = 14 + Math.sin(elapsed * 1.5) * 0.6;
      glowSrc.scale.set(sourceScale * glowPulse, sourceScale * glowPulse, 1);
      glowTgt.scale.set(sourceScale * glowPulse, sourceScale * glowPulse, 1);

      const centerScale = 10 + Math.sin(elapsed * 2) * 0.5 + (homeSceneState.converting ? 4 : homeSceneState.boost * 2.5);
      glowCenter.scale.set(centerScale, centerScale, 1);

      dust.rotation.y = elapsed * 0.008;
      dust.rotation.x = Math.sin(elapsed * 0.005) * 0.05;

      renderer.render(scene, camera);
    }

    animate();

    window.addEventListener("resize", () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    });
  } catch (error) {
    console.error("Homepage 3D scene failed to initialize.", error);
    canvas.remove();
  }
}
