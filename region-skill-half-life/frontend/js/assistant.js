const assistantState = {
  conversationHistory: [],
  selectedCountry: "",
  selectedCity: "",
  selectedSkill: "",
  analytics: null,
  initialized: false,
  pendingTypingNode: null,
  isSending: false,
};

const selectors = {
  chatMessages: ["#chatMessages", "#chat-box"],
  chatInput: ["#chatInput", "#chat-input"],
  sendButton: ["#sendChatBtn", "#chat-send"],
  voiceButton: ["#voiceBtn"],
  countrySelect: ["#countrySelect", "#country-select"],
  citySelect: ["#citySelect", "#city-select"],
  skillSelect: ["#skillSelect", "#skill-select"],
};

const domRefs = {
  panelEl: null,
  chatMessagesEl: null,
  chatInputEl: null,
  sendButtonEl: null,
  voiceButtonEl: null,
  countrySelectEl: null,
  citySelectEl: null,
  skillSelectEl: null,
};

const skillKeywordMap = {
  python: ["python", "py"],
  java: ["java"],
  ai: ["ai", "artificial intelligence", "machine learning", "ml"],
  cloud: ["cloud", "aws", "azure", "gcp"],
  devops: ["devops", "kubernetes", "docker", "ci/cd", "sre"],
  data: ["data", "data engineering", "analytics", "bi", "sql"],
  cybersecurity: ["cyber", "cybersecurity", "security"],
  frontend: ["frontend", "front-end", "react", "ui"],
};

const countryKeywordMap = {
  india: ["india"],
  usa: ["usa", "us", "united states", "america"],
  germany: ["germany", "deutschland"],
  canada: ["canada"],
  singapore: ["singapore"],
  uk: ["uk", "united kingdom", "britain", "england"],
};

const skillOutlook = {
  python: { demand: "High", trend: "Growing", cities: ["Bengaluru", "Berlin", "Toronto"], recommendation: "Pair Python with Data Engineering + AI workflows." },
  java: { demand: "Medium", trend: "Stable", cities: ["Frankfurt", "Bangalore", "Chicago"], recommendation: "Strengthen cloud-native Java and platform engineering." },
  ai: { demand: "High", trend: "Growing", cities: ["San Francisco", "London", "Singapore"], recommendation: "Build production AI, evaluation, and governance skills." },
  cloud: { demand: "High", trend: "Growing", cities: ["Seattle", "Dublin", "Singapore"], recommendation: "Focus on multi-cloud architecture and FinOps." },
  devops: { demand: "High", trend: "Stable", cities: ["Toronto", "Berlin", "Hyderabad"], recommendation: "Combine DevOps with observability and security automation." },
  data: { demand: "High", trend: "Growing", cities: ["Bengaluru", "Amsterdam", "Toronto"], recommendation: "Invest in streaming, warehousing, and data quality practices." },
  cybersecurity: { demand: "High", trend: "Growing", cities: ["Tel Aviv", "Berlin", "Washington DC"], recommendation: "Add cloud security and incident response depth." },
  frontend: { demand: "Medium", trend: "Stable", cities: ["London", "New York", "Bengaluru"], recommendation: "Differentiate with performance, accessibility, and product analytics." },
};

const countryTopSkills = {
  india: { topSkills: ["AI", "Cloud", "Data Engineering"], topCities: ["Bengaluru", "Hyderabad", "Pune"] },
  usa: { topSkills: ["AI", "Cybersecurity", "Cloud"], topCities: ["San Francisco", "Seattle", "Austin"] },
  germany: { topSkills: ["Cloud", "Java", "Cybersecurity"], topCities: ["Berlin", "Munich", "Frankfurt"] },
  canada: { topSkills: ["DevOps", "Data", "AI"], topCities: ["Toronto", "Vancouver", "Montreal"] },
  singapore: { topSkills: ["AI", "Cloud", "Cybersecurity"], topCities: ["Singapore", "Jurong", "Woodlands"] },
  uk: { topSkills: ["Data", "AI", "DevOps"], topCities: ["London", "Manchester", "Cambridge"] },
};

