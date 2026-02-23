const state = {
  initialized: false,
  container: null,
  starCanvas: null,
  starContext: null,
  canvas: null,
  context: null,
  frameId: null,
  resizeObserver: null,
  resizeHandler: null,
  width: 0,
  height: 0,
  centerX: 0,
  centerY: 0,
  globeRadius: 0,
  startTime: 0,
  stars: [],
  signalArcs: [],
  selectedCity: null,
};

const STAR_LIMIT = 100;

function randomRange(min, max) {
  return min + Math.random() * (max - min);
}

function createSignalArcs() {
  const arcs = [];
  for (let index = 0; index < 5; index += 1) {
    arcs.push({
      startAngle: randomRange(-Math.PI * 0.95, Math.PI * 0.95),
      endAngle: randomRange(-Math.PI * 0.95, Math.PI * 0.95),
      heightFactor: randomRange(0.18, 0.34),
      speed: randomRange(0.12, 0.22),
      phase: randomRange(0, 1),
      hue: randomRange(184, 205),
    });
  }
  state.signalArcs = arcs;
}

function createStarfield() {
  const area = state.width * state.height;
  const starCount = Math.min(STAR_LIMIT, Math.max(55, Math.round(area / 5200)));
  const colors = [
    "rgba(242, 248, 255, 1)",
    "rgba(214, 241, 255, 1)",
    "rgba(186, 230, 253, 1)",
  ];

  state.stars = Array.from({ length: starCount }, () => ({
    xRatio: Math.random(),
    yRatio: Math.random(),
    size: randomRange(1, 3),
    baseOpacity: randomRange(0.12, 0.34),
    twinkleAmplitude: randomRange(0.05, 0.18),
    twinkleSpeed: randomRange(0.22, 0.55),
    twinklePhase: randomRange(0, Math.PI * 2),
    driftSpeed: randomRange(1.4, 4.2),
    color: colors[Math.floor(Math.random() * colors.length)],
  }));
}

function resizeCanvas() {
  if (!state.container || !state.canvas || !state.context || !state.starCanvas || !state.starContext) {
    return;
  }

  const width = Math.max(320, Math.floor(state.container.clientWidth || 0));
  const height = Math.max(260, Math.floor(state.container.clientHeight || 0));
  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);

  state.canvas.width = Math.floor(width * pixelRatio);
  state.canvas.height = Math.floor(height * pixelRatio);
  state.canvas.style.width = `${width}px`;
  state.canvas.style.height = `${height}px`;

  state.starCanvas.width = Math.floor(width * pixelRatio);
  state.starCanvas.height = Math.floor(height * pixelRatio);
  state.starCanvas.style.width = `${width}px`;
  state.starCanvas.style.height = `${height}px`;

  state.context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  state.starContext.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);

  state.width = width;
  state.height = height;
  state.centerX = width * 0.5;
  state.centerY = height * 0.52;
  state.globeRadius = Math.min(width, height) * 0.32;

  createStarfield();
}

function drawStarfield(context, elapsedSeconds) {
  context.clearRect(0, 0, state.width, state.height);

  for (const star of state.stars) {
    const twinkle = Math.sin((elapsedSeconds * star.twinkleSpeed * Math.PI * 2) + star.twinklePhase);
    const opacity = Math.max(0.06, Math.min(0.45, star.baseOpacity + (twinkle * star.twinkleAmplitude)));
    const driftOffset = (elapsedSeconds * star.driftSpeed) % (state.height + 8);
    const x = star.xRatio * state.width;
    const y = ((star.yRatio * state.height) + state.height - driftOffset) % state.height;

    context.beginPath();
    context.arc(x, y, star.size * 0.5, 0, Math.PI * 2);
    context.fillStyle = star.color.replace("1)", `${opacity})`);
    context.fill();
  }
}

function drawBackdrop(context) {
  const glow = context.createRadialGradient(
    state.centerX,
    state.centerY,
    state.globeRadius * 0.4,
    state.centerX,
    state.centerY,
    state.globeRadius * 1.9
  );
  glow.addColorStop(0, "rgba(56, 189, 248, 0.18)");
  glow.addColorStop(1, "rgba(15, 23, 42, 0)");

  context.fillStyle = glow;
  context.fillRect(0, 0, state.width, state.height);
}

