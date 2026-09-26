// Office Lunch — reads data/menus.json, renders today's menus, and
// lets the user switch UI language (DE / EN / FR). Each restaurant may
// only publish in a subset of those languages; the scraper fills the
// missing ones via MyMemory translation. When a translation is used
// the card shows a small "auto-translated" note.

const LANGS = ["de", "en", "fr"];
const LANG_ORDER = ["de", "en", "fr"];

const LANG_LABEL = {
  de: { de: "Deutsch",     en: "German",  fr: "allemand" },
  en: { de: "Englisch",    en: "English", fr: "anglais"  },
  fr: { de: "Französisch", en: "French",  fr: "français" },
};

const I18N = {
  de: {
    brand: "Lunch im Büro",
    subtitle: "Heutige Mittagsmenüs in der Nähe",
    "footer-updated": "Zuletzt aktualisiert:",
    "site-link": "Website ↗",
    loading: "Menüs werden geladen…",
    empty: "Für heute wurden noch keine Menüs abgerufen.",
    error: "Menüs konnten nicht geladen werden.",
    weekend: "Am Wochenende gibt es kein Mittagsmenü.",
    "state-pdf-only-title": "Kein Tagesmenü online.",
    "state-pdf-only-body": "Dieses Restaurant veröffentlicht nur eine Gesamtkarte als PDF.",
    "state-pdf-available-title": "Tagesmenü nicht ausgelesen.",
    "state-pdf-available-body": "Die vollständige Wochenkarte ist als PDF verfügbar.",
    "state-fetch-failed-title": "Heutiges Menü nicht verfügbar.",
    "state-fetch-failed-body": "Schau direkt auf der Website nach.",
    "cta-open-pdf": "Menü als PDF öffnen",
    "cta-visit-site": "Zur Website",
    "note-translated": (from) =>
      `Automatisch aus dem ${LANG_LABEL[from].de}en übersetzt — kann ungenau sein.`,
    "note-fallback": (from) => `Nur auf ${LANG_LABEL[from].de} verfügbar.`,
    "note-standing-menu": "Standardkarte — Auswahl beliebter Gerichte, täglich verfügbar.",
  },
  en: {
    brand: "Office Lunch",
    subtitle: "Today's lunch options near the office",
    "footer-updated": "Last updated:",
    "site-link": "Website ↗",
    loading: "Loading menus…",
    empty: "No menus fetched yet for today.",
    error: "Menus could not be loaded.",
    weekend: "No lunch menu on weekends.",
    "state-pdf-only-title": "No daily menu online.",
    "state-pdf-only-body": "This restaurant publishes only its full menu as a PDF.",
    "state-pdf-available-title": "Daily menu couldn't be extracted.",
    "state-pdf-available-body": "The full weekly menu is available as a PDF.",
    "state-fetch-failed-title": "Today's menu isn't available.",
    "state-fetch-failed-body": "Check the restaurant's own website.",
    "cta-open-pdf": "Open menu (PDF)",
    "cta-visit-site": "Visit website",
    "note-translated": (from) =>
      `Auto-translated from ${LANG_LABEL[from].en} — may be imprecise.`,
    "note-fallback": (from) => `Only available in ${LANG_LABEL[from].en}.`,
    "note-standing-menu": "Standing menu — popular dishes available every day.",
  },
  fr: {
    brand: "Déjeuner au bureau",
    subtitle: "Les options du midi près du bureau",
    "footer-updated": "Dernière mise à jour :",
    "site-link": "Site web ↗",
    loading: "Chargement des menus…",
    empty: "Aucun menu récupéré pour aujourd'hui.",
    error: "Impossible de charger les menus.",
    weekend: "Pas de menu du midi le week-end.",
    "state-pdf-only-title": "Pas de menu du jour en ligne.",
    "state-pdf-only-body": "Ce restaurant publie uniquement sa carte complète en PDF.",
    "state-pdf-available-title": "Menu du jour non extrait.",
    "state-pdf-available-body": "La carte hebdomadaire complète est disponible en PDF.",
    "state-fetch-failed-title": "Menu du jour indisponible.",
    "state-fetch-failed-body": "Consulte directement le site du restaurant.",
    "cta-open-pdf": "Ouvrir le menu (PDF)",
    "cta-visit-site": "Voir le site",
    "note-translated": (from) =>
      `Traduit automatiquement de l'${LANG_LABEL[from].fr} — peut être imprécis.`,
    "note-fallback": (from) => `Disponible uniquement en ${LANG_LABEL[from].fr}.`,
    "note-standing-menu": "Carte permanente — plats populaires disponibles tous les jours.",
  },
};