const skillCountrySignals = {
  india: {
    ai: { demand: "High", trend: "Growing", cities: ["Bengaluru", "Hyderabad", "Gurugram"], recommendation: "Target AI product teams and MLOps-heavy roles." },
    cloud: { demand: "High", trend: "Growing", cities: ["Bengaluru", "Pune", "Chennai"], recommendation: "Build cloud architecture and reliability engineering depth." },
  },
  usa: {
    ai: { demand: "High", trend: "Growing", cities: ["San Francisco", "Seattle", "New York"], recommendation: "Prioritize GenAI productization and evaluation tooling." },
    devops: { demand: "High", trend: "Stable", cities: ["Austin", "Seattle", "Denver"], recommendation: "Lean into platform automation and security-by-default pipelines." },
  },
  germany: {
    java: { demand: "Medium", trend: "Stable", cities: ["Frankfurt", "Berlin", "Munich"], recommendation: "Position for enterprise modernization and cloud migration projects." },
    cloud: { demand: "High", trend: "Growing", cities: ["Berlin", "Munich", "Hamburg"], recommendation: "Develop Kubernetes + governance + cost optimization expertise." },
  },
  canada: {
    data: { demand: "High", trend: "Growing", cities: ["Toronto", "Vancouver", "Montreal"], recommendation: "Focus on analytics engineering and real-time data stacks." },
    ai: { demand: "High", trend: "Growing", cities: ["Toronto", "Montreal", "Waterloo"], recommendation: "Blend ML fundamentals with production deployment patterns." },
  },
};

function queryFirst(list) {
  for (const selector of list) {
    const node = document.querySelector(selector);
    if (node) {
      return node;
    }
  }
  return null;
}

function resolveDom() {
  domRefs.panelEl = document.querySelector(".panel--assistant");
  domRefs.chatMessagesEl = queryFirst(selectors.chatMessages);
  domRefs.chatInputEl = queryFirst(selectors.chatInput);
  domRefs.sendButtonEl = queryFirst(selectors.sendButton);
  domRefs.voiceButtonEl = queryFirst(selectors.voiceButton);
  domRefs.countrySelectEl = queryFirst(selectors.countrySelect);
  domRefs.citySelectEl = queryFirst(selectors.citySelect);
  domRefs.skillSelectEl = queryFirst(selectors.skillSelect);
}

function setAssistantResponding(isResponding) {
  domRefs.panelEl?.classList.toggle("is-responding", Boolean(isResponding));
}

function addRippleEffect(event) {
  const button = event.currentTarget;
  if (!(button instanceof HTMLElement)) {
    return;
  }

  button.querySelector(".ripple")?.remove();
  const rect = button.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height);
  const ripple = document.createElement("span");
  ripple.className = "ripple";
  ripple.style.width = `${size}px`;
  ripple.style.height = `${size}px`;
  ripple.style.left = `${event.clientX - rect.left - size / 2}px`;
  ripple.style.top = `${event.clientY - rect.top - size / 2}px`;
  button.appendChild(ripple);
  window.setTimeout(() => ripple.remove(), 700);
}

function normalizeSender(sender) {
  return sender === "user" ? "user" : "ai";
}

function applyAssistantPanelUI() {
  const panel = domRefs.panelEl;
  if (!panel) {
    return;
  }

  const title = panel.querySelector("#assistantPanelTitle");
  const subtitle = panel.querySelector(".panel-header .panel-subtitle");
  const assistantName = panel.querySelector(".assistant-name");
  const assistantStateLabel = panel.querySelector(".assistant-state");

  if (title) title.textContent = "Global Intelligence Assistant";
  if (subtitle) subtitle.textContent = "Analyzing regional demand and skill longevity in real time";
  if (assistantName) assistantName.textContent = "Global Intelligence Assistant";
  if (assistantStateLabel) assistantStateLabel.textContent = "Online • Global Signal Analysis";
}