function drawGlobe(context, elapsedSeconds) {
  const oceanGradient = context.createRadialGradient(
    state.centerX - state.globeRadius * 0.3,
    state.centerY - state.globeRadius * 0.35,
    state.globeRadius * 0.18,
    state.centerX,
    state.centerY,
    state.globeRadius
  );
  oceanGradient.addColorStop(0, "#53e4ff");
  oceanGradient.addColorStop(0.45, "#1792d9");
  oceanGradient.addColorStop(1, "#003366");

  context.beginPath();
  context.arc(state.centerX, state.centerY, state.globeRadius, 0, Math.PI * 2);
  context.fillStyle = oceanGradient;
  context.fill();

  const highlightX = state.centerX + state.globeRadius * 0.22;
  const highlightY = state.centerY - state.globeRadius * 0.35;
  const highlight = context.createRadialGradient(highlightX, highlightY, 0, highlightX, highlightY, state.globeRadius * 0.52);
  highlight.addColorStop(0, "rgba(209, 250, 255, 0.45)");
  highlight.addColorStop(1, "rgba(209, 250, 255, 0)");
  context.fillStyle = highlight;
  context.fillRect(state.centerX - state.globeRadius, state.centerY - state.globeRadius, state.globeRadius * 2, state.globeRadius * 2);

  context.save();
  context.beginPath();
  context.arc(state.centerX, state.centerY, state.globeRadius, 0, Math.PI * 2);
  context.clip();

  const drift = elapsedSeconds * 0.35;
  context.fillStyle = "rgba(30, 215, 96, 0.85)";

  context.beginPath();
  context.ellipse(state.centerX - state.globeRadius * 0.35 + Math.sin(drift) * 4, state.centerY - state.globeRadius * 0.1, state.globeRadius * 0.35, state.globeRadius * 0.22, -0.3, 0, Math.PI * 2);
  context.fill();

  context.beginPath();
  context.ellipse(state.centerX + state.globeRadius * 0.26 + Math.cos(drift * 0.8) * 3, state.centerY + state.globeRadius * 0.2, state.globeRadius * 0.28, state.globeRadius * 0.18, 0.24, 0, Math.PI * 2);
  context.fill();

  context.beginPath();
  context.ellipse(state.centerX + state.globeRadius * 0.18, state.centerY - state.globeRadius * 0.35, state.globeRadius * 0.18, state.globeRadius * 0.12, 0.15, 0, Math.PI * 2);
  context.fill();

  context.restore();

  context.strokeStyle = "rgba(132, 235, 255, 0.42)";
  context.lineWidth = 1.5;
  context.beginPath();
  context.arc(state.centerX, state.centerY, state.globeRadius, 0, Math.PI * 2);
  context.stroke();
}

function drawOrbitRings(context, elapsedSeconds) {
  context.save();
  context.translate(state.centerX, state.centerY);

  const drawRing = (rotation, widthScale, heightScale, color) => {
    context.save();
    context.rotate(rotation);
    context.beginPath();
    context.ellipse(0, 0, state.globeRadius * widthScale, state.globeRadius * heightScale, 0, 0, Math.PI * 2);
    context.strokeStyle = color;
    context.lineWidth = 1.2;
    context.stroke();
    context.restore();
  };

  drawRing(elapsedSeconds * 0.22, 1.32, 0.43, "rgba(224, 248, 255, 0.20)");
  drawRing(-elapsedSeconds * 0.18, 1.2, 0.36, "rgba(117, 236, 255, 0.22)");

  context.restore();
}

function pointOnSphereEdge(angle) {
  return {
    x: state.centerX + Math.cos(angle) * state.globeRadius,
    y: state.centerY + Math.sin(angle) * state.globeRadius,
  };
}

function drawSignalArcs(context, elapsedSeconds) {
  state.signalArcs.forEach((arc) => {
    const start = pointOnSphereEdge(arc.startAngle);
    const end = pointOnSphereEdge(arc.endAngle);

    const controlX = (start.x + end.x) * 0.5;
    const controlY = (start.y + end.y) * 0.5 - state.globeRadius * arc.heightFactor;

    const path = new Path2D();
    path.moveTo(start.x, start.y);
    path.quadraticCurveTo(controlX, controlY, end.x, end.y);

    context.save();
    context.setLineDash([10, 12]);
    context.lineDashOffset = -(elapsedSeconds * 120 * arc.speed);
    context.strokeStyle = `hsla(${arc.hue}, 95%, 72%, 0.42)`;
    context.lineWidth = 1.5;
    context.stroke(path);
    context.restore();

    const t = (elapsedSeconds * arc.speed + arc.phase) % 1;
    const oneMinusT = 1 - t;
    const pulseX = (oneMinusT * oneMinusT * start.x) + (2 * oneMinusT * t * controlX) + (t * t * end.x);
    const pulseY = (oneMinusT * oneMinusT * start.y) + (2 * oneMinusT * t * controlY) + (t * t * end.y);

    context.beginPath();
    context.arc(pulseX, pulseY, 3.2, 0, Math.PI * 2);
    context.fillStyle = "rgba(206, 254, 255, 0.95)";
    context.fill();
  });
}

