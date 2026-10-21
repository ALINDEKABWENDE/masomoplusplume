/* MasomoPlus Plume — chat en temps réel (WebSocket, avec repli par sondage HTTP) */
(function () {
  "use strict";
  const cfg = window.PLUME_CHAT;
  if (!cfg) return;

  const csrf = () => document.querySelector('meta[name="csrf-token"]').content;
  const badges = document.querySelectorAll("[data-badge-messages]");
  let nonLus = cfg.nonLus || 0;
  const majBadge = () => badges.forEach((b) => { b.textContent = nonLus > 99 ? "99+" : nonLus; b.hidden = !(nonLus > 0); });
  majBadge();

  const fil = document.getElementById("chat-fil");
  const zone = document.getElementById("chat-messages");
  const convId = fil ? parseInt(fil.dataset.conv, 10) : null;
  const moi = cfg.userId;
  const vus = new Set();
  let dernierId = 0;
  if (fil && zone) {
    zone.querySelectorAll("[data-id]").forEach((el) => {
      const id = parseInt(el.dataset.id, 10);
      vus.add(id);
      dernierId = Math.max(dernierId, id);
    });
    zone.scrollTop = zone.scrollHeight;
  }

  const post = (url, corps) =>
    fetch(url, {
      method: "POST", credentials: "same-origin",
      headers: { "X-CSRFToken": csrf(), "X-Requested-With": "XMLHttpRequest" },
      body: corps,
    });

  function ajouter(m) {
    if (!fil || m.conversation !== convId || vus.has(m.id)) return false;
    vus.add(m.id);
    dernierId = Math.max(dernierId, m.id);
    const vide = document.getElementById("chat-vide");
    if (vide) vide.remove();
    const proche = zone.scrollHeight - zone.scrollTop - zone.clientHeight < 160;
    const bulle = document.createElement("div");
    bulle.className = "bulle " + (m.expediteur_id === moi ? "moi" : "autre");
    bulle.dataset.id = m.id;
    const texte = document.createElement("div");
    texte.className = "bulle-texte";
    texte.textContent = m.contenu; // textContent : aucune injection HTML possible
    const heure = document.createElement("div");
    heure.className = "bulle-heure";
    heure.textContent = m.heure;
    bulle.append(texte, heure);
    zone.appendChild(bulle);
    if (proche || m.expediteur_id === moi) zone.scrollTop = zone.scrollHeight;
    return true;
  }

  function majListe(m, ouverte) {
    const item = document.querySelector('.chat-item[data-conv="' + m.conversation + '"]');
    if (!item) return;
    const apercu = item.querySelector("[data-apercu]");
    if (apercu) apercu.textContent = (m.expediteur_id === moi ? "Vous : " : "") + m.contenu;
    const heure = item.querySelector("[data-heure]");
    if (heure) heure.textContent = m.heure;
    if (m.expediteur_id !== moi && !ouverte) {
      const pastille = item.querySelector("[data-non-lus]");
      if (pastille) { pastille.textContent = (parseInt(pastille.textContent, 10) || 0) + 1; pastille.hidden = false; }
    }
    const liste = document.getElementById("chat-liste");
    if (liste && liste.firstElementChild !== item) liste.prepend(item);
  }

  function marquerLu() {
    if (fil && fil.dataset.lire) post(fil.dataset.lire).catch(() => {});
  }

  function traiter(m) {
    const entrant = m.expediteur_id !== moi;
    const ouverte = !!fil && m.conversation === convId;
    if (ouverte) {
      ajouter(m);
      if (entrant) marquerLu();
    } else if (entrant) {
      nonLus += 1;
      majBadge();
      window.plumeToast(m.expediteur + " : " + (m.contenu.length > 70 ? m.contenu.slice(0, 70) + "…" : m.contenu), "message", m.url);
    }
    majListe(m, ouverte);
  }

  /* ----- envoi ----- */
  const form = document.getElementById("chat-form");
  if (form) {
    const champ = form.querySelector("textarea");
    const ajuster = () => { champ.style.height = "auto"; champ.style.height = Math.min(champ.scrollHeight, 140) + "px"; };
    champ.addEventListener("input", ajuster);
    champ.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); form.requestSubmit(); }
    });
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const texte = champ.value.trim();
      if (!texte) return;
      const bouton = form.querySelector("button");
      bouton.disabled = true;
      try {
        const rep = await post(form.action, new URLSearchParams({ contenu: texte }));
        const data = await rep.json();
        if (!rep.ok) throw new Error(data.erreur || "Envoi impossible.");
        champ.value = "";
        ajuster();
        traiter(data.message);
      } catch (err) {
        window.plumeToast(err.message || "Envoi impossible.", "erreur");
      }
      bouton.disabled = false;
      champ.focus();
    });
    champ.focus({ preventScroll: true });
  }

  /* ----- réception : WebSocket + repli par sondage ----- */
  let ws = null, ouvert = false, tentatives = 0;

  async function rattraper() {
    if (fil) {
      try {
        const rep = await fetch(fil.dataset.nouveaux + "?apres=" + dernierId, { credentials: "same-origin" });
        if (rep.ok) (await rep.json()).messages.forEach(traiter);
      } catch (e) {}
    }
    try {
      const rep = await fetch(cfg.nonLusUrl, { credentials: "same-origin" });
      if (rep.ok) { nonLus = (await rep.json()).total; majBadge(); }
    } catch (e) {}
  }

  function connecter() {
    const protocole = location.protocol === "https:" ? "wss://" : "ws://";
    try { ws = new WebSocket(protocole + location.host + cfg.wsChemin); } catch (e) { planifier(); return; }
    ws.onopen = () => { ouvert = true; tentatives = 0; rattraper(); };
    ws.onmessage = (ev) => {
      try { const d = JSON.parse(ev.data); if (d.type === "message") traiter(d.message); } catch (e) {}
    };
    ws.onclose = () => { ouvert = false; planifier(); };
    ws.onerror = () => { try { ws.close(); } catch (e) {} };
  }
  function planifier() {
    tentatives += 1;
    setTimeout(connecter, Math.min(1000 * Math.pow(2, tentatives), 15000));
  }
  if ("WebSocket" in window) connecter();

  // Repli : si le WebSocket est indisponible, on interroge le serveur toutes les 3 s.
  setInterval(() => { if (!ouvert && !document.hidden) rattraper(); }, 3000);
  // Filet de sécurité : le compteur est resynchronisé chaque minute.
  setInterval(async () => {
    try {
      const rep = await fetch(cfg.nonLusUrl, { credentials: "same-origin" });
      if (rep.ok) { nonLus = (await rep.json()).total; majBadge(); }
    } catch (e) {}
  }, 60000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) rattraper(); });
})();
