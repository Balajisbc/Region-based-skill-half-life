import {
  compareCities,
  downloadReport,
  fetchAnalytics,
  fetchRegions,
  fetchReportPreview,
  getCities,
  runSimulationRefresh,
} from "./api.js";
import { initializeAssistant, resetAssistantConversation, setAssistantContext } from "./assistant.js";
import { renderStabilityRadarChart } from "./report.js";
import { initializeGlobe, updateGlobeWithCity } from "./globe/GlobeScene.js";

if (!localStorage.getItem("userLoggedIn")) {
  window.location.href = "login.html";
}

let migrationFlowInterval = null;
let reportDownloading = false;

const isDev = ["127.0.0.1", "localhost"].includes(window.location.hostname);

function devLog(...args) {
  if (isDev) {
    console.log(...args);
  }
}

const dashboardState = {
  regionMap: {},
  cityDetailsByCountry: {},
  analytics: null,
  chartInstance: null,
  forecastChartInstance: null,
  radarInstance: null,
  reportPreview: null,
  initialized: false,
  signalAnimationFrame: null,
  signalResizeObserver: null,
  summaryCountersAnimated: false,
  premiumCountersAnimated: false,
  starfieldAnimationFrame: null,
  starfieldActive: false,
  starfieldInitialized: false,
};

const refs = {
  countrySelect: null,
  citySelect: null,
  skillSelect: null,
  experienceSelect: null,
  timeHorizonSelect: null,
  startJourneyBtn: null,
  downloadReportBtn: null,
  halfLifeValue: null,
  trendValue: null,
  salaryRange: null,
  cityNameSlot: null,
  demandChart: null,
  forecastTrendChart: null,
  stabilityRadar: null,
  migrationMap: null,
  migrationFromCountry: null,
  migrationFromCity: null,
  migrationToCountry: null,
  migrationToCity: null,
  migrationFlowTooltip: null,
  migrationScoreValue: null,
  migrationDemandDelta: null,
  migrationSalaryAdvantage: null,
  migrationCompetitionDiff: null,
  migrationFlowTrend: null,
  demandIndexValue: null,
  globalRankValue: null,
  careerScoreValue: null,
  automationRiskValue: null,
  insightGlobalRank: null,
  insightMomentum: null,
  insightSalaryGrowth: null,
  insightAutomationRisk: null,
  insightTopCompanies: null,
  insightConfidence: null,
  aiRecommendedSkill: null,
  aiRiskRewardFill: null,
  aiRiskRewardLabel: null,
  aiCareerTimeline: null,
  aiMigrationCities: null,
  radarCountry: null,
  radarRegion: null,
  radarMarketTier: null,
  radarTopIndustries: null,
  stabilityScoreValue: null,
  radarDemandLevel: null,
  radarGrowthRate: null,
  radarLongevity: null,
  radarRiskLevel: null,
  radarCareerBadge: null,
  flightPath: null,
  plane: null,
  landingPulse: null,
  signalPathA: null,
  signalPathB: null,
  signalDotA: null,
  signalDotB: null,
};

const fallbackTimeline = ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6"];

const cityCoordinateFallback = {
  Bengaluru: { latitude: 12.9716, longitude: 77.5946, tech_index: 86.4 },
  Mumbai: { latitude: 19.076, longitude: 72.8777, tech_index: 81.2 },
  Hyderabad: { latitude: 17.385, longitude: 78.4867, tech_index: 84.1 },
  "San Francisco": { latitude: 37.7749, longitude: -122.4194, tech_index: 92.0 },
  Seattle: { latitude: 47.6062, longitude: -122.3321, tech_index: 89.0 },
  "New York": { latitude: 40.7128, longitude: -74.006, tech_index: 88.0 },
  London: { latitude: 51.5072, longitude: -0.1276, tech_index: 88.0 },
};

const uiState = {
  initialized: false,
};

const uiRefs = {
  logoutBtn: null,
  userEmailLabel: null,
  settingsButton: null,
  settingsOverlay: null,
  settingsPanel: null,
  themeToggleBtn: null,
  clearChatBtn: null,
  closeSettingsBtn: null,
};

const storageKeys = {
  userEmail: "userEmail",
  theme: "dashboardTheme",
  chatHistory: "chatHistory",
};

function selectFirst(...selectors) {
  for (const selector of selectors) {
    const element = document.querySelector(selector);
    if (element) {
      return element;
    }
  }
  return null;
}

function safeStorageGet(key) {
  try {
    return window.localStorage.getItem(key);
  } catch (_error) {
    return null;
  }
}

function safeStorageSet(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch (_error) {
    devLog("Storage unavailable for setItem", key);
  }
}

function safeStorageRemove(key) {
  try {
    window.localStorage.removeItem(key);
  } catch (_error) {
    devLog("Storage unavailable for removeItem", key);
  }
}

function safeStorageClear() {
  try {
    window.localStorage.clear();
  } catch (_error) {
    devLog("Storage unavailable for clear");
  }
}

function cacheUiRefs() {
  uiRefs.logoutBtn = selectFirst("#logoutBtn");
  uiRefs.userEmailLabel = selectFirst("#userEmailLabel");
  uiRefs.settingsButton = selectFirst(".settings-button");
  uiRefs.settingsOverlay = selectFirst("#settingsModalOverlay");
  uiRefs.settingsPanel = selectFirst("#settingsPanel");
  uiRefs.themeToggleBtn = selectFirst("#themeToggleBtn");
  uiRefs.clearChatBtn = selectFirst("#clearChatBtn");
  uiRefs.closeSettingsBtn = selectFirst("#closeSettingsBtn");
}

function isLightTheme() {
  return document.body.classList.contains("theme-light");
}

function updateThemeToggleLabel() {
  if (!uiRefs.themeToggleBtn) {
    return;
  }
  uiRefs.themeToggleBtn.textContent = isLightTheme() ? "Switch to Dark Theme" : "Switch to Light Theme";
}

function applySavedTheme() {
  const theme = safeStorageGet(storageKeys.theme);
  if (theme === "light") {
    document.body.classList.add("theme-light");
  } else {
    document.body.classList.remove("theme-light");
  }
  updateThemeToggleLabel();
}

function toggleTheme() {
  const nextLight = !isLightTheme();
  document.body.classList.toggle("theme-light", nextLight);
  safeStorageSet(storageKeys.theme, nextLight ? "light" : "dark");
  updateThemeToggleLabel();
}

function openSettingsPanel() {
  if (!uiRefs.settingsOverlay || !uiRefs.settingsPanel) {
    return;
  }
  uiRefs.settingsOverlay.hidden = false;
  requestAnimationFrame(() => {
    uiRefs.settingsOverlay.classList.add("is-open");
    uiRefs.settingsPanel.classList.add("is-open");
    uiRefs.settingsPanel.setAttribute("aria-hidden", "false");
  });
}

function closeSettingsPanel() {
  if (!uiRefs.settingsOverlay || !uiRefs.settingsPanel) {
    return;
  }
  uiRefs.settingsOverlay.classList.remove("is-open");
  uiRefs.settingsPanel.classList.remove("is-open");
  uiRefs.settingsPanel.setAttribute("aria-hidden", "true");
  window.setTimeout(() => {
    if (uiRefs.settingsOverlay && !uiRefs.settingsOverlay.classList.contains("is-open")) {
      uiRefs.settingsOverlay.hidden = true;
    }
  }, 220);
}

function clearChatUiState() {
  resetAssistantConversation();
  safeStorageRemove(storageKeys.chatHistory);
}

function syncProfileEmail(userEmail) {
  if (uiRefs.userEmailLabel) {
    uiRefs.userEmailLabel.textContent = userEmail;
  }
}

function resetUiAfterLogout() {
  clearChatUiState();
  closeSettingsPanel();
  document.body.classList.remove("theme-light");
  updateThemeToggleLabel();
  const chatInput = selectFirst("#chatInput");
  if (chatInput) {
    chatInput.value = "";
  }
}

function redirectToLogin() {
  window.location.href = "login.html";
}

function handleLogout() {
  safeStorageClear();
  resetUiAfterLogout();
  redirectToLogin();
}

function initializeDashboardControls() {
  if (uiState.initialized) {
    return;
  }

  cacheUiRefs();
  const userEmail = safeStorageGet(storageKeys.userEmail);
  if (!userEmail) {
    redirectToLogin();
    return;
  }
  syncProfileEmail(userEmail);
  applySavedTheme();

  uiRefs.settingsButton?.addEventListener("click", openSettingsPanel);
  uiRefs.closeSettingsBtn?.addEventListener("click", closeSettingsPanel);
  uiRefs.themeToggleBtn?.addEventListener("click", toggleTheme);
  uiRefs.clearChatBtn?.addEventListener("click", clearChatUiState);
  uiRefs.logoutBtn?.addEventListener("click", handleLogout);

  uiRefs.settingsOverlay?.addEventListener("click", (event) => {
    if (event.target === uiRefs.settingsOverlay) {
      closeSettingsPanel();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeSettingsPanel();
    }
  });

  uiState.initialized = true;
}