function drawSelectedCityMarker(context, elapsedSeconds) {
  if (!state.selectedCity || typeof state.selectedCity.longitude !== "number" || typeof state.selectedCity.latitude !== "number") {
    return;
  }

  const lon = (state.selectedCity.longitude * Math.PI) / 180;
  const lat = (state.selectedCity.latitude * Math.PI) / 180;
  const x = state.centerX + Math.sin(lon) * Math.cos(lat) * state.globeRadius * 0.9;
  const y = state.centerY - Math.sin(lat) * state.globeRadius * 0.72;
  const pulse = 3 + ((Math.sin(elapsedSeconds * 4) + 1) * 2.2);

  context.beginPath();
  context.arc(x, y, pulse, 0, Math.PI * 2);
  context.fillStyle = "rgba(125, 249, 255, 0.78)";
  context.fill();
}

function drawFrame(timestamp) {
  if (!state.context || !state.starContext) {
    return;
  }

  if (!state.startTime) {
    state.startTime = timestamp;
  }

  const elapsedSeconds = (timestamp - state.startTime) / 1000;
  const context = state.context;
  const starContext = state.starContext;

  drawStarfield(starContext, elapsedSeconds);

  context.clearRect(0, 0, state.width, state.height);
  drawBackdrop(context);
  drawOrbitRings(context, elapsedSeconds);
  drawGlobe(context, elapsedSeconds);
  drawSignalArcs(context, elapsedSeconds);
  drawSelectedCityMarker(context, elapsedSeconds);

  state.frameId = requestAnimationFrame(drawFrame);
}

function attachResizeHandling() {
  if (!state.container) {
    return;
  }

  state.resizeHandler = () => {
    resizeCanvas();
  };

  window.addEventListener("resize", state.resizeHandler, { passive: true });

  if (typeof ResizeObserver !== "undefined") {
    state.resizeObserver = new ResizeObserver(() => {
      resizeCanvas();
    });
    state.resizeObserver.observe(state.container);
  }
}

function cleanup() {
  if (state.frameId) {
    cancelAnimationFrame(state.frameId);
    state.frameId = null;
  }

  if (state.resizeHandler) {
    window.removeEventListener("resize", state.resizeHandler);
    state.resizeHandler = null;
  }

  if (state.resizeObserver) {
    state.resizeObserver.disconnect();
    state.resizeObserver = null;
  }
}

export async function initializeGlobe(containerId) {
  const container = document.getElementById(containerId);
  if (!container) {
    return;
  }

  if (state.initialized && state.container === container) {
    return;
  }

  cleanup();

  state.container = container;
  state.container.innerHTML = "";

  const starCanvas = document.createElement("canvas");
  starCanvas.className = "globe-starfield-canvas";
  state.container.appendChild(starCanvas);

  const canvas = document.createElement("canvas");
  canvas.className = "globe-main-canvas";
  state.container.appendChild(canvas);

  const starContext = starCanvas.getContext("2d");
  const context = canvas.getContext("2d");
  if (!context || !starContext) {
    return;
  }

  state.starCanvas = starCanvas;
  state.starContext = starContext;
  state.canvas = canvas;
  state.context = context;
  createSignalArcs();
  resizeCanvas();
  attachResizeHandling();

  state.startTime = 0;
  state.frameId = requestAnimationFrame(drawFrame);
  state.initialized = true;
}

export function updateGlobeWithCity(cityData) {
  state.selectedCity = cityData || null;
}

export function disposeGlobeScene() {
  cleanup();
  state.initialized = false;
  state.container = null;
  state.starCanvas = null;
  state.starContext = null;
  state.canvas = null;
  state.context = null;
  state.stars = [];
  state.selectedCity = null;
}

if (typeof window !== "undefined") {
  window.initializeGlobe = initializeGlobe;
  window.updateGlobeWithCity = updateGlobeWithCity;
}
