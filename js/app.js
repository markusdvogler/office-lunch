// Office Lunch — reads data/menus.json, renders today's menus, and
// lets the user switch UI language (DE / EN / FR). Each restaurant
// may only publish in a subset of those languages; when the chosen
// language isn't available we fall back to the best available and
// show a small note.

const LANGS = ["de", "en", "fr"];
const LANG_ORDER = ["de", "en", "fr"]; // preferred fallback order

const I18N = {
  de: {
    brand: "Lunch im Büro",
    "footer-updated": "Zuletzt aktualisiert:",
    "site-link": "Website ↗",
    loading: "Menüs werden geladen…",
    empty: "Für heute wurden noch keine Menüs abgerufen.",
    error: "Menüs konnten nicht geladen werden.",
    weekend: "Am Wochenende gibt es kein Mittagsmenü.",
    "note-fallback": (from) => `Nur auf ${LANG_LABEL[from].de} verfügbar.`,
    "note-translated": (from) =>
      `Automatisch aus dem ${LANG_LABEL[from].de}en übersetzt — kann ungenau sein.`,
    "note-pdf": "Vollständige Karte als PDF ansehen.",
    "note-error": "Menü konnte nicht automatisch ausgelesen werden.",
  },
  en: {
    brand: "Office Lunch",
    "footer-updated": "Last updated:",
    "site-link": "Website ↗",
    loading: "Loading menus…",
    empty: "No menus fetched yet for today.",
    error: "Menus could not be loaded.",
    weekend: "No lunch menu on weekends.",
    "note-fallback": (from) => `Only available in ${LANG_LABEL[from].en}.`,
    "note-translated": (from) =>
      `Auto-translated from ${LANG_LABEL[from].en} — may be imprecise.`,
    "note-pdf": "See the full menu (PDF).",
    "note-error": "This menu could not be scraped automatically.",
  },
  fr: {
    brand: "Déjeuner au bureau",
    "footer-updated": "Dernière mise à jour :",
    "site-link": "Site web ↗",
    loading: "Chargement des menus…",
    empty: "Aucun menu récupéré pour aujourd'hui.",
    error: "Impossible de charger les menus.",
    weekend: "Pas de menu du midi le week-end.",
    "note-fallback": (from) => `Disponible uniquement en ${LANG_LABEL[from].fr}.`,
    "note-translated": (from) =>
      `Traduit automatiquement depuis l'${LANG_LABEL[from].fr} — peut être imprécis.`,
    "note-pdf": "Voir la carte complète (PDF).",
    "note-error": "Ce menu n'a pas pu être récupéré automatiquement.",
  },
};

const LANG_LABEL = {
  de: { de: "Deutsch", en: "German",  fr: "allemand" },
  en: { de: "Englisch", en: "English", fr: "anglais"  },
  fr: { de: "Französisch", en: "French", fr: "français" },
};

const WEEKDAY_LABEL = {
  de: ["Sonntag","Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag"],
  en: ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"],
  fr: ["Dimanche","Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi"],
};

const state = {
  lang: loadLang(),
  data: null,
};