function cacheDomReferences() {
  refs.countrySelect = selectFirst("#countrySelect");
  refs.citySelect = selectFirst("#citySelect");
  refs.skillSelect = selectFirst("#skillSelect");
  refs.experienceSelect = selectFirst("#experienceSelect");
  refs.timeHorizonSelect = selectFirst("#timeHorizonSelect");
  refs.startJourneyBtn = selectFirst("#startJourneyBtn");
  refs.downloadReportBtn = selectFirst("#downloadReportBtn");
  refs.halfLifeValue = selectFirst("#halfLifeValue");
  refs.trendValue = selectFirst("#trendValue");
  refs.salaryRange = selectFirst("#salaryRange");
  refs.cityNameSlot = selectFirst("#cityNameSlot");
  refs.demandChart = selectFirst("#skillDemandChart", "#demandChart");
  refs.forecastTrendChart = selectFirst("#forecastTrendChart");
  refs.stabilityRadar = selectFirst("#stabilityRadar");
  refs.migrationMap = selectFirst("#migrationMap");
  refs.migrationFromCountry = selectFirst("#migrationFromCountry");
  refs.migrationFromCity = selectFirst("#migrationFromCity");
  refs.migrationToCountry = selectFirst("#migrationToCountry");
  refs.migrationToCity = selectFirst("#migrationToCity");
  refs.migrationFlowTooltip = selectFirst("#migrationFlowTooltip");
  refs.migrationScoreValue = selectFirst("#migrationScoreValue");
  refs.migrationDemandDelta = selectFirst("#migrationDemandDelta");
  refs.migrationSalaryAdvantage = selectFirst("#migrationSalaryAdvantage");
  refs.migrationCompetitionDiff = selectFirst("#migrationCompetitionDiff");
  refs.migrationFlowTrend = selectFirst("#migrationFlowTrend");
  refs.demandIndexValue = selectFirst("#demandIndexValue");
  refs.globalRankValue = selectFirst("#globalRankValue");
  refs.careerScoreValue = selectFirst("#careerScoreValue");
  refs.automationRiskValue = selectFirst("#automationRiskValue");
  refs.insightGlobalRank = selectFirst("#insightGlobalRank");
  refs.insightMomentum = selectFirst("#insightMomentum");
  refs.insightSalaryGrowth = selectFirst("#insightSalaryGrowth");
  refs.insightAutomationRisk = selectFirst("#insightAutomationRisk");
  refs.insightTopCompanies = selectFirst("#insightTopCompanies");
  refs.insightConfidence = selectFirst("#insightConfidence");
  refs.aiRecommendedSkill = selectFirst("#aiRecommendedSkill");
  refs.radarCountry = selectFirst("#radarCountry");
  refs.radarRegion = selectFirst("#radarRegion");
  refs.radarMarketTier = selectFirst("#radarMarketTier");
  refs.radarTopIndustries = selectFirst("#radarTopIndustries");
  refs.stabilityScoreValue = selectFirst("#stabilityScoreValue");
  refs.radarDemandLevel = selectFirst("#radarDemandLevel");
  refs.radarGrowthRate = selectFirst("#radarGrowthRate");
  refs.radarLongevity = selectFirst("#radarLongevity");
  refs.radarRiskLevel = selectFirst("#radarRiskLevel");
  refs.radarCareerBadge = selectFirst("#radarCareerBadge");
  refs.aiRiskRewardFill = selectFirst("#aiRiskRewardFill");
  refs.aiRiskRewardLabel = selectFirst("#aiRiskRewardLabel");
  refs.aiCareerTimeline = selectFirst("#aiCareerTimeline");
  refs.aiMigrationCities = selectFirst("#aiMigrationCities");
  refs.flightPath = selectFirst("#flightPath");
  refs.plane = selectFirst("#plane");
  refs.landingPulse = selectFirst("#landingPulse");
  refs.signalPathA = selectFirst("#signalPathA");
  refs.signalPathB = selectFirst("#signalPathB");
  refs.signalDotA = selectFirst("#signalDotA");
  refs.signalDotB = selectFirst("#signalDotB");
}

function initializeGlobeSignalAnimation() {
  const pathA = refs.signalPathA || selectFirst("#signalPathA");
  const pathB = refs.signalPathB || selectFirst("#signalPathB");
  const dotA = refs.signalDotA || selectFirst("#signalDotA");
  const dotB = refs.signalDotB || selectFirst("#signalDotB");

  if (!pathA || !pathB || !dotA || !dotB || typeof pathA.getPointAtLength !== "function" || typeof pathB.getPointAtLength !== "function") {
    return;
  }

  if (dashboardState.signalAnimationFrame) {
    cancelAnimationFrame(dashboardState.signalAnimationFrame);
    dashboardState.signalAnimationFrame = null;
  }

  const lengthA = pathA.getTotalLength();
  const lengthB = pathB.getTotalLength();
  let origin = 0;

  const tick = (timestamp) => {
    if (!origin) {
      origin = timestamp;
    }

    const elapsed = (timestamp - origin) / 1000;
    const progressA = (elapsed * 0.18) % 1;
    const progressB = (elapsed * 0.13 + 0.4) % 1;

    const pointA = pathA.getPointAtLength(progressA * lengthA);
    const pointB = pathB.getPointAtLength(progressB * lengthB);

    dotA.setAttribute("cx", String(pointA.x));
    dotA.setAttribute("cy", String(pointA.y));
    dotB.setAttribute("cx", String(pointB.x));
    dotB.setAttribute("cy", String(pointB.y));

    dashboardState.signalAnimationFrame = requestAnimationFrame(tick);
  };

  dashboardState.signalAnimationFrame = requestAnimationFrame(tick);
}

function animateJourneyGlobeFlight() {
  const path = refs.flightPath || selectFirst("#flightPath");
  const plane = refs.plane || selectFirst("#plane");
  const landingPulse = refs.landingPulse || selectFirst("#landingPulse");

  if (!path || !plane || typeof path.getTotalLength !== "function" || typeof path.getPointAtLength !== "function") {
    return;
  }

  const length = path.getTotalLength();
  path.style.transition = "none";
  path.style.strokeDasharray = "1000";
  path.style.strokeDashoffset = "1000";
  path.getBoundingClientRect();
  path.style.transition = "stroke-dashoffset 2s ease";
  path.style.strokeDashoffset = "0";

  let start = 0;
  const duration = 2000;

  const animatePlane = (timestamp) => {
    if (!start) {
      start = timestamp;
    }

    const progress = timestamp - start;
    const percent = Math.min(progress / duration, 1);
    const point = path.getPointAtLength(percent * length);

    plane.setAttribute("x", String(point.x));
    plane.setAttribute("y", String(point.y));

    if (percent < 1) {
      requestAnimationFrame(animatePlane);
    } else if (landingPulse) {
      const destination = path.getPointAtLength(length);
      landingPulse.setAttribute("cx", String(destination.x));
      landingPulse.setAttribute("cy", String(destination.y));

      let pulseStart = 0;
      const pulseDuration = 650;
      const pulseStep = (pulseTimestamp) => {
        if (!pulseStart) {
          pulseStart = pulseTimestamp;
        }
        const pulseProgress = Math.min((pulseTimestamp - pulseStart) / pulseDuration, 1);
        const radius = 2 + pulseProgress * 20;
        const opacity = Math.max(0, 0.85 - pulseProgress);

        landingPulse.setAttribute("r", String(radius));
        landingPulse.setAttribute("opacity", String(opacity));

        if (pulseProgress < 1) {
          requestAnimationFrame(pulseStep);
        } else {
          landingPulse.setAttribute("r", "0");
          landingPulse.setAttribute("opacity", "0");
        }
      };

      requestAnimationFrame(pulseStep);
    }
  };

  requestAnimationFrame(animatePlane);
}

function requiredRefsExist() {
  return Boolean(refs.countrySelect && refs.citySelect && refs.skillSelect && refs.startJourneyBtn);
}

function applyGlobeFallback() {
  const globeContainer = selectFirst("#globeContainer");
  if (!globeContainer) {
    return;
  }
  globeContainer.classList.add("globe-fallback");
  globeContainer.textContent = "";
}