function wait(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

async function requestChatResponse(message) {
  const response = await fetch("http://127.0.0.1:8000/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    throw new Error("Chat request failed");
  }

  return response.json();
}

function scrollChatToBottom() {
  if (!domRefs.chatMessagesEl) {
    return;
  }
  domRefs.chatMessagesEl.scrollTop = domRefs.chatMessagesEl.scrollHeight;
}

function createMessageNode(text, sender, className = "") {
  const role = normalizeSender(sender);
  const item = document.createElement("div");
  item.classList.add("chat-bubble", role === "user" ? "chat-bubble--user" : "chat-bubble--assistant");
  if (className) {
    item.classList.add(className);
  }

  const body = document.createElement("p");
  body.style.margin = "0";
  body.textContent = text;
  item.appendChild(body);

  return item;
}

export function addMessage(text, sender) {
  const chatRoot = domRefs.chatMessagesEl || queryFirst(selectors.chatMessages);
  if (!chatRoot) {
    return;
  }

  const role = normalizeSender(sender);
  assistantState.conversationHistory.push({
    text,
    sender: role,
    timestamp: new Date().toISOString(),
  });

  chatRoot.appendChild(createMessageNode(text, role));
  scrollChatToBottom();
}

function removeTypingIndicator() {
  assistantState.pendingTypingNode?.remove();
  assistantState.pendingTypingNode = null;
  setAssistantResponding(false);
}

function showTypingIndicator() {
  const chatRoot = domRefs.chatMessagesEl;
  if (!chatRoot) {
    return;
  }

  removeTypingIndicator();
  setAssistantResponding(true);

  const wrapper = document.createElement("div");
  wrapper.classList.add("chat-bubble", "chat-bubble--assistant", "chat-typing");

  const dotA = document.createElement("span");
  dotA.className = "typing-dot";
  const dotB = document.createElement("span");
  dotB.className = "typing-dot";
  const dotC = document.createElement("span");
  dotC.className = "typing-dot";

  const label = document.createElement("span");
  label.className = "typing-label";
  label.textContent = "Analyzing global signals...";

  wrapper.append(dotA, dotB, dotC, label);
  chatRoot.appendChild(wrapper);
  assistantState.pendingTypingNode = wrapper;
  scrollChatToBottom();
}

function detectEntities(message) {
  const lower = String(message || "").toLowerCase();

  const skills = Object.entries(skillKeywordMap)
    .filter(([, keywords]) => keywords.some((keyword) => lower.includes(keyword)))
    .map(([skill]) => skill);

  const countries = Object.entries(countryKeywordMap)
    .filter(([, keywords]) => keywords.some((keyword) => lower.includes(keyword)))
    .map(([country]) => country);

  return {
    skills: [...new Set(skills)],
    countries: [...new Set(countries)],
  };
}

function toTitle(value) {
  return String(value || "")
    .split(" ")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatStructuredReply({ heading, demand, trend, topCities, recommendation, extras = [] }) {
  const cityList = Array.isArray(topCities) && topCities.length ? topCities.join(", ") : "No strong city signal yet";
  return [
    heading,
    `📈 Demand Level: ${demand}`,
    `📊 Trend: ${trend}`,
    `🌍 Top Cities: ${cityList}`,
    `🧭 Career Recommendation: ${recommendation}`,
    ...extras,
  ].join("\n");
}

function buildSkillCountryResponse(skill, country) {
  const pair = skillCountrySignals[country]?.[skill];
  const skillGlobal = skillOutlook[skill];
  const countryProfile = countryTopSkills[country];

  const source = pair || skillGlobal || {
    demand: "Medium",
    trend: "Stable",
    cities: countryProfile?.topCities || ["Signal building"],
    recommendation: "Build depth in fundamentals and add adjacent platform skills.",
  };

  return formatStructuredReply({
    heading: `🤖 ${toTitle(skill)} in ${toTitle(country)} — Contextual Intelligence`,
    demand: source.demand,
    trend: source.trend,
    topCities: source.cities,
    recommendation: source.recommendation,
    extras: [`• Focus Window: next 12-18 months`, `• Competitive Edge: combine ${toTitle(skill)} with communication + product thinking`],
  });
}

function buildSkillOnlyResponse(skill) {
  const profile = skillOutlook[skill] || {
    demand: "Medium",
    trend: "Stable",
    cities: ["Global mixed signal"],
    recommendation: "Pair this skill with cloud and data fundamentals.",
  };

  return formatStructuredReply({
    heading: `🌐 Global Outlook — ${toTitle(skill)}`,
    demand: profile.demand,
    trend: profile.trend,
    topCities: profile.cities,
    recommendation: profile.recommendation,
    extras: ["• Best move: build one portfolio project with measurable impact"],
  });
}

function buildCountryOnlyResponse(country) {
  const profile = countryTopSkills[country] || {
    topSkills: ["Cloud", "Data", "AI"],
    topCities: ["Primary metro hubs"],
  };

  return [
    `🏳️ ${toTitle(country)} — Top Skill Signals`,
    `🔥 Top Skills: ${profile.topSkills.join(", ")}`,
    `🏙️ Top Cities: ${profile.topCities.join(", ")}`,
    "🎯 Recommendation: choose one core skill and one acceleration skill (AI/Cloud/Data) for faster market fit.",
  ].join("\n");
}

function buildIntentFallback(message) {
  const text = String(message || "").trim();
  const questionType = /best|top|which/.test(text.toLowerCase())
    ? "ranking"
    : /switch|move|change/.test(text.toLowerCase())
      ? "transition"
      : "analysis";

  if (questionType === "ranking") {
    return [
      "🧠 Smart Prompt Detected — Ranking Request",
      "• Tell me one skill and one country (example: 'AI in Canada').",
      "• I will return demand level, trend, top cities, and a career action plan.",
    ].join("\n");
  }

  if (questionType === "transition") {
    return [
      "🔄 Skill Transition Guidance",
      "• Share your current skill + target skill + country.",
      "• I’ll generate a phased migration path with market viability.",
    ].join("\n");
  }

  return [
    "📡 Context Needed for Precision",
    "• Mention at least one skill (Python, Java, AI, Cloud, DevOps, Data...) and/or one country.",
    "• I’ll convert it into a market intelligence brief instantly.",
  ].join("\n");
}

function generateResponse(message) {
  const { skills, countries } = detectEntities(message);
  const skill = skills[0] || "";
  const country = countries[0] || "";

  if (skill && country) {
    return buildSkillCountryResponse(skill, country);
  }

  if (skill) {
    return buildSkillOnlyResponse(skill);
  }

  if (country) {
    return buildCountryOnlyResponse(country);
  }

  const contextualSkill = (assistantState.selectedSkill || "").toLowerCase();
  const contextualCountry = (assistantState.selectedCountry || "").toLowerCase();
  if (contextualSkill && contextualCountry && skillOutlook[contextualSkill] && countryTopSkills[contextualCountry]) {
    return buildSkillCountryResponse(contextualSkill, contextualCountry);
  }

  return buildIntentFallback(message);
}

async function sendMessage() {
  const inputEl = domRefs.chatInputEl;
  if (!inputEl) {
    return;
  }

  if (assistantState.isSending) {
    return;
  }

  const userText = String(inputEl.value || "").trim();
  if (!userText) {
    return;
  }

  assistantState.isSending = true;

  addMessage(userText, "user");
  showTypingIndicator();

  domRefs.sendButtonEl && (domRefs.sendButtonEl.disabled = true);
  inputEl.value = "";

  try {
    const payload = await requestChatResponse(userText);
    const aiResponse = String(payload?.response || "").trim() || "Ask about any skill, country, or tech trend for analysis.";
    removeTypingIndicator();
    addMessage(aiResponse, "ai");
  } catch {
    removeTypingIndicator();
    addMessage("Server unavailable. Please try again.", "ai");
  } finally {
    assistantState.isSending = false;
    if (domRefs.sendButtonEl) {
      domRefs.sendButtonEl.disabled = false;
      domRefs.sendButtonEl.focus();
    }
  }
}

export function speakResponse(text) {
  if (!text || typeof window === "undefined" || !window.speechSynthesis) {
    return;
  }

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.98;
  utterance.pitch = 1.02;
  utterance.volume = 1;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

export function getSuggestionPrompts(skill = "this skill") {
  return [
    `Is ${skill} future-proof?`,
    "What should I learn next?",
    "Which city has better demand?",
  ];
}

function bindChatListeners() {
  if (domRefs.sendButtonEl) {
    domRefs.sendButtonEl.addEventListener("click", sendMessage);
    domRefs.sendButtonEl.addEventListener("click", addRippleEffect);
  }

  if (domRefs.chatInputEl) {
    domRefs.chatInputEl.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        sendMessage();
      }
    });
  }

  const suggestionButtons = Array.from(document.querySelectorAll(".suggested-chip"));
  suggestionButtons.forEach((button) => {
    button.addEventListener("click", addRippleEffect);
    button.addEventListener("click", () => {
      if (!domRefs.chatInputEl) {
        return;
      }

      domRefs.chatInputEl.value = String(button.textContent || "").trim();
      sendMessage();
    });
  });
}

