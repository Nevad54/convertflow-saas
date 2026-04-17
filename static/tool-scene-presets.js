import { THREE, createGlowSprite, mountToolScene } from "/static/tool-scene.js";

const scenePresets = {
  ocr: {
    canvasId: "ocr-scene",
    pulseSelectors: ".action-strip button, .field select, .upload--drop, .tool-tip-pills span",
    pulseValue: 0.34,
    setup({ scene, data }) {
      const geometry = new THREE.IcosahedronGeometry(3.1, 3);
      const material = new THREE.MeshBasicMaterial({
        color: 0xe8a838,
        wireframe: true,
        transparent: true,
        opacity: 0.18
      });

      const orb = new THREE.Mesh(geometry, material);
      orb.position.set(4.8, 2.6, -7);
      scene.add(orb);

      const glow = createGlowSprite({
        inner: "rgba(232,168,56,0.28)",
        middle: "rgba(212,74,26,0.1)",
        scale: 12
      });
      glow.position.copy(orb.position);
      scene.add(glow);

      const ringGroup = new THREE.Group();
      ringGroup.position.copy(orb.position);
      scene.add(ringGroup);

      const ringMaterial = new THREE.LineBasicMaterial({
        color: 0xf0c060,
        transparent: true,
        opacity: 0.16
      });
      [4.2, 5.5, 6.8].forEach((radius, index) => {
        const points = [];
        for (let i = 0; i <= 96; i++) {
          const angle = (i / 96) * Math.PI * 2;
          points.push(new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, 0));
        }
        const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), ringMaterial.clone());
        line.rotation.x = 1.1 - index * 0.38;
        line.rotation.y = index * 0.45;
        ringGroup.add(line);
      });

      const particleCount = 140;
      const particlePositions = new Float32Array(particleCount * 3);
      for (let i = 0; i < particleCount; i++) {
        const angle = Math.random() * Math.PI * 2;
        const radius = 4.5 + Math.random() * 3;
        particlePositions[i * 3] = Math.cos(angle) * radius;
        particlePositions[i * 3 + 1] = (Math.random() - 0.5) * 3.5;
        particlePositions[i * 3 + 2] = Math.sin(angle) * radius;
      }
      const particles = new THREE.Points(
        new THREE.BufferGeometry().setAttribute("position", new THREE.BufferAttribute(particlePositions, 3)),
        new THREE.PointsMaterial({
          color: 0xe8a838,
          size: 0.08,
          transparent: true,
          opacity: 0.45,
          blending: THREE.AdditiveBlending,
          depthWrite: false
        })
      );
      particles.position.copy(orb.position);
      scene.add(particles);

      Object.assign(data, { orb, glow, ringGroup, particles });
    },
    frame({ camera, pointer, state, data }, elapsed) {
      const { orb, glow, ringGroup, particles } = data;
      if (!orb || !glow || !ringGroup || !particles) return;
      camera.position.x = pointer.x * 0.45;
      camera.position.y = -pointer.y * 0.35;
      camera.lookAt(0, 0, -4);
      const successBoost = state.success * 0.28;
      const errorTension = state.error * 0.18;
      orb.rotation.x += 0.002 + state.energy * 0.004 + successBoost * 0.01;
      orb.rotation.y += 0.003 + state.energy * 0.005 + successBoost * 0.014;
      orb.position.y = 2.6 + Math.sin(elapsed * 0.8) * 0.18;
      glow.position.copy(orb.position);
      glow.scale.setScalar(12 + state.energy * 1.8 + successBoost * 2.1 + Math.sin(elapsed * 1.2) * 0.2 - errorTension * 0.35);
      glow.material.opacity = 0.4 + state.energy * 0.22 + successBoost * 0.18 - errorTension * 0.08;
      ringGroup.position.copy(orb.position);
      ringGroup.rotation.z += 0.0015 + state.energy * 0.002 + successBoost * 0.004 + errorTension * 0.003;
      ringGroup.rotation.x = Math.sin(elapsed * 0.55) * 0.03 + errorTension * 0.06;
      particles.position.copy(orb.position);
      particles.rotation.y += 0.0012 + state.energy * 0.003 + successBoost * 0.006;
      particles.material.opacity = 0.45 + successBoost * 0.18 - errorTension * 0.1;
    }
  },
  "pdf-word": {
    canvasId: "pdf-word-scene",
    pulseSelectors: ".action-strip button, .upload--drop, .tool-tip-pills span",
    pulseValue: 0.32,
    setup({ scene, data }) {
      const pageGroup = new THREE.Group();
      pageGroup.position.set(4.8, 2.2, -6.5);
      scene.add(pageGroup);

      function makeSheet(offsetX, offsetY, color, opacity) {
        const mesh = new THREE.Mesh(
          new THREE.PlaneGeometry(4.2, 5.5),
          new THREE.MeshBasicMaterial({ color, transparent: true, opacity, side: THREE.DoubleSide })
        );
        mesh.position.set(offsetX, offsetY, 0);
        mesh.rotation.z = -0.08 + offsetX * 0.04;
        return mesh;
      }

      pageGroup.add(makeSheet(-0.5, 0.25, 0xa24b2a, 0.1));
      pageGroup.add(makeSheet(0, 0, 0xf0ece4, 0.16));
      pageGroup.add(makeSheet(0.55, -0.22, 0x2b5eb8, 0.12));

      const lineMaterial = new THREE.LineBasicMaterial({ color: 0xe8a838, transparent: true, opacity: 0.18 });
      for (let i = 0; i < 3; i++) {
        const points = [];
        for (let y = 2; y >= -2; y -= 0.65) {
          points.push(new THREE.Vector3(-1.35 + i * 0.2, y, 0.02));
          points.push(new THREE.Vector3(1.2 + i * 0.15, y, 0.02));
        }
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const lines = new THREE.LineSegments(geometry, lineMaterial.clone());
        lines.position.z = 0.08 + i * 0.02;
        pageGroup.add(lines);
      }

      const ring = new THREE.LineLoop(
        new THREE.BufferGeometry().setFromPoints(
          Array.from({ length: 80 }, (_, i) => {
            const angle = (i / 80) * Math.PI * 2;
            return new THREE.Vector3(Math.cos(angle) * 4.8, Math.sin(angle) * 3.6, 0);
          })
        ),
        new THREE.LineBasicMaterial({ color: 0xf0c060, transparent: true, opacity: 0.14 })
      );
      ring.position.copy(pageGroup.position);
      ring.rotation.x = 1.05;
      scene.add(ring);

      const glow = createGlowSprite({
        inner: "rgba(59,130,246,0.18)",
        middle: "rgba(232,168,56,0.12)",
        scale: 11
      });
      glow.position.copy(pageGroup.position);
      scene.add(glow);
      Object.assign(data, { pageGroup, ring, glow });
    },
    frame({ camera, pointer, state, data }, elapsed) {
      const { pageGroup, ring, glow } = data;
      if (!pageGroup || !ring || !glow) return;
      const successBoost = state.success * 0.26;
      const errorTension = state.error * 0.16;
      camera.position.x = pointer.x * 0.35;
      camera.position.y = -pointer.y * 0.28;
      camera.lookAt(0, 0, -3);
      pageGroup.rotation.y = Math.sin(elapsed * 0.4) * 0.08 + state.energy * 0.08 + successBoost * 0.08;
      pageGroup.rotation.x = Math.cos(elapsed * 0.35) * 0.04 + errorTension * 0.03;
      pageGroup.position.y = 2.2 + Math.sin(elapsed * 0.8) * 0.12;
      ring.position.copy(pageGroup.position);
      ring.rotation.z += 0.002 + state.energy * 0.004 + successBoost * 0.004 + errorTension * 0.003;
      glow.position.copy(pageGroup.position);
      glow.material.opacity = 0.38 + state.energy * 0.2 + successBoost * 0.15 - errorTension * 0.06;
      glow.scale.setScalar(11 + state.energy * 1.4 + successBoost * 1.8 - errorTension * 0.2);
    }
  },
  "images-pdf": {
    canvasId: "images-pdf-scene",
    pulseSelectors: ".action-strip button, .upload--drop, .tool-tip-pills span",
    pulseValue: 0.34,
    setup({ scene, data }) {
      const stackGroup = new THREE.Group();
      stackGroup.position.set(-5.2, 1.9, -6.5);
      scene.add(stackGroup);

      const frameColors = [0xf0ece4, 0xd44a1a, 0xe8a838];
      [-0.42, 0, 0.42].forEach((x, index) => {
        const panel = new THREE.Mesh(
          new THREE.PlaneGeometry(3.6, 4.8),
          new THREE.MeshBasicMaterial({
            color: frameColors[index],
            transparent: true,
            opacity: index === 0 ? 0.18 : 0.1,
            side: THREE.DoubleSide
          })
        );
        panel.position.set(x, index * -0.12, index * -0.14);
        panel.rotation.z = index === 0 ? -0.05 : index === 1 ? 0.04 : 0.1;
        stackGroup.add(panel);
      });

      const imageLineMaterial = new THREE.LineBasicMaterial({ color: 0xf0c060, transparent: true, opacity: 0.16 });
      for (let i = 0; i < 2; i++) {
        const points = [
          new THREE.Vector3(-1.1, 1.15 - i * 1.2, 0.12),
          new THREE.Vector3(1.15, 1.15 - i * 1.2, 0.12),
          new THREE.Vector3(1.15, 0.4 - i * 1.2, 0.12),
          new THREE.Vector3(-1.1, 0.4 - i * 1.2, 0.12),
          new THREE.Vector3(-1.1, 1.15 - i * 1.2, 0.12)
        ];
        const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), imageLineMaterial.clone());
        stackGroup.add(line);
      }

      const orbit = new THREE.Group();
      orbit.position.copy(stackGroup.position);
      scene.add(orbit);
      [4.4, 5.8].forEach((radius, index) => {
        const points = Array.from({ length: 72 }, (_, i) => {
          const angle = (i / 72) * Math.PI * 2;
          return new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * (2.7 + index * 0.5), 0);
        });
        const line = new THREE.LineLoop(
          new THREE.BufferGeometry().setFromPoints(points),
          new THREE.LineBasicMaterial({ color: index === 0 ? 0xe8a838 : 0xf0c060, transparent: true, opacity: 0.14 })
        );
        line.rotation.x = 1.15 - index * 0.3;
        line.rotation.y = index * 0.5;
        orbit.add(line);
      });

      const dust = new THREE.Points(
        new THREE.BufferGeometry().setAttribute(
          "position",
          new THREE.BufferAttribute(
            new Float32Array(Array.from({ length: 180 * 3 }, (_, i) => {
              if (i % 3 === 0) return (Math.random() - 0.5) * 8;
              if (i % 3 === 1) return (Math.random() - 0.5) * 5;
              return (Math.random() - 0.5) * 6;
            })),
            3
          )
        ),
        new THREE.PointsMaterial({
          color: 0xe8a838,
          size: 0.08,
          transparent: true,
          opacity: 0.38,
          blending: THREE.AdditiveBlending,
          depthWrite: false
        })
      );
      dust.position.copy(stackGroup.position);
      scene.add(dust);

      const glow = createGlowSprite({
        inner: "rgba(232,168,56,0.24)",
        middle: "rgba(212,74,26,0.1)",
        scale: 12
      });
      glow.position.copy(stackGroup.position);
      scene.add(glow);
      Object.assign(data, { stackGroup, orbit, dust, glow });
    },
    frame({ camera, pointer, state, data }, elapsed) {
      const { stackGroup, orbit, dust, glow } = data;
      if (!stackGroup || !orbit || !dust || !glow) return;
      const successBoost = state.success * 0.24;
      const errorTension = state.error * 0.16;
      camera.position.x = pointer.x * 0.42;
      camera.position.y = -pointer.y * 0.3;
      camera.lookAt(0, 0, -3);
      stackGroup.rotation.y = Math.sin(elapsed * 0.45) * 0.08 + state.energy * 0.08 + successBoost * 0.06;
      stackGroup.rotation.x = Math.cos(elapsed * 0.35) * 0.03 + errorTension * 0.03;
      stackGroup.position.y = 1.9 + Math.sin(elapsed * 0.75) * 0.12;
      orbit.position.copy(stackGroup.position);
      orbit.rotation.z += 0.002 + state.energy * 0.004 + successBoost * 0.004 + errorTension * 0.002;
      dust.position.copy(stackGroup.position);
      dust.rotation.y += 0.0015 + state.energy * 0.003 + successBoost * 0.004;
      dust.material.opacity = 0.38 + successBoost * 0.14 - errorTension * 0.08;
      glow.position.copy(stackGroup.position);
      glow.scale.setScalar(12 + state.energy * 1.5 + successBoost * 1.7 - errorTension * 0.2);
      glow.material.opacity = 0.36 + state.energy * 0.22 + successBoost * 0.14 - errorTension * 0.06;
    }
  },
  merge: {
    canvasId: "merge-pdf-scene",
    pulseSelectors: ".action-strip button, .upload--drop, .tool-tip-pills span",
    pulseValue: 0.34,
    setup({ scene, data }) {
      const stackGroup = new THREE.Group();
      stackGroup.position.set(-5.1, 2.1, -6.4);
      scene.add(stackGroup);

      const sheetColors = [0xa24b2a, 0xf0ece4, 0xe8a838];
      [-0.6, -0.05, 0.5].forEach((x, index) => {
        const panel = new THREE.Mesh(
          new THREE.PlaneGeometry(3.9, 5.1),
          new THREE.MeshBasicMaterial({
            color: sheetColors[index],
            transparent: true,
            opacity: index === 1 ? 0.16 : 0.1,
            side: THREE.DoubleSide
          })
        );
        panel.position.set(x, index * -0.12, -index * 0.12);
        panel.rotation.z = -0.08 + index * 0.08;
        stackGroup.add(panel);
      });

      const spine = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(-1.9, 2.4, 0.16),
          new THREE.Vector3(-1.9, -2.4, 0.16)
        ]),
        new THREE.LineBasicMaterial({ color: 0xf0c060, transparent: true, opacity: 0.2 })
      );
      stackGroup.add(spine);

      const orbit = new THREE.Group();
      orbit.position.copy(stackGroup.position);
      scene.add(orbit);
      [4.6, 5.9].forEach((radius, index) => {
        const line = new THREE.LineLoop(
          new THREE.BufferGeometry().setFromPoints(
            Array.from({ length: 72 }, (_, i) => {
              const angle = (i / 72) * Math.PI * 2;
              return new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * (2.8 + index * 0.55), 0);
            })
          ),
          new THREE.LineBasicMaterial({
            color: index === 0 ? 0xe8a838 : 0xf0c060,
            transparent: true,
            opacity: 0.14
          })
        );
        line.rotation.x = 1.15 - index * 0.28;
        line.rotation.y = index * 0.55;
        orbit.add(line);
      });

      const glow = createGlowSprite({
        inner: "rgba(232,168,56,0.22)",
        middle: "rgba(212,74,26,0.1)",
        scale: 12
      });
      glow.position.copy(stackGroup.position);
      scene.add(glow);

      Object.assign(data, { stackGroup, orbit, glow });
    },
    frame({ camera, pointer, state, data }, elapsed) {
      const { stackGroup, orbit, glow } = data;
      if (!stackGroup || !orbit || !glow) return;
      const successBoost = state.success * 0.24;
      const errorTension = state.error * 0.16;
      camera.position.x = pointer.x * 0.38;
      camera.position.y = -pointer.y * 0.28;
      camera.lookAt(0, 0, -3);
      stackGroup.rotation.y = Math.sin(elapsed * 0.42) * 0.08 + state.energy * 0.08 + successBoost * 0.06;
      stackGroup.rotation.x = Math.cos(elapsed * 0.34) * 0.03 + errorTension * 0.03;
      stackGroup.position.y = 2.1 + Math.sin(elapsed * 0.72) * 0.12;
      orbit.position.copy(stackGroup.position);
      orbit.rotation.z += 0.0018 + state.energy * 0.0038 + successBoost * 0.004 + errorTension * 0.002;
      glow.position.copy(stackGroup.position);
      glow.scale.setScalar(12 + state.energy * 1.5 + successBoost * 1.7 - errorTension * 0.24);
      glow.material.opacity = 0.36 + state.energy * 0.2 + successBoost * 0.15 - errorTension * 0.06;
    }
  },
  numbering: {
    canvasId: "add-page-numbers-scene",
    pulseSelectors: ".action-strip button, .upload--drop, .field select, .tool-tip-pills span",
    pulseValue: 0.32,
    setup({ scene, data }) {
      const sheet = new THREE.Group();
      sheet.position.set(5, 2.2, -6.5);
      scene.add(sheet);

      const page = new THREE.Mesh(
        new THREE.PlaneGeometry(4.2, 5.6),
        new THREE.MeshBasicMaterial({
          color: 0xf0ece4,
          transparent: true,
          opacity: 0.16,
          side: THREE.DoubleSide
        })
      );
      sheet.add(page);

      const lines = new THREE.Group();
      const lineMaterial = new THREE.LineBasicMaterial({ color: 0xe8a838, transparent: true, opacity: 0.16 });
      for (let i = 0; i < 6; i++) {
        const y = 1.8 - i * 0.55;
        lines.add(new THREE.Line(
          new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(-1.3, y, 0.06),
            new THREE.Vector3(1.35, y, 0.06)
          ]),
          lineMaterial.clone()
        ));
      }
      sheet.add(lines);

      const numberRing = new THREE.Group();
      numberRing.position.copy(sheet.position);
      scene.add(numberRing);
      [3.9, 5.2].forEach((radius, index) => {
        const line = new THREE.LineLoop(
          new THREE.BufferGeometry().setFromPoints(
            Array.from({ length: 72 }, (_, i) => {
              const angle = (i / 72) * Math.PI * 2;
              return new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * (2.6 + index * 0.45), 0);
            })
          ),
          new THREE.LineBasicMaterial({
            color: index === 0 ? 0xf0c060 : 0xe8a838,
            transparent: true,
            opacity: 0.13
          })
        );
        line.rotation.x = 1.08 - index * 0.22;
        line.rotation.y = index * 0.42;
        numberRing.add(line);
      });

      const badge = new THREE.Mesh(
        new THREE.CircleGeometry(0.62, 32),
        new THREE.MeshBasicMaterial({ color: 0xe8a838, transparent: true, opacity: 0.2 })
      );
      badge.position.set(0, -2.15, 0.12);
      sheet.add(badge);

      const glow = createGlowSprite({
        inner: "rgba(240,192,96,0.24)",
        middle: "rgba(232,168,56,0.1)",
        scale: 11
      });
      glow.position.copy(sheet.position);
      scene.add(glow);

      Object.assign(data, { sheet, numberRing, glow, badge });
    },
    frame({ camera, pointer, state, data }, elapsed) {
      const { sheet, numberRing, glow, badge } = data;
      if (!sheet || !numberRing || !glow || !badge) return;
      const successBoost = state.success * 0.22;
      const errorTension = state.error * 0.16;
      camera.position.x = pointer.x * 0.34;
      camera.position.y = -pointer.y * 0.26;
      camera.lookAt(0, 0, -3);
      sheet.rotation.y = Math.sin(elapsed * 0.35) * 0.06 + state.energy * 0.05 + successBoost * 0.05;
      sheet.position.y = 2.2 + Math.sin(elapsed * 0.8) * 0.1;
      numberRing.position.copy(sheet.position);
      numberRing.rotation.z += 0.0017 + state.energy * 0.003 + successBoost * 0.004 + errorTension * 0.002;
      badge.scale.setScalar(1 + state.energy * 0.18 + successBoost * 0.26 + Math.sin(elapsed * 1.4) * 0.03 - errorTension * 0.04);
      glow.position.copy(sheet.position);
      glow.scale.setScalar(11 + state.energy * 1.35 + successBoost * 1.5 - errorTension * 0.18);
      glow.material.opacity = 0.34 + state.energy * 0.18 + successBoost * 0.13 - errorTension * 0.05;
    }
  },
  compress: {
    canvasId: "compress-pdf-scene",
    pulseSelectors: ".action-strip button, .upload--drop, .tool-tip-pills span",
    pulseValue: 0.32,
    setup({ scene, data }) {
      const group = new THREE.Group();
      group.position.set(5.2, 1.8, -6);
      scene.add(group);

      const ringMat = (opacity, color) => new THREE.LineBasicMaterial({ color, transparent: true, opacity });
      const rings = [];
      [3.8, 2.9, 2.1, 1.4].forEach((r, i) => {
        const pts = Array.from({ length: 64 }, (_, k) => {
          const a = (k / 64) * Math.PI * 2;
          return new THREE.Vector3(Math.cos(a) * r, i * -0.55, Math.sin(a) * r);
        });
        const ring = new THREE.LineLoop(
          new THREE.BufferGeometry().setFromPoints(pts),
          ringMat(0.1 + i * 0.045, i % 2 === 0 ? 0xe8a838 : 0xf0c060)
        );
        ring.rotation.x = 0.3 + i * 0.12;
        group.add(ring);
        rings.push(ring);
      });

      const glow = createGlowSprite({ inner: "rgba(232,168,56,0.18)", middle: "rgba(212,74,26,0.07)", scale: 10 });
      glow.position.copy(group.position);
      scene.add(glow);

      Object.assign(data, { group, rings, glow });
    },
    frame({ camera, pointer, state, data }, elapsed) {
      const { group, glow } = data;
      if (!group) return;
      const successBoost = state.success * 0.24;
      const errorTension = state.error * 0.16;
      camera.position.x = pointer.x * 0.35;
      camera.position.y = -pointer.y * 0.25;
      camera.lookAt(0, 0, -3);
      group.rotation.y = elapsed * 0.22 + state.energy * 0.12;
      group.rotation.x = Math.sin(elapsed * 0.31) * 0.06;
      group.position.y = 1.8 + Math.sin(elapsed * 0.65) * 0.1;
      glow.position.copy(group.position);
      glow.scale.setScalar(10 + state.energy * 1.2 + successBoost * 1.4 - errorTension * 0.18);
      glow.material.opacity = 0.32 + state.energy * 0.18 + successBoost * 0.12 - errorTension * 0.05;
    }
  },
  protect: {
    canvasId: "protect-pdf-scene",
    pulseSelectors: ".action-strip button, .upload--drop, .field input, .tool-tip-pills span",
    pulseValue: 0.34,
    setup({ scene, data }) {
      const group = new THREE.Group();
      group.position.set(5.1, 1.4, -6.4);
      scene.add(group);

      const mat = (opacity, color) => new THREE.LineBasicMaterial({ color, transparent: true, opacity });

      const shieldPts = [
        [0, 3.0], [2.2, 2.0], [2.2, -0.5], [0, -2.8], [-2.2, -0.5], [-2.2, 2.0], [0, 3.0]
      ].map(([x, y]) => new THREE.Vector3(x * 0.9, y * 0.9, 0));
      group.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(shieldPts), mat(0.22, 0xe8a838)));

      [1.6, 2.4].forEach((r, i) => {
        const pts = Array.from({ length: 48 }, (_, k) => {
          const a = (k / 48) * Math.PI * 2;
          return new THREE.Vector3(Math.cos(a) * r, Math.sin(a) * r, 0.01);
        });
        group.add(new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts), mat(0.1 + i * 0.04, 0xf0c060)));
      });

      const glow = createGlowSprite({ inner: "rgba(232,168,56,0.2)", middle: "rgba(212,74,26,0.08)", scale: 11 });
      glow.position.copy(group.position);
      scene.add(glow);

      Object.assign(data, { group, glow });
    },
    frame({ camera, pointer, state, data }, elapsed) {
      const { group, glow } = data;
      if (!group) return;
      const successBoost = state.success * 0.26;
      const errorTension = state.error * 0.16;
      camera.position.x = pointer.x * 0.35;
      camera.position.y = -pointer.y * 0.25;
      camera.lookAt(0, 0, -3);
      group.rotation.y = Math.sin(elapsed * 0.26) * 0.09 + pointer.x * 0.05;
      group.rotation.x = Math.sin(elapsed * 0.18) * 0.04;
      group.position.y = 1.4 + Math.sin(elapsed * 0.64) * 0.1;
      glow.position.copy(group.position);
      glow.scale.setScalar(11 + state.energy * 1.4 + successBoost * 1.6 - errorTension * 0.22);
      glow.material.opacity = 0.34 + state.energy * 0.18 + successBoost * 0.16 - errorTension * 0.06;
    }
  },
  watermark: {
    canvasId: "watermark-pdf-scene",
    pulseSelectors: ".action-strip button, .upload--drop, .field input, .field select, .tool-tip-pills span",
    pulseValue: 0.34,
    setup({ scene, data }) {
      const pageGroup = new THREE.Group();
      pageGroup.position.set(5, 2.15, -6.6);
      scene.add(pageGroup);

      const page = new THREE.Mesh(
        new THREE.PlaneGeometry(4.1, 5.4),
        new THREE.MeshBasicMaterial({
          color: 0xf0ece4,
          transparent: true,
          opacity: 0.14,
          side: THREE.DoubleSide
        })
      );
      pageGroup.add(page);

      const watermarkA = new THREE.Mesh(
        new THREE.PlaneGeometry(3.2, 0.5),
        new THREE.MeshBasicMaterial({ color: 0xe8a838, transparent: true, opacity: 0.12, side: THREE.DoubleSide })
      );
      watermarkA.rotation.z = -0.62;
      pageGroup.add(watermarkA);

      const watermarkB = new THREE.Mesh(
        new THREE.PlaneGeometry(2.6, 0.34),
        new THREE.MeshBasicMaterial({ color: 0xd44a1a, transparent: true, opacity: 0.09, side: THREE.DoubleSide })
      );
      watermarkB.rotation.z = -0.62;
      watermarkB.position.set(0.2, -0.6, 0.04);
      pageGroup.add(watermarkB);

      const orbit = new THREE.Group();
      orbit.position.copy(pageGroup.position);
      scene.add(orbit);
      [4.2, 5.6].forEach((radius, index) => {
        const line = new THREE.LineLoop(
          new THREE.BufferGeometry().setFromPoints(
            Array.from({ length: 72 }, (_, i) => {
              const angle = (i / 72) * Math.PI * 2;
              return new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * (2.7 + index * 0.45), 0);
            })
          ),
          new THREE.LineBasicMaterial({
            color: index === 0 ? 0xd44a1a : 0xe8a838,
            transparent: true,
            opacity: 0.13
          })
        );
        line.rotation.x = 1.08 - index * 0.24;
        line.rotation.y = index * 0.48;
        orbit.add(line);
      });

      const glow = createGlowSprite({
        inner: "rgba(212,74,26,0.18)",
        middle: "rgba(232,168,56,0.12)",
        scale: 11.5
      });
      glow.position.copy(pageGroup.position);
      scene.add(glow);

      Object.assign(data, { pageGroup, watermarkA, watermarkB, orbit, glow });
    },
    frame({ camera, pointer, state, data }, elapsed) {
      const { pageGroup, watermarkA, watermarkB, orbit, glow } = data;
      if (!pageGroup || !watermarkA || !watermarkB || !orbit || !glow) return;
      const successBoost = state.success * 0.24;
      const errorTension = state.error * 0.16;
      camera.position.x = pointer.x * 0.34;
      camera.position.y = -pointer.y * 0.26;
      camera.lookAt(0, 0, -3);
      pageGroup.rotation.y = Math.sin(elapsed * 0.38) * 0.06 + state.energy * 0.06 + successBoost * 0.05;
      pageGroup.position.y = 2.15 + Math.sin(elapsed * 0.75) * 0.1;
      watermarkA.scale.setScalar(1 + state.energy * 0.08 + successBoost * 0.1 - errorTension * 0.03);
      watermarkB.scale.setScalar(1 + state.energy * 0.06 + successBoost * 0.08 - errorTension * 0.02);
      orbit.position.copy(pageGroup.position);
      orbit.rotation.z += 0.0018 + state.energy * 0.0034 + successBoost * 0.004 + errorTension * 0.002;
      glow.position.copy(pageGroup.position);
      glow.scale.setScalar(11.5 + state.energy * 1.45 + successBoost * 1.6 - errorTension * 0.24);
      glow.material.opacity = 0.34 + state.energy * 0.2 + successBoost * 0.14 - errorTension * 0.06;
    }
  }
};

export function mountToolScenePreset(name, options = {}) {
  const preset = scenePresets[name];
  if (!preset) {
    console.warn(`Unknown tool scene preset: ${name}`);
    return null;
  }
  return mountToolScene({ ...preset, ...options });
}

export { scenePresets };