const WEEKDAY_LABEL = {
  de: ["Sonntag","Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag"],
  en: ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"],
  fr: ["Dimanche","Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi"],
};

const state = { lang: loadLang(), data: null };

function loadLang() {
  try {
    const saved = localStorage.getItem("office-lunch-lang");
    if (saved && LANGS.includes(saved)) return saved;
  } catch {}
  const browser = (navigator.language || "en").slice(0, 2).toLowerCase();
  return LANGS.includes(browser) ? browser : "en";
}

function saveLang(lang) {
  try { localStorage.setItem("office-lunch-lang", lang); } catch {}
}

function t(key) {
  const val = I18N[state.lang][key];
  return typeof val === "function" ? val : val ?? key;
}

function formatHeaderDate(iso, lang) {
  if (!iso) return "";
  const d = new Date(iso + "T12:00:00");
  const weekday = WEEKDAY_LABEL[lang][d.getDay()];
  const opts = { day: "numeric", month: "long", year: "numeric" };
  const locale = lang === "de" ? "de-CH" : lang === "fr" ? "fr-CH" : "en-GB";
  return `${weekday}, ${d.toLocaleDateString(locale, opts)}`;
}

function formatUpdated(iso, lang) {
  if (!iso) return "—";
  const d = new Date(iso);
  const locale = lang === "de" ? "de-CH" : lang === "fr" ? "fr-CH" : "en-GB";
  return d.toLocaleString(locale, {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function pickMenu(restaurant, lang) {
  const menus = restaurant.menus || {};
  const hasContent = (m) => m && (m.items?.length || m.raw);
  if (hasContent(menus[lang])) return { menu: menus[lang], sourceLang: lang };
  for (const fb of LANG_ORDER) {
    if (fb !== lang && hasContent(menus[fb])) {
      return { menu: menus[fb], sourceLang: fb };
    }
  }
  return { menu: null, sourceLang: null };
}

function pickMeta(restaurant, lang) {
  const meta = restaurant.meta || {};
  return meta[lang] || meta.de || meta.en || meta.fr || {};
}

function renderCard(restaurant) {
  const tpl = document.getElementById("card-template");
  const node = tpl.content.firstElementChild.cloneNode(true);

  // Header
  node.querySelector(".card-title").textContent = restaurant.name;
  const meta = pickMeta(restaurant, state.lang);
  const subtitleBits = [];
  if (meta.cuisine) subtitleBits.push(meta.cuisine);
  if (meta.hours) subtitleBits.push(meta.hours);
  const subtitleEl = node.querySelector(".card-subtitle");
  if (subtitleBits.length) subtitleEl.textContent = subtitleBits.join(" · ");
  else subtitleEl.remove();

  const link = node.querySelector(".card-link");
  link.href = restaurant.url;
  link.textContent = t("site-link");

  // Body
  const body = node.querySelector(".card-body");
  const list = node.querySelector(".menu-items");
  const stateEl = node.querySelector(".card-state");

  const { menu, sourceLang } = pickMenu(restaurant, state.lang);
  const hasItems = menu && menu.items?.length;
  const hasRaw = menu && menu.raw;

  if (hasItems) {
    for (const it of menu.items) list.appendChild(renderItem(it));
  } else if (hasRaw) {
    const li = document.createElement("li");
    li.className = "menu-item";
    const desc = document.createElement("div");
    desc.className = "menu-item-desc";
    desc.style.whiteSpace = "pre-line";
    desc.textContent = menu.raw;
    li.appendChild(desc);
    list.appendChild(li);
  } else {
    list.remove();
    renderState(stateEl, restaurant);
  }
  if (hasItems || hasRaw) stateEl.remove();

  // Foot (translated badge, standing-menu note, phone)
  const foot = node.querySelector(".card-foot");
  const noteEl = node.querySelector(".card-note");
  const footBits = [];
  if (menu?.note === "standing-menu") {
    footBits.push(t("note-standing-menu"));
  }
  if (menu && menu.translated_from) {
    footBits.push(t("note-translated")(menu.translated_from));
    node.classList.add("card-translated");
  } else if (sourceLang && sourceLang !== state.lang) {
    footBits.push(t("note-fallback")(sourceLang));
  }
  if (meta.phone) footBits.push(`📞 ${meta.phone}`);
  if (footBits.length) {
    foot.hidden = false;
    noteEl.textContent = footBits.join(" · ");
  } else {
    foot.remove();
  }

  return node;
}

function renderState(stateEl, restaurant) {
  stateEl.hidden = false;

  let titleKey, bodyKey, ctaLabelKey, ctaHref, ctaSecondary = false;
  if (restaurant.pdf_only && restaurant.pdf_url) {
    titleKey = "state-pdf-only-title";
    bodyKey  = "state-pdf-only-body";
    ctaLabelKey = "cta-open-pdf";
    ctaHref = restaurant.pdf_url;
  } else if (restaurant.pdf_url) {
    titleKey = "state-pdf-available-title";
    bodyKey  = "state-pdf-available-body";
    ctaLabelKey = "cta-open-pdf";
    ctaHref = restaurant.pdf_url;
  } else {
    titleKey = "state-fetch-failed-title";
    bodyKey  = "state-fetch-failed-body";
    ctaLabelKey = "cta-visit-site";
    ctaHref = restaurant.url;
    ctaSecondary = true;
  }

  const title = document.createElement("p");
  title.className = "card-state-text";
  title.innerHTML = `<strong>${t(titleKey)}</strong> ${t(bodyKey)}`;
  stateEl.appendChild(title);

  const cta = document.createElement("a");
  cta.className = "card-state-cta" + (ctaSecondary ? " secondary" : "");
  cta.href = ctaHref;
  cta.target = "_blank";
  cta.rel = "noopener";
  cta.textContent = t(ctaLabelKey);
  stateEl.appendChild(cta);
}

function renderItem(it) {
  const li = document.createElement("li");
  li.className = "menu-item";

  if (it.title) {
    const title = document.createElement("div");
    title.className = "menu-item-title";
    const name = document.createElement("span");
    name.textContent = it.title;
    title.appendChild(name);
    if (it.price) {
      const price = document.createElement("span");
      price.className = "price";
      price.textContent = it.price;
      title.appendChild(price);
    }
    li.appendChild(title);
  }
  if (it.description) {
    const desc = document.createElement("div");
    desc.className = "menu-item-desc";
    desc.textContent = it.description;
    li.appendChild(desc);
  }
  if (it.tags?.length) {
    const tags = document.createElement("div");
    tags.className = "menu-item-tags";
    for (const tag of it.tags) {
      const el = document.createElement("span");
      el.className = "tag";
      el.textContent = tag;
      tags.appendChild(el);
    }
    li.appendChild(tags);
  }
  return li;
}

function render() {
  document.documentElement.lang = state.lang;
  for (const el of document.querySelectorAll("[data-i18n]")) {
    const val = I18N[state.lang][el.dataset.i18n];
    if (typeof val === "string") el.textContent = val;
  }
  for (const btn of document.querySelectorAll(".lang-switch button")) {
    btn.setAttribute("aria-pressed",
      btn.dataset.lang === state.lang ? "true" : "false");
  }

  const status = document.getElementById("status");
  const grid = document.getElementById("grid");
  grid.innerHTML = "";

  if (!state.data) {
    status.textContent = t("loading");
    grid.hidden = true;
    return;
  }

  document.getElementById("today").textContent =
    state.data.date ? formatHeaderDate(state.data.date, state.lang) : "";
  const updatedEl = document.getElementById("updated");
  updatedEl.dateTime = state.data.generated_at || "";
  updatedEl.textContent = formatUpdated(state.data.generated_at, state.lang);

  const restaurants = state.data.restaurants || [];
  const weekday = state.data.weekday;
  if (weekday === "saturday" || weekday === "sunday") {
    status.textContent = t("weekend");
    grid.hidden = true;
    return;
  }
  if (!restaurants.length) {
    status.textContent = t("empty");
    grid.hidden = true;
    return;
  }

  status.textContent = "";
  grid.hidden = false;
  for (const r of restaurants) grid.appendChild(renderCard(r));
}

async function load() {
  try {
    const res = await fetch("data/menus.json", { cache: "no-store" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    state.data = await res.json();
  } catch (err) {
    console.error(err);
    document.getElementById("status").textContent = I18N[state.lang].error;
    return;
  }
  render();
}

function setupLangSwitch() {
  for (const btn of document.querySelectorAll(".lang-switch button")) {
    btn.addEventListener("click", () => {
      state.lang = btn.dataset.lang;
      saveLang(state.lang);
      render();
    });
  }
}

setupLangSwitch();
render();
load();