export function initializeGlobalSkillSignalEngine(data) {
  try {
    const container = selectFirst("#globeContainer");
    if (!container) {
      return;
    }

    if (dashboardState.signalAnimationFrame) {
      cancelAnimationFrame(dashboardState.signalAnimationFrame);
      dashboardState.signalAnimationFrame = null;
    }
    if (dashboardState.signalResizeObserver) {
      dashboardState.signalResizeObserver.disconnect();
      dashboardState.signalResizeObserver = null;
    }

    container.classList.remove("globe-fallback");
    container.textContent = "";

    const canvas = document.createElement("canvas");
    canvas.style.width = "100%";
    canvas.style.height = "100%";
    canvas.style.display = "block";
    canvas.style.borderRadius = "14px";
    container.appendChild(canvas);

    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }

    const points = Array.isArray(data) ? data : [];
    const safeData = points.length
      ? points
      : [
        { city: "Bengaluru", signal: 80 },
        { city: "Mumbai", signal: 65 },
        { city: "San Francisco", signal: 90 },
      ];

    const rings = [];
    const vectors = [];
    let width = 0;
    let height = 0;
    let centerX = 0;
    let centerY = 0;
    let coreRadius = 18;
    let cityNodes = [];

    const resizeCanvas = () => {
      const rect = container.getBoundingClientRect();
      width = Math.max(320, Math.floor(rect.width));
      height = Math.max(240, Math.floor(rect.height));
      const ratio = window.devicePixelRatio || 1;

      canvas.width = Math.floor(width * ratio);
      canvas.height = Math.floor(height * ratio);
      context.setTransform(ratio, 0, 0, ratio, 0, 0);

      centerX = width / 2;
      centerY = height / 2;
      coreRadius = Math.max(14, Math.min(width, height) * 0.045);

      const orbitalRadius = Math.min(width, height) * 0.34;
      cityNodes = safeData.map((item, index) => {
        const angle = (-Math.PI / 2) + (index * (2 * Math.PI / safeData.length));
        return {
          city: item.city,
          signal: Number(item.signal) || 50,
          x: centerX + Math.cos(angle) * orbitalRadius,
          y: centerY + Math.sin(angle) * orbitalRadius,
          angle,
        };
      });
    };

    const createRing = (node) => {
      rings.push({
        x: node.x,
        y: node.y,
        radius: 4,
        maxRadius: 24 + (node.signal * 0.22),
        alpha: 0.55,
        speed: 0.9 + (node.signal / 120),
      });
    };

    const createVectorPulse = (node) => {
      vectors.push({
        fromX: centerX,
        fromY: centerY,
        toX: node.x,
        toY: node.y,
        t: 0,
        speed: 0.012 + (node.signal / 9000),
      });
    };

    let tick = 0;
    const draw = () => {
      context.clearRect(0, 0, width, height);

      const radial = context.createRadialGradient(centerX, centerY, 12, centerX, centerY, Math.max(width, height) * 0.65);
      radial.addColorStop(0, "rgba(59,130,246,0.18)");
      radial.addColorStop(1, "rgba(15,23,42,0)");
      context.fillStyle = radial;
      context.fillRect(0, 0, width, height);

      const corePulse = 1 + Math.sin(tick * 0.065) * 0.16;
      context.beginPath();
      context.arc(centerX, centerY, coreRadius * corePulse, 0, Math.PI * 2);
      context.fillStyle = "rgba(34, 211, 238, 0.34)";
      context.fill();

      context.beginPath();
      context.arc(centerX, centerY, coreRadius * 0.48, 0, Math.PI * 2);
      context.fillStyle = "rgba(96, 165, 250, 0.95)";
      context.fill();

      cityNodes.forEach((node, index) => {
        if (tick % (28 + index * 6) === 0) {
          createRing(node);
        }
        if (tick % (50 + index * 9) === 0) {
          createVectorPulse(node);
        }
      });

      for (let index = rings.length - 1; index >= 0; index -= 1) {
        const ring = rings[index];
        ring.radius += ring.speed;
        ring.alpha -= 0.012;

        context.beginPath();
        context.arc(ring.x, ring.y, ring.radius, 0, Math.PI * 2);
        context.strokeStyle = `rgba(34, 211, 238, ${Math.max(ring.alpha, 0)})`;
        context.lineWidth = 1.4;
        context.stroke();

        if (ring.radius > ring.maxRadius || ring.alpha <= 0) {
          rings.splice(index, 1);
        }
      }

      for (let index = vectors.length - 1; index >= 0; index -= 1) {
        const vector = vectors[index];
        vector.t += vector.speed;
        const t = Math.min(vector.t, 1);
        const x = vector.fromX + (vector.toX - vector.fromX) * t;
        const y = vector.fromY + (vector.toY - vector.fromY) * t;

        context.beginPath();
        context.moveTo(vector.fromX, vector.fromY);
        context.lineTo(x, y);
        context.strokeStyle = "rgba(96, 165, 250, 0.28)";
        context.lineWidth = 1;
        context.stroke();

        context.beginPath();
        context.arc(x, y, 2.4, 0, Math.PI * 2);
        context.fillStyle = "rgba(147, 197, 253, 0.95)";
        context.fill();

        if (vector.t >= 1) {
          vectors.splice(index, 1);
        }
      }

      cityNodes.forEach((node) => {
        context.beginPath();
        context.arc(node.x, node.y, 4 + (node.signal / 55), 0, Math.PI * 2);
        context.fillStyle = "rgba(56, 189, 248, 0.95)";
        context.fill();

        context.fillStyle = "rgba(219, 231, 255, 0.9)";
        context.font = "12px Inter, sans-serif";
        context.textAlign = "center";
        context.fillText(node.city, node.x, node.y - 14);
      });

      tick += 1;
      dashboardState.signalAnimationFrame = requestAnimationFrame(draw);
    };

    resizeCanvas();
    draw();

    dashboardState.signalResizeObserver = new ResizeObserver(() => {
      resizeCanvas();
    });
    dashboardState.signalResizeObserver.observe(container);
  } catch (error) {
    console.error("Visualization error:", error);
    applyGlobeFallback();
  }
}

function updateGlobeFromSelection(overrides = {}) {
  const payload = getSelectedPayload();
  const selectedCountry = overrides.country || payload.country || "India";
  const selectedCity = overrides.city || payload.city || "Bengaluru";
  const cachedCity = dashboardState.cityDetailsByCountry?.[selectedCountry]?.find((entry) => entry.city === selectedCity);
  const fallback = cityCoordinateFallback[selectedCity] || { latitude: 12.9716, longitude: 77.5946, tech_index: 70 };

  updateGlobeWithCity({
    country: selectedCountry,
    city: selectedCity,
    latitude: Number(overrides.latitude ?? cachedCity?.latitude ?? fallback.latitude),
    longitude: Number(overrides.longitude ?? cachedCity?.longitude ?? fallback.longitude),
    tech_index: Number(overrides.tech_index ?? cachedCity?.tech_index ?? fallback.tech_index),
  });
}

async function ensureCityDetailsForCountry(country, forceRefresh = false) {
  if (!country) {
    return [];
  }
  if (!forceRefresh && Array.isArray(dashboardState.cityDetailsByCountry[country])) {
    return dashboardState.cityDetailsByCountry[country];
  }

  try {
    const response = await getCities(country);
    const cities = Array.isArray(response?.cities) ? response.cities : [];
    dashboardState.cityDetailsByCountry[country] = cities;
    return cities;
  } catch (error) {
    console.error("Visualization error:", error);
    dashboardState.cityDetailsByCountry[country] = [];
    return [];
  }
}

async function updateGlobeFromApiCity(country, city, forceRefresh = false) {
  const cities = await ensureCityDetailsForCountry(country, forceRefresh);
  const cityData = cities.find((entry) => entry.city === city);

  if (cityData) {
    updateGlobeWithCity(cityData);
    return;
  }

  updateGlobeFromSelection({ country, city });
}

function clearAndPopulateSelect(selectElement, values, placeholder) {
  if (!selectElement) {
    return;
  }

  selectElement.textContent = "";

  const placeholderOption = document.createElement("option");
  placeholderOption.value = "";
  placeholderOption.textContent = placeholder;
  selectElement.appendChild(placeholderOption);

  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = String(value);
    option.textContent = String(value);
    selectElement.appendChild(option);
  });
}

function getSelectedPayload() {
  return {
    country: refs.countrySelect?.value || "",
    city: refs.citySelect?.value || "",
    skill: refs.skillSelect?.value || "",
    experience: refs.experienceSelect?.value || "Mid",
    timeHorizon: refs.timeHorizonSelect?.value || "1y",
  };
}

function buildMockAnalytics(payload) {
  return {
    country: payload.country || "India",
    city: payload.city || "Bengaluru",
    skill: payload.skill || "Python",
    half_life: 4.2,
    trend: "Stable",
    salary: "$95k-$125k",
    demand: [58, 62, 65, 69, 73, 78],
    timeline: fallbackTimeline,
    stability_score: 73,
    volatility_index: 2.8,
    forecast_projection: {
      outlook: "Positive",
      slope: 2.0,
    },
    upgrade_path: ["Core Engineering", "Cloud + Data", "AI Integration"],
  };
}