function bindVoiceListener() {
  if (!domRefs.voiceButtonEl) {
    return;
  }

  domRefs.voiceButtonEl.addEventListener("click", addRippleEffect);
  domRefs.voiceButtonEl.addEventListener("click", () => {
    const lastAi = [...assistantState.conversationHistory].reverse().find((entry) => entry.sender === "ai");
    if (lastAi?.text) {
      speakResponse(lastAi.text);
    }
  });
}

export function setAssistantContext({ country, city, skill, analytics } = {}) {
  if (typeof country === "string") assistantState.selectedCountry = country;
  if (typeof city === "string") assistantState.selectedCity = city;
  if (typeof skill === "string") assistantState.selectedSkill = skill;
  if (analytics) assistantState.analytics = analytics;
}

export function getConversationHistory() {
  return [...assistantState.conversationHistory];
}

export function resetAssistantConversation() {
  assistantState.conversationHistory = [];
  assistantState.pendingTypingNode = null;
  if (domRefs.chatMessagesEl) {
    domRefs.chatMessagesEl.textContent = "";
  }
}

export function getWelcomeMessage(city, skill, analytics = null) {
  setAssistantContext({ city, skill, analytics });
  return "AI Strategic Assistant is ready.";
}

export function getAssistantReply(text) {
  return generateResponse(text);
}

export function initializeAssistant(options = {}) {
  resolveDom();
  applyAssistantPanelUI();

  if (!domRefs.chatMessagesEl || !domRefs.chatInputEl) {
    return { initialized: false, reason: "Assistant DOM elements not found." };
  }

  if (assistantState.initialized) {
    return { initialized: true, reason: "Assistant already initialized." };
  }

  setAssistantContext({
    country: options.country || domRefs.countrySelectEl?.value || assistantState.selectedCountry,
    city: options.city || domRefs.citySelectEl?.value || assistantState.selectedCity,
    skill: options.skill || domRefs.skillSelectEl?.value || assistantState.selectedSkill,
    analytics: options.analytics || assistantState.analytics,
  });

  bindChatListeners();
  bindVoiceListener();

  if (domRefs.chatMessagesEl.childElementCount === 0) {
    addMessage("🛰️ Global signal engine is online. Ask about a skill, country, or both for a contextual market brief.", "ai");
  }

  assistantState.initialized = true;
  return { initialized: true, reason: "Assistant initialized successfully." };
}