function loadLang() {
  const saved = localStorage.getItem("office-lunch-lang");
  if (saved && LANGS.includes(saved)) return saved;
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

function formatDate(iso, lang) {
  if (!iso) return "";
  const d = new Date(iso + "T12:00:00");
  const weekday = WEEKDAY_LABEL[lang][d.getDay()];
  const opts = { year: "numeric", month: "long", day: "numeric" };
  const locale = lang === "de" ? "de-CH" : lang === "fr" ? "fr-CH" : "en-GB";
  return `${weekday}, ${d.toLocaleDateString(locale, opts)}`;
}

function pickMenu(restaurant, lang) {
  // Returns {menu, sourceLang} where sourceLang !== lang if we fell back.
  const menus = restaurant.menus || {};
  if (menus[lang] && (menus[lang].items?.length || menus[lang].raw)) {
    return { menu: menus[lang], sourceLang: lang };
  }
  for (const fb of LANG_ORDER) {
    if (fb !== lang && menus[fb] && (menus[fb].items?.length || menus[fb].raw)) {
      return { menu: menus[fb], sourceLang: fb };
    }
  }
  return { menu: null, sourceLang: null };
}

function renderCard(restaurant) {
  const tpl = document.getElementById("card-template");
  const node = tpl.content.firstElementChild.cloneNode(true);

  node.querySelector(".card-title").textContent = restaurant.name;
  const link = node.querySelector(".card-link");
  link.href = restaurant.url;
  link.textContent = t("site-link");

  const noteEl = node.querySelector(".card-note");
  const errorEl = node.querySelector(".card-error");
  const list = node.querySelector(".menu-items");

  const { menu, sourceLang } = pickMenu(restaurant, state.lang);

  const notes = [];
  if (menu && menu.translated_from) {
    notes.push(t("note-translated")(menu.translated_from));
    node.classList.add("card-translated");
  } else if (sourceLang && sourceLang !== state.lang) {
    notes.push(t("note-fallback")(sourceLang));
  }
  if (restaurant.pdf_url) {
    const label = t("note-pdf");
    notes.push(`<a href="${restaurant.pdf_url}" target="_blank" rel="noopener">${label}</a>`);
  }

  if (notes.length) {
    noteEl.hidden = false;
    noteEl.innerHTML = notes.join(" · ");
  }

  if (menu && menu.items && menu.items.length) {
    for (const item of menu.items) {
      list.appendChild(renderItem(item));
    }
  } else if (menu && menu.raw) {
    const li = document.createElement("li");
    li.className = "menu-item";
    const pre = document.createElement("div");
    pre.className = "menu-item-desc";
    pre.style.whiteSpace = "pre-line";
    pre.textContent = menu.raw;
    li.appendChild(pre);
    list.appendChild(li);
  } else if (!restaurant.pdf_url) {
    // Only surface an error when we have nothing else to show.
    // If a PDF link is present, that's the answer — the raw English
    // scraper error would just look broken next to it.
    errorEl.hidden = false;
    errorEl.textContent = t("note-error");
    if (restaurant.error) errorEl.title = restaurant.error;
  }

  return node;
}

function renderItem(item) {
  const li = document.createElement("li");
  li.className = "menu-item";

  if (item.title) {
    const title = document.createElement("div");
    title.className = "menu-item-title";
    const name = document.createElement("span");
    name.textContent = item.title;
    title.appendChild(name);
    if (item.price) {
      const price = document.createElement("span");
      price.className = "price";
      price.textContent = item.price;
      title.appendChild(price);
    }
    li.appendChild(title);
  }
  if (item.description) {
    const desc = document.createElement("div");
    desc.className = "menu-item-desc";
    desc.textContent = item.description;
    li.appendChild(desc);
  }
  if (item.tags && item.tags.length) {
    const tags = document.createElement("div");
    tags.className = "menu-item-tags";
    for (const t of item.tags) {
      const tag = document.createElement("span");
      tag.className = "tag";
      tag.textContent = t;
      tags.appendChild(tag);
    }
    li.appendChild(tags);
  }
  return li;
}

function render() {
  document.documentElement.lang = state.lang;
  for (const el of document.querySelectorAll("[data-i18n]")) {
    const key = el.dataset.i18n;
    const val = I18N[state.lang][key];
    if (typeof val === "string") el.textContent = val;
  }
  for (const btn of document.querySelectorAll(".lang-switch button")) {
    btn.setAttribute("aria-pressed", btn.dataset.lang === state.lang ? "true" : "false");
  }

  const status = document.getElementById("status");
  const grid = document.getElementById("grid");
  grid.innerHTML = "";

  if (!state.data) {
    status.textContent = t("loading");
    grid.hidden = true;
    return;
  }

  const dateStr = state.data.date;
  document.getElementById("today").textContent = dateStr ? formatDate(dateStr, state.lang) : "";
  const updated = document.getElementById("updated");
  if (state.data.generated_at) {
    const d = new Date(state.data.generated_at);
    updated.dateTime = state.data.generated_at;
    updated.textContent = d.toLocaleString(
      state.lang === "de" ? "de-CH" : state.lang === "fr" ? "fr-CH" : "en-GB"
    );
  } else {
    updated.textContent = "—";
  }

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