export async function getRegions() {
  let regions;
  try {
    regions = await fetchRegions();
  } catch (error) {
    console.error("Visualization error:", error);
    regions = {
      countries: ["India", "United States"],
      region_map: {
        India: { Bengaluru: ["Python", "Machine Learning"], Hyderabad: ["Python", "Data Engineering"] },
        "United States": { "New York": ["Python", "Cloud Architecture"], Seattle: ["Python", "DevOps"] },
      },
      experience_levels: ["Junior", "Mid", "Senior"],
    };
  }

  dashboardState.regionMap = regions?.region_map || {};

  const countries = Array.isArray(regions?.countries) ? regions.countries : Object.keys(dashboardState.regionMap);
  clearAndPopulateSelect(refs.countrySelect, countries, "Select Country");
  clearAndPopulateSelect(refs.experienceSelect, regions?.experience_levels || ["Junior", "Mid", "Senior"], "Experience");

  if (countries.length > 0) {
    refs.countrySelect.value = countries[0];
    populateCitiesForCountry(countries[0]);
    await ensureCityDetailsForCountry(countries[0]);
  }

  setupMigrationSelectors(getSelectedPayload());
}

function populateCitiesForCountry(country) {
  const cityMap = dashboardState.regionMap[country] || {};
  const cities = Object.keys(cityMap);
  clearAndPopulateSelect(refs.citySelect, cities, "Select City");

  if (cities.length > 0) {
    refs.citySelect.value = cities[0];
    populateSkillsForCity(country, cities[0]);
  }
}

function populateSkillsForCity(country, city) {
  const skills = dashboardState.regionMap[country]?.[city] || [];
  clearAndPopulateSelect(refs.skillSelect, skills, "Select Skill");
  if (skills.length > 0) {
    refs.skillSelect.value = skills[0];
  }
}

function populateMigrationCitySelect(countryValue, citySelect) {
  if (!citySelect) {
    return;
  }

  const cityMap = dashboardState.regionMap[countryValue] || {};
  const cityNames = Object.keys(cityMap);
  clearAndPopulateSelect(citySelect, cityNames, "Select City");
  if (cityNames.length > 0) {
    citySelect.value = cityNames[0];
  }
}

function setupMigrationSelectors(payload = getSelectedPayload()) {
  if (!refs.migrationFromCountry || !refs.migrationToCountry || !refs.migrationFromCity || !refs.migrationToCity) {
    return;
  }

  const countries = Object.keys(dashboardState.regionMap || {});
  clearAndPopulateSelect(refs.migrationFromCountry, countries, "Select Country");
  clearAndPopulateSelect(refs.migrationToCountry, countries, "Select Country");

  const fromCountry = payload.country || countries[0] || "";
  const toCountry = countries.find((country) => country !== fromCountry) || countries[0] || "";
  refs.migrationFromCountry.value = fromCountry;
  refs.migrationToCountry.value = toCountry;

  populateMigrationCitySelect(fromCountry, refs.migrationFromCity);
  populateMigrationCitySelect(toCountry, refs.migrationToCity);

  if (payload.city && refs.migrationFromCity.querySelector(`option[value="${payload.city}"]`)) {
    refs.migrationFromCity.value = payload.city;
  }
}

function bindMigrationSelectors() {
  const controls = [refs.migrationFromCountry, refs.migrationFromCity, refs.migrationToCountry, refs.migrationToCity];
  if (controls.some((control) => !control)) {
    return;
  }

  if (refs.migrationFromCountry.dataset.bound === "true") {
    return;
  }

  refs.migrationFromCountry.addEventListener("change", () => {
    populateMigrationCitySelect(refs.migrationFromCountry.value, refs.migrationFromCity);
    initializeMigrationVisualization(getSelectedPayload(), dashboardState.analytics || buildMockAnalytics(getSelectedPayload()));
  });

  refs.migrationToCountry.addEventListener("change", () => {
    populateMigrationCitySelect(refs.migrationToCountry.value, refs.migrationToCity);
    initializeMigrationVisualization(getSelectedPayload(), dashboardState.analytics || buildMockAnalytics(getSelectedPayload()));
  });

  refs.migrationFromCity.addEventListener("change", () => {
    initializeMigrationVisualization(getSelectedPayload(), dashboardState.analytics || buildMockAnalytics(getSelectedPayload()));
  });

  refs.migrationToCity.addEventListener("change", () => {
    initializeMigrationVisualization(getSelectedPayload(), dashboardState.analytics || buildMockAnalytics(getSelectedPayload()));
  });

  refs.migrationFromCountry.dataset.bound = "true";
}

function bindDropdownLogic() {
  refs.countrySelect.addEventListener("change", async () => {
    populateCitiesForCountry(refs.countrySelect.value);
    initializeMigrationVisualization(getSelectedPayload(), dashboardState.analytics || buildMockAnalytics(getSelectedPayload()));
    await ensureCityDetailsForCountry(refs.countrySelect.value);
    await updateGlobeFromApiCity(refs.countrySelect.value, refs.citySelect.value);
  });

  refs.citySelect.addEventListener("change", async () => {
    populateSkillsForCity(refs.countrySelect.value, refs.citySelect.value);
    initializeMigrationVisualization(getSelectedPayload(), dashboardState.analytics || buildMockAnalytics(getSelectedPayload()));
    await updateGlobeFromApiCity(refs.countrySelect.value, refs.citySelect.value, true);
  });
}

function buildChartGradient(context) {
  const gradient = context.createLinearGradient(0, 0, 0, 280);
  gradient.addColorStop(0, "rgba(59, 130, 246, 0.55)");
  gradient.addColorStop(1, "rgba(59, 130, 246, 0.03)");
  return gradient;
}

function animateCounter(element, target, suffix = "") {
  if (!element) {
    return;
  }

  const safeTarget = Math.max(0, Number(target) || 0);
  const duration = 1200;
  const start = performance.now();

  const step = (now) => {
    const progress = Math.min(1, (now - start) / duration);
    const value = Math.floor(safeTarget * (1 - Math.pow(1 - progress, 3)));
    element.textContent = `${value}${suffix}`;
    if (progress < 1) {
      requestAnimationFrame(step);
    }
  };

  requestAnimationFrame(step);
}

function renderGlobalSummaryCounters() {
  if (dashboardState.summaryCountersAnimated) {
    return;
  }
  animateCounter(selectFirst("#totalCountriesCount"), 120);
  animateCounter(selectFirst("#totalCitiesCount"), 2400, "+");
  animateCounter(selectFirst("#totalSkillsCount"), 20, "+");
  animateCounter(selectFirst("#aiConfidenceCount"), 87, "%");
  dashboardState.summaryCountersAnimated = true;
}

function animateValueWithRaf(onFrame, target, duration = 1500) {
  const safeTarget = Number(target) || 0;
  const startTime = performance.now();

  const step = (now) => {
    const progress = Math.min(1, (now - startTime) / duration);
    const eased = 1 - Math.pow(1 - progress, 3);
    onFrame(safeTarget * eased, progress);
    if (progress < 1) {
      requestAnimationFrame(step);
    }
  };

  requestAnimationFrame(step);
}

function parseSalaryRange(salaryText) {
  const matches = String(salaryText || "").match(/\d+(?:\.\d+)?/g);
  if (!matches || matches.length < 2) {
    return null;
  }

  const low = Number(matches[0]);
  const high = Number(matches[1]);
  if (!Number.isFinite(low) || !Number.isFinite(high)) {
    return null;
  }

  const hasK = /k/i.test(String(salaryText || ""));
  return { low, high, hasK };
}

function setSalaryRangeValue(salaryText, shouldAnimate) {
  if (!refs.salaryRange) {
    return;
  }

  const parsed = parseSalaryRange(salaryText);
  if (!parsed) {
    refs.salaryRange.textContent = salaryText || "--";
    return;
  }

  if (!shouldAnimate) {
    refs.salaryRange.textContent = `$${Math.round(parsed.low)}${parsed.hasK ? "k" : ""}-$${Math.round(parsed.high)}${parsed.hasK ? "k" : ""}`;
    return;
  }

  animateValueWithRaf((value) => {
    refs.salaryRange.textContent = `$${Math.round(value)}${parsed.hasK ? "k" : ""}-$${Math.round(parsed.high)}${parsed.hasK ? "k" : ""}`;
  }, parsed.low, 1500);
}

function renderPremiumAnimatedCounters(data) {
  const demandSeries = Array.isArray(data?.demand) ? data.demand : [];
  const demandIndex = Math.max(0, Math.round(Number(demandSeries[demandSeries.length - 1] ?? 68)));
  const previousDemand = Math.max(1, Math.round(Number(demandSeries[demandSeries.length - 2] ?? demandIndex - 4)));
  const growthPercent = Math.max(0, Math.round(((demandIndex - previousDemand) / previousDemand) * 100));
  const volatilityIndex = Number(data?.volatility_index ?? 2.8);
  const normalizedVolatility = Math.max(0, Math.min(100, Math.round((volatilityIndex / 5) * 100)));
  const automationRisk = Math.max(8, Math.min(92, Math.round(22 + normalizedVolatility * 0.46)));
  const careerScore = Math.max(0, Math.min(100, Math.round(Number(data?.stability_score ?? 73))));
  const globalRank = Math.max(1, Math.min(50, Math.round((130 - demandIndex) / 9)));
  const shouldAnimate = !dashboardState.premiumCountersAnimated;

  if (refs.demandIndexValue) {
    if (shouldAnimate) {
      animateValueWithRaf((value) => {
        refs.demandIndexValue.textContent = `${Math.round(value)}`;
      }, demandIndex, 1500);
    } else {
      refs.demandIndexValue.textContent = `${demandIndex}`;
    }
  }

  if (refs.insightSalaryGrowth) {
    if (shouldAnimate) {
      animateValueWithRaf((value) => {
        refs.insightSalaryGrowth.textContent = `+${Math.round(value)}%`;
      }, growthPercent, 1500);
    } else {
      refs.insightSalaryGrowth.textContent = `+${growthPercent}%`;
    }
  }

  if (refs.automationRiskValue) {
    if (shouldAnimate) {
      animateValueWithRaf((value) => {
        refs.automationRiskValue.textContent = `${Math.round(value)}%`;
      }, automationRisk, 1500);
    } else {
      refs.automationRiskValue.textContent = `${automationRisk}%`;
    }
  }

  if (refs.careerScoreValue) {
    if (shouldAnimate) {
      animateValueWithRaf((value) => {
        refs.careerScoreValue.textContent = `${Math.round(value)}`;
      }, careerScore, 1500);
    } else {
      refs.careerScoreValue.textContent = `${careerScore}`;
    }
  }

  if (refs.globalRankValue) {
    if (shouldAnimate) {
      animateValueWithRaf((value) => {
        refs.globalRankValue.textContent = `${Math.max(1, Math.round(value))}`;
      }, globalRank, 1500);
    } else {
      refs.globalRankValue.textContent = `${globalRank}`;
    }
  }

  setSalaryRangeValue(data?.salary || "--", shouldAnimate);
  dashboardState.premiumCountersAnimated = true;
}

function initializeStarfieldBackground() {
  if (dashboardState.starfieldInitialized) {
    return;
  }

  const canvas = document.getElementById("starfieldCanvas");
  if (!(canvas instanceof HTMLCanvasElement)) {
    return;
  }

  const ctx = canvas.getContext("2d", { alpha: true });
  if (!ctx) {
    return;
  }

  const particles = [];
  const maxParticles = 60;
  let width = 0;
  let height = 0;

  const buildParticle = () => ({
    x: Math.random() * width,
    y: Math.random() * height,
    radius: 0.55 + Math.random() * 1.25,
    vx: 0.03 + Math.random() * 0.08,
    vy: 0.01 + Math.random() * 0.04,
    alpha: 0.15 + Math.random() * 0.1,
  });

  const resize = () => {
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.max(1, Math.floor(width * dpr));
    canvas.height = Math.max(1, Math.floor(height * dpr));
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const targetCount = Math.min(maxParticles, Math.max(24, Math.floor((width * height) / 36000)));
    if (particles.length > targetCount) {
      particles.length = targetCount;
    }
    while (particles.length < targetCount) {
      particles.push(buildParticle());
    }
  };

  const draw = () => {
    if (!dashboardState.starfieldActive) {
      return;
    }

    ctx.clearRect(0, 0, width, height);
    for (let index = 0; index < particles.length; index += 1) {
      const particle = particles[index];
      particle.x += particle.vx;
      particle.y += particle.vy;

      if (particle.x > width + 3) {
        particle.x = -3;
      }
      if (particle.y > height + 3) {
        particle.y = -3;
      }

      ctx.beginPath();
      ctx.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(191, 219, 254, ${particle.alpha})`;
      ctx.fill();
    }

    dashboardState.starfieldAnimationFrame = requestAnimationFrame(draw);
  };

  const start = () => {
    if (dashboardState.starfieldActive || document.hidden) {
      return;
    }
    dashboardState.starfieldActive = true;
    draw();
  };

  const stop = () => {
    dashboardState.starfieldActive = false;
    if (dashboardState.starfieldAnimationFrame) {
      cancelAnimationFrame(dashboardState.starfieldAnimationFrame);
      dashboardState.starfieldAnimationFrame = null;
    }
  };

  window.addEventListener("resize", resize, { passive: true });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      stop();
    } else {
      start();
    }
  });

  resize();
  start();
  dashboardState.starfieldInitialized = true;
}

function buildForecastValues(values) {
  const base = Array.isArray(values) && values.length ? values : [56, 60, 64, 68, 71];
  const series = base.slice(0, 5);
  while (series.length < 5) {
    const lastValue = series[series.length - 1] || 60;
    series.push(lastValue + 3);
  }
  return series;
}

function renderDemandChart(data) {
  if (!refs.demandChart || typeof Chart === "undefined") {
    return;
  }

  const ctx = refs.demandChart.getContext("2d");
  if (!ctx) {
    return;
  }

  if (dashboardState.chartInstance) {
    dashboardState.chartInstance.destroy();
  }

  const labels = Array.isArray(data.timeline) && data.timeline.length ? data.timeline : fallbackTimeline;
  const values = Array.isArray(data.demand) && data.demand.length ? data.demand : [55, 60, 64, 68, 73, 77];

  dashboardState.chartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: `${data.skill || "Skill"} demand index`,
          data: values,
          borderColor: "#7eb0ff",
          backgroundColor: buildChartGradient(ctx),
          fill: true,
          tension: 0.35,
          pointRadius: 4,
          pointHoverRadius: 6,
          pointBackgroundColor: "#c9ddff",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
    },
  });
}

function renderForecastTrendChart(data) {
  if (!refs.forecastTrendChart || typeof Chart === "undefined") {
    return;
  }

  const ctx = refs.forecastTrendChart.getContext("2d");
  if (!ctx) {
    return;
  }

  if (dashboardState.forecastChartInstance) {
    dashboardState.forecastChartInstance.destroy();
  }

  dashboardState.forecastChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: ["Y1", "Y2", "Y3", "Y4", "Y5"],
      datasets: [
        {
          label: "5-Year Forecast",
          data: buildForecastValues(data?.demand),
          borderColor: "#38bdf8",
          backgroundColor: "rgba(56, 189, 248, 0.12)",
          fill: true,
          tension: 0.34,
          pointRadius: 3,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 900,
      },
      scales: {
        y: {
          ticks: {
            color: "#bfd8ff",
          },
          grid: {
            color: "rgba(148, 183, 255, 0.14)",
          },
        },
        x: {
          ticks: {
            color: "#bfd8ff",
          },
          grid: {
            color: "rgba(148, 183, 255, 0.08)",
          },
        },
      },
      plugins: {
        legend: {
          labels: {
            color: "#d8e7ff",
          },
        },
      },
    },
  });
}

function renderSkillIntelligence(data) {
  const skillName = data?.skill || "AI";
  const cityName = data?.city || "Selected City";
  const rankBadge = selectFirst("#globalRankBadge");
  const rankValue = selectFirst("#globalRankValue");
  const volatilityFill = selectFirst("#volatilityMeterFill");
  const volatilityLabel = selectFirst("#volatilityLabel");
  const automationRisk = selectFirst("#automationRiskValue");

  const volatilityIndex = Number(data?.volatility_index ?? 2.8);
  const normalizedVolatility = Math.max(0, Math.min(100, Math.round((volatilityIndex / 5) * 100)));

  let volatilityState = "Stable";
  if (normalizedVolatility >= 68) {
    volatilityState = "Disruptive";
  } else if (normalizedVolatility >= 36) {
    volatilityState = "Transforming";
  }

  const automationRiskValue = Math.max(8, Math.min(92, Math.round(22 + normalizedVolatility * 0.46)));

  if (rankBadge) {
    rankBadge.setAttribute("title", `${skillName} hiring rank in ${cityName}`);
  }
  if (rankValue) {
    rankValue.textContent = `${Math.max(1, Math.min(15, Math.round((100 - normalizedVolatility) / 8)))}`;
  }
  if (volatilityFill) {
    volatilityFill.style.width = `${normalizedVolatility}%`;
  }
  if (volatilityLabel) {
    volatilityLabel.textContent = volatilityState;
  }
  if (automationRisk) {
    automationRisk.textContent = `${automationRiskValue}%`;
  }

  const currentSkillStep = selectFirst("#currentSkillStep");
  const nextSkillStep = selectFirst("#nextSkillStep");
  const advancedSkillStep = selectFirst("#advancedSkillStep");
  if (currentSkillStep) {
    currentSkillStep.textContent = skillName;
  }
  if (nextSkillStep) {
    nextSkillStep.textContent = (data?.upgrade_path?.[1]) || "Data Engineering";
  }
  if (advancedSkillStep) {
    advancedSkillStep.textContent = (data?.upgrade_path?.[2]) || "AI Architecture";
  }
}

function renderStrategicInsightPanel(data) {
  const demandSeries = Array.isArray(data?.demand) ? data.demand : [];
  const latestDemand = Number(demandSeries[demandSeries.length - 1] || 68);
  const previousDemand = Number(demandSeries[demandSeries.length - 2] || latestDemand - 4);
  const momentum = Math.max(0, Math.min(100, Math.round((latestDemand + (latestDemand - previousDemand) * 2) * 0.9)));
  const salaryGrowth = Math.max(4, Math.min(35, Math.round((latestDemand - 52) * 0.4)));
  const automationRisk = Math.max(10, Math.min(85, Math.round(30 + Number(data?.volatility_index || 2.5) * 8)));
  const confidence = Math.max(50, Math.min(98, 100 - automationRisk + 18));

  if (refs.insightGlobalRank) {
    refs.insightGlobalRank.textContent = `#${Math.max(1, Math.round((130 - latestDemand) / 9))} Global`;
  }
  if (refs.insightMomentum) {
    refs.insightMomentum.textContent = `${momentum} / 100`;
  }
  if (refs.insightSalaryGrowth) {
    refs.insightSalaryGrowth.textContent = `+${salaryGrowth}%`;
  }
  if (refs.insightAutomationRisk) {
    refs.insightAutomationRisk.textContent = `${automationRisk}%`;
  }
  if (refs.insightTopCompanies) {
    refs.insightTopCompanies.textContent = "Google • Amazon • Microsoft";
  }
  if (refs.insightConfidence) {
    refs.insightConfidence.textContent = `${confidence} / 100`;
  }
}

function renderAiRecommendationPanel(data) {
  const skillPath = Array.isArray(data?.upgrade_path) && data.upgrade_path.length
    ? data.upgrade_path
    : ["Data Engineering", "MLOps", "AI Architecture"];

  if (refs.aiRecommendedSkill) {
    refs.aiRecommendedSkill.textContent = skillPath[1] || skillPath[0] || "Data Engineering";
  }

  const riskReward = Math.max(24, Math.min(92, Math.round(62 + Number(data?.forecast_projection?.slope || 0) * 8)));
  if (refs.aiRiskRewardFill) {
    refs.aiRiskRewardFill.style.width = `${riskReward}%`;
  }
  if (refs.aiRiskRewardLabel) {
    refs.aiRiskRewardLabel.textContent = riskReward >= 70 ? "High Reward Window" : riskReward >= 50 ? "Balanced-High Reward" : "Cautious Growth";
  }

  if (refs.aiCareerTimeline) {
    refs.aiCareerTimeline.innerHTML = "";
    const timelineEntries = [
      `Year 1: Strengthen ${skillPath[0] || "core engineering"}`,
      `Year 2: Deliver ${skillPath[1] || "AI-enabled"} production modules`,
      `Year 3: Lead ${skillPath[2] || "enterprise AI"} architecture initiatives`,
    ];

    timelineEntries.forEach((entry) => {
      const li = document.createElement("li");
      li.textContent = entry;
      refs.aiCareerTimeline.appendChild(li);
    });
  }

  if (refs.aiMigrationCities) {
    refs.aiMigrationCities.textContent = "Singapore • London • Toronto";
  }
}

function renderStabilityRadar(data) {
  const demand = Math.max(0, Math.min(100, Math.round(Number(data?.demand_index ?? data?.market_demand ?? 82))));
  const growth = Number(data?.forecast_projection?.slope ?? data?.growth_rate ?? 12);
  const growthPercent = Math.max(0, Math.round(Math.abs(growth) * 10));
  const longevityYears = Number(data?.half_life ?? 5.2);
  const longevityText = `${Math.max(1, Math.round(longevityYears))}+ Years`;
  const stabilityIndex = Math.max(0, Math.min(100, Math.round(Number(data?.stability_score ?? 84))));
  const riskScore = Math.max(0, Math.min(100, Math.round(Number(data?.automation_risk ?? 42))));

  const skillProfile = {
    country: data?.country || refs.countrySelect?.value || "Germany",
    region: String(data?.region || "Europe"),
    marketTier: demand >= 80 ? "Tier 1 Market" : demand >= 65 ? "Tier 2 Growth Market" : "Emerging Market",
    topIndustries: Array.isArray(data?.top_companies) && data.top_companies.length
      ? data.top_companies.slice(0, 3).join(" • ")
      : "Fintech • Automotive AI • Industrial Cloud",
    demand,
    growth: growthPercent,
    longevity: longevityText,
    risk: riskScore >= 65 ? "High" : riskScore >= 40 ? "Moderate" : "Low",
    stabilityIndex,
  };

  if (refs.radarCountry) refs.radarCountry.textContent = skillProfile.country;
  if (refs.radarRegion) refs.radarRegion.textContent = skillProfile.region;
  if (refs.radarMarketTier) refs.radarMarketTier.textContent = skillProfile.marketTier;
  if (refs.radarTopIndustries) refs.radarTopIndustries.textContent = skillProfile.topIndustries;
  if (refs.stabilityScoreValue) refs.stabilityScoreValue.textContent = String(skillProfile.stabilityIndex);
  if (refs.radarDemandLevel) refs.radarDemandLevel.textContent = String(skillProfile.demand);
  if (refs.radarGrowthRate) refs.radarGrowthRate.textContent = `+${skillProfile.growth}%`;
  if (refs.radarLongevity) refs.radarLongevity.textContent = skillProfile.longevity;
  if (refs.radarRiskLevel) refs.radarRiskLevel.textContent = skillProfile.risk;
  if (refs.radarCareerBadge) refs.radarCareerBadge.textContent = `${skillProfile.stabilityIndex} / 100`;

  const radarPayload = {
    ...data,
    radar_scores: [
      skillProfile.stabilityIndex,
      skillProfile.demand,
      Math.max(40, Math.min(100, 60 + skillProfile.growth)),
      Math.max(30, Math.min(100, Math.round(longevityYears * 14))),
      Math.max(20, Math.min(100, 100 - riskScore)),
    ],
  };

  dashboardState.radarInstance = renderStabilityRadarChart(refs.stabilityRadar, radarPayload, dashboardState.radarInstance);
}

function renderCareerPath(data) {
  const cards = Array.from(document.querySelectorAll(".panel--career-path .upgrade-path-card"));
  const path = Array.isArray(data.upgrade_path) && data.upgrade_path.length
    ? data.upgrade_path
    : ["Core mastery", "Applied AI", "Platform strategy"];

  cards.forEach((card, index) => {
    const list = card.querySelector(".upgrade-path-list");
    if (!list) {
      return;
    }

    list.textContent = "";
    path.slice(index, index + 3).forEach((item) => {
      const li = document.createElement("li");
      li.textContent = item;
      list.appendChild(li);
    });
  });
}

function animateMetricValue(element, target, suffix = "", includeSign = false) {
  if (!element) {
    return;
  }

  const safeTarget = Number(target) || 0;
  const duration = 900;
  const start = performance.now();

  const tick = (now) => {
    const progress = Math.min(1, (now - start) / duration);
    const value = safeTarget * (1 - Math.pow(1 - progress, 3));
    const rounded = Math.round(value);
    const sign = includeSign && rounded > 0 ? "+" : "";
    element.textContent = `${sign}${rounded}${suffix}`;
    if (progress < 1) {
      requestAnimationFrame(tick);
    }
  };

  requestAnimationFrame(tick);
}

function initializeMigrationVisualization(payload, analytics) {
  if (!refs.migrationMap) {
    return;
  }

  const fromCountry = refs.migrationFromCountry?.value || payload.country;
  const fromCity = refs.migrationFromCity?.value || payload.city || "Bengaluru";
  const toCountry = refs.migrationToCountry?.value || fromCountry;
  const toCity = refs.migrationToCity?.value || "Hyderabad";

  const deltaSeed = (fromCity.length * 7 + toCity.length * 11 + fromCountry.length * 3 + toCountry.length * 2) % 27;
  const demandDelta = deltaSeed - 10;
  const salaryAdvantage = demandDelta + 6;
  const competitionDiff = Math.max(4, 28 - demandDelta);
  const opportunityScore = Math.max(12, Math.min(98, 70 + demandDelta));
  const trendLabel = demandDelta > 5 ? "Increasing" : demandDelta < -5 ? "Declining" : "Stable";
  const flowClass = demandDelta > 5 ? "flow-positive" : demandDelta < -5 ? "flow-decline" : "flow-neutral";

  const pathD = "M 42 162 C 140 52 296 72 402 156";

  refs.migrationMap.innerHTML = `
    <svg class="migration-flow-svg" viewBox="0 0 440 220" preserveAspectRatio="none">
      <path class="migration-flow-path ${flowClass} migration-flow-hotspot" d="${pathD}"></path>
      <circle class="migration-flow-particle" r="4" style="offset-path:path('${pathD}');"></circle>
      <circle class="migration-flow-particle delay-1" r="3.2" style="offset-path:path('${pathD}');"></circle>
      <circle class="migration-flow-particle delay-2" r="3.6" style="offset-path:path('${pathD}');"></circle>
      <circle cx="42" cy="162" r="6" fill="#93c5fd"></circle>
      <circle cx="402" cy="156" r="6" fill="#67e8f9"></circle>
      <text x="26" y="182" fill="#dbeafe" font-size="11">${fromCity}</text>
      <text x="370" y="178" fill="#dbeafe" font-size="11">${toCity}</text>
    </svg>
  `;

  animateMetricValue(refs.migrationScoreValue, opportunityScore);
  animateMetricValue(refs.migrationDemandDelta, demandDelta, "%", true);
  animateMetricValue(refs.migrationSalaryAdvantage, salaryAdvantage, "%", true);
  animateMetricValue(refs.migrationCompetitionDiff, competitionDiff);
  if (refs.migrationFlowTrend) {
    refs.migrationFlowTrend.textContent = trendLabel;
  }

  const hotspot = refs.migrationMap.querySelector(".migration-flow-hotspot");
  const particles = Array.from(refs.migrationMap.querySelectorAll(".migration-flow-particle"));
  if (hotspot && refs.migrationFlowTooltip) {
    hotspot.addEventListener("mouseenter", () => {
      refs.migrationFlowTooltip.hidden = false;
    });
    hotspot.addEventListener("mousemove", (event) => {
      const hostRect = refs.migrationMap.getBoundingClientRect();
      refs.migrationFlowTooltip.style.left = `${Math.min(hostRect.width - 260, Math.max(8, event.clientX - hostRect.left + 10))}px`;
      refs.migrationFlowTooltip.style.top = `${Math.min(hostRect.height - 100, Math.max(8, event.clientY - hostRect.top + 10))}px`;
      refs.migrationFlowTooltip.style.right = "auto";
    });
    hotspot.addEventListener("mouseleave", () => {
      refs.migrationFlowTooltip.hidden = true;
      refs.migrationFlowTooltip.style.right = "10px";
      refs.migrationFlowTooltip.style.left = "auto";
      refs.migrationFlowTooltip.style.top = "10px";
    });
  }

  if (migrationFlowInterval) {
    window.clearInterval(migrationFlowInterval);
    migrationFlowInterval = null;
  }

  if (hotspot && particles.length) {
    const pathLength = hotspot.getTotalLength();
    let elapsed = 0;
    migrationFlowInterval = window.setInterval(() => {
      if (!refs.migrationMap || !document.body.contains(refs.migrationMap)) {
        window.clearInterval(migrationFlowInterval);
        migrationFlowInterval = null;
        return;
      }

      elapsed += 0.015;
      particles.forEach((particle, index) => {
        const flowPosition = ((elapsed + index * 0.22) % 1) * pathLength;
        const point = hotspot.getPointAtLength(flowPosition);
        particle.setAttribute("cx", point.x.toFixed(2));
        particle.setAttribute("cy", point.y.toFixed(2));
        const pulse = 0.65 + 0.35 * Math.sin((elapsed + index) * 7.5);
        particle.setAttribute("opacity", pulse.toFixed(2));
      });
    }, 34);
  }

}

async function refreshCompareModule(payload) {
  try {
    const cityMap = dashboardState.regionMap[payload.country] || {};
    const compareCity = Object.keys(cityMap).find((city) => city !== payload.city);

    if (!compareCity) {
      return;
    }

    const result = await compareCities({
      country_a: payload.country,
      city_a: payload.city,
      country_b: payload.country,
      city_b: compareCity,
      skill: payload.skill,
      experience: payload.experience,
      time_horizon: payload.timeHorizon,
    });

    const cards = Array.from(document.querySelectorAll(".region-comparison-card"));
    [result?.city_a, result?.city_b].forEach((cityInfo, index) => {
      const card = cards[index];
      if (!card || !cityInfo) {
        return;
      }
      const cityLabel = card.querySelector(".region-name");
      const metrics = card.querySelectorAll(".region-metric");
      if (cityLabel) {
        cityLabel.textContent = cityInfo.city;
      }
      if (metrics[0]) {
        metrics[0].textContent = `Skill Momentum: ${cityInfo.trend}`;
      }
      if (metrics[1]) {
        metrics[1].textContent = `Growth Signal: ${cityInfo.forecast_projection?.outlook || "Stable"}`;
      }
    });

    const cityA = result?.city_a;
    const cityB = result?.city_b;
    const demandA = Number((Array.isArray(cityA?.demand) ? cityA.demand[cityA.demand.length - 1] : cityA?.demand_index) ?? 68);
    const demandB = Number((Array.isArray(cityB?.demand) ? cityB.demand[cityB.demand.length - 1] : cityB?.demand_index) ?? 61);
    const demandDelta = Math.round(demandA - demandB);

    const compareCityAName = selectFirst("#compareCityAName");
    const compareCityBName = selectFirst("#compareCityBName");
    const compareDemandA = selectFirst("#compareDemandA");
    const compareDemandB = selectFirst("#compareDemandB");
    const compareSalaryA = selectFirst("#compareSalaryA");
    const compareSalaryB = selectFirst("#compareSalaryB");
    const compareCompetitionA = selectFirst("#compareCompetitionA");
    const compareCompetitionB = selectFirst("#compareCompetitionB");
    const compareOpportunityA = selectFirst("#compareOpportunityA");
    const compareOpportunityB = selectFirst("#compareOpportunityB");

    if (compareCityAName && cityA?.city) {
      compareCityAName.textContent = cityA.city;
    }
    if (compareCityBName && cityB?.city) {
      compareCityBName.textContent = cityB.city;
    }
    if (compareDemandA) {
      compareDemandA.textContent = `${demandDelta >= 0 ? "+" : ""}${demandDelta}`;
    }
    if (compareDemandB) {
      compareDemandB.textContent = `${demandDelta <= 0 ? "+" : ""}${-demandDelta}`;
    }
    if (compareSalaryA) {
      compareSalaryA.textContent = cityA?.salary || "$118k avg";
    }
    if (compareSalaryB) {
      compareSalaryB.textContent = cityB?.salary || "$102k avg";
    }
    if (compareCompetitionA) {
      compareCompetitionA.textContent = `${Math.max(12, 42 - demandDelta)} pts`;
    }
    if (compareCompetitionB) {
      compareCompetitionB.textContent = `${Math.max(12, 42 + demandDelta)} pts`;
    }
    if (compareOpportunityA) {
      compareOpportunityA.textContent = `${Math.max(50, 78 + demandDelta)} / 100`;
    }
    if (compareOpportunityB) {
      compareOpportunityB.textContent = `${Math.max(50, 78 - demandDelta)} / 100`;
    }
  } catch (error) {
    console.error("Visualization error:", error);
  }
}

async function renderReportPreview(payload) {
  const reportBlocks = Array.from(document.querySelectorAll(".panel--report .report-block"));
  if (!reportBlocks.length) {
    return;
  }

  try {
    const preview = await fetchReportPreview({
      country: payload.country,
      city: payload.city,
      skill: payload.skill,
      experience: payload.experience,
      time_horizon: payload.timeHorizon,
    });

    dashboardState.reportPreview = preview;

    const reportUser = safeStorageGet(storageKeys.userName) || "Alex Morgan";
    const generatedAt = new Date().toLocaleDateString();

    reportBlocks[0].querySelector(".report-copy").textContent = `${preview.skill} in ${preview.city} has a half-life of ${preview.halfLife} years with ${preview.marketTrend} market trend. Prepared for ${reportUser} on ${generatedAt}.`;
    const list = reportBlocks[1].querySelector(".report-list");
    list.textContent = "";
    [`Half-life: ${preview.halfLife} years`, `Market trend: ${preview.marketTrend}`, `Salary index: ${preview.salaryIndex}`].forEach((value) => {
      const li = document.createElement("li");
      li.textContent = value;
      list.appendChild(li);
    });
    reportBlocks[2].querySelector(".report-copy").textContent = (preview.recommendations || [])[0] || "Recommendation unavailable.";
    reportBlocks[3].querySelector(".report-copy").textContent = (preview.recommendations || [])[1] || "Risk guidance unavailable.";
  } catch (error) {
    console.error("Visualization error:", error);
  }
}

function renderAnalytics(data) {
  dashboardState.analytics = data;

  if (refs.halfLifeValue) {
    refs.halfLifeValue.textContent = `${data.half_life ?? "--"} years`;
  }
  if (refs.trendValue) {
    refs.trendValue.textContent = data.trend || "--";
  }
  if (refs.salaryRange) {
    refs.salaryRange.textContent = data.salary || "--";
  }
  if (refs.cityNameSlot) {
    refs.cityNameSlot.textContent = data.city || "Selected City";
  }

  renderDemandChart(data);
  renderForecastTrendChart(data);
  renderStabilityRadar(data);
  renderCareerPath(data);
  renderSkillIntelligence(data);
  renderStrategicInsightPanel(data);
  renderPremiumAnimatedCounters(data);
  renderAiRecommendationPanel(data);
  renderGlobalSummaryCounters();
  initializeMigrationVisualization(getSelectedPayload(), data);
  updateGlobeFromSelection({
    country: data.country,
    city: data.city,
    latitude: data.city_metadata?.latitude,
    longitude: data.city_metadata?.longitude,
    tech_index: data.city_metadata?.tech_index,
  });

  setAssistantContext({ country: data.country, city: data.city, skill: data.skill, analytics: data });
}

export async function getAnalytics(country, city, skill, experience = "Mid", time_horizon = "1y") {
  return fetchAnalytics(country, city, skill, experience, time_horizon);
}

async function handleStartJourney() {
  const payload = getSelectedPayload();
  if (!payload.country || !payload.city || !payload.skill) {
    return;
  }

  refs.startJourneyBtn.disabled = true;
  refs.startJourneyBtn.textContent = "Loading...";

  try {
    let data;
    try {
      data = await getAnalytics(payload.country, payload.city, payload.skill, payload.experience, payload.timeHorizon);
    } catch (error) {
      console.error("Visualization error:", error);
      data = buildMockAnalytics(payload);
    }

    renderAnalytics(data);
    await renderReportPreview(payload);
    await refreshCompareModule(payload);

    try {
      await runSimulationRefresh();
    } catch (error) {
      console.error("Visualization error:", error);
    }
  } catch (error) {
    console.error("Visualization error:", error);
  } finally {
    refs.startJourneyBtn.disabled = false;
    refs.startJourneyBtn.textContent = "Start Journey";
  }
}

async function generateReport() {
  if (!dashboardState.analytics) {
    return;
  }

  if (reportDownloading) {
    return;
  }

  const button = refs.downloadReportBtn;
  const defaultLabel = "Download Full Career Intelligence Report";
  let spinnerTimer = null;
  let spinnerIndex = 0;
  const spinnerFrames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

  reportDownloading = true;
  if (button) {
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    button.textContent = `${spinnerFrames[0]} Generating Report...`;
    spinnerTimer = window.setInterval(() => {
      spinnerIndex = (spinnerIndex + 1) % spinnerFrames.length;
      button.textContent = `${spinnerFrames[spinnerIndex]} Generating Report...`;
    }, 90);
  }

  const payload = getSelectedPayload();
  try {
    const { blob, fileName } = await downloadReport({
      country: payload.country,
      city: payload.city,
      skill: payload.skill,
      experience: payload.experience,
      time_horizon: payload.timeHorizon,
    });

    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = fileName || "career_intelligence_report.pdf";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(objectUrl);
  } catch (error) {
    console.error("Visualization error:", error);

    const analytics = dashboardState.analytics;
    const generatedDate = new Date().toLocaleString();
    const userName = safeStorageGet(storageKeys.userName) || "Alex Morgan";
    const reportHtml = `
      <html>
      <head><title>Career Intelligence Report</title></head>
      <body style="font-family:Inter,Segoe UI,sans-serif;padding:24px;color:#0f172a;line-height:1.5;">
        <h1 style="margin-bottom:4px;">Skill Half-Life Intelligence</h1>
        <p style="margin-top:0;color:#334155;">Enterprise Career Intelligence Report</p>
        <p><strong>User:</strong> ${userName}<br/><strong>Generated:</strong> ${generatedDate}</p>
        <h2>1. Executive Summary</h2><p>${analytics.skill} in ${analytics.city} shows ${analytics.trend} trend and ${analytics.half_life} year half-life.</p>
        <h2>2. Regional Market Demand</h2><p>Current salary band: ${analytics.salary}. Demand trajectory reflects regional market pressure.</p>
        <h2>3. Skill Half-Life Analysis</h2><p>Estimated half-life: ${analytics.half_life} years. Volatility index: ${analytics.volatility_index ?? "--"}.</p>
        <h2>4. 5-Year Forecast</h2><p>Forecast outlook: ${analytics.forecast_projection?.outlook || "Stable"}.</p>
        <h2>5. Risk Analysis</h2><p>Automation and market transition risks require periodic upskilling.</p>
        <h2>6. Recommended Career Path</h2><p>${(analytics.upgrade_path || []).join(" → ") || "Core Engineering → Data Engineering → AI Architecture"}</p>
        <h2>7. Migration Insights</h2><p>Compare neighboring cities for salary, demand, and opportunity spread before moving.</p>
      </body>
      </html>
    `;

    const fallbackBlob = new Blob([reportHtml], { type: "text/html" });
    const fallbackUrl = URL.createObjectURL(fallbackBlob);
    const fallbackLink = document.createElement("a");
    fallbackLink.href = fallbackUrl;
    fallbackLink.download = "career_intelligence_report.html";
    document.body.appendChild(fallbackLink);
    fallbackLink.click();
    fallbackLink.remove();
    URL.revokeObjectURL(fallbackUrl);
  } finally {
    reportDownloading = false;
    if (spinnerTimer) {
      window.clearInterval(spinnerTimer);
    }
    if (button) {
      button.disabled = false;
      button.removeAttribute("aria-busy");
      button.textContent = defaultLabel;
    }
  }
}

function bindActionHandlers() {
  refs.startJourneyBtn.addEventListener("click", handleStartJourney);
  if (refs.downloadReportBtn && refs.downloadReportBtn.dataset.bound !== "true") {
    refs.downloadReportBtn.addEventListener("click", generateReport);
    refs.downloadReportBtn.dataset.bound = "true";
  }
}

export async function initializeDashboard() {
  cacheDomReferences();

  if (!requiredRefsExist()) {
    console.error("Visualization error:", new Error("Missing required dashboard nodes"));
    return;
  }

  if (dashboardState.initialized) {
    return;
  }

  initializeDashboardControls();
  bindDropdownLogic();
  bindMigrationSelectors();
  bindActionHandlers();

  await initializeGlobe("globeContainer");
  await getRegions();
  await updateGlobeFromApiCity(refs.countrySelect.value, refs.citySelect.value);

  const payload = getSelectedPayload();
  initializeAssistant({ country: payload.country, city: payload.city, skill: payload.skill });

  await handleStartJourney();
  dashboardState.initialized = true;
}

function initializeAllVisualizations() {
  initializeStarfieldBackground();
  initializeDashboard().catch((error) => {
    console.error("Visualization error:", error);
  });
}

document.addEventListener("DOMContentLoaded", function () {
  devLog("Dashboard JS is running");
  initializeGlobeSignalAnimation();

  const btn = document.getElementById("startJourneyBtn");

  if (btn && btn.dataset.flightBound !== "true") {
    btn.addEventListener("click", function () {
      const path = document.getElementById("flightPath");
      const plane = document.getElementById("plane");

      if (!path || !plane || typeof path.getTotalLength !== "function" || typeof path.getPointAtLength !== "function") {
        return;
      }

      let length = path.getTotalLength();
      path.style.transition = "none";
      path.style.strokeDashoffset = "1000";
      path.getBoundingClientRect();
      path.style.transition = "stroke-dashoffset 2s ease";
      path.style.strokeDashoffset = "0";

      let start = null;
      const duration = 2000;

      function animate(timestamp) {
        if (!start) start = timestamp;
        const progress = timestamp - start;
        const percent = Math.min(progress / duration, 1);

        const point = path.getPointAtLength(percent * length);
        plane.setAttribute("x", point.x);
        plane.setAttribute("y", point.y);

        if (percent < 1) {
          requestAnimationFrame(animate);
        }
      }

      requestAnimationFrame(animate);
    });

    btn.dataset.flightBound = "true";
  }

  initializeAllVisualizations();
});

export { renderAnalytics };
