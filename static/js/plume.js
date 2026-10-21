/* MasomoPlus Plume — comportements de l'interface */
(function () {
  "use strict";

  /* ----- notifications visuelles ----- */
  window.plumeToast = function (texte, type, url) {
    let conteneur = document.querySelector(".toasts-plume");
    if (!conteneur) {
      conteneur = document.createElement("div");
      conteneur.className = "toasts-plume";
      conteneur.setAttribute("aria-live", "polite");
      document.body.appendChild(conteneur);
    }
    const toast = document.createElement(url ? "a" : "div");
    toast.className = "toast-plume " + (type || "");
    if (url) toast.href = url;
    const icone = document.createElement("i");
    icone.className = "bi " + (type === "erreur" ? "bi-exclamation-circle" : type === "message" ? "bi-chat-dots-fill" : "bi-check-circle");
    const message = document.createElement("span");
    message.textContent = texte;
    toast.append(icone, message);
    conteneur.appendChild(toast);
    setTimeout(() => { toast.classList.add("sortie"); setTimeout(() => toast.remove(), 300); }, 4500);
  };

  const csrf = () => {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : "";
  };

  /* ----- thème clair / sombre ----- */
  const racine = document.documentElement;
  const majIconesTheme = () => {
    const sombre = racine.getAttribute("data-bs-theme") === "dark";
    document.querySelectorAll("[data-theme-icone]").forEach((i) => {
      i.classList.toggle("bi-sun", sombre);
      i.classList.toggle("bi-moon-stars", !sombre);
    });
  };
  document.querySelectorAll("[data-theme-toggle]").forEach((b) =>
    b.addEventListener("click", () => {
      const suivant = racine.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
      racine.setAttribute("data-bs-theme", suivant);
      try { localStorage.setItem("plume-theme", suivant); } catch (e) {}
      majIconesTheme();
    })
  );
  majIconesTheme();

  /* ----- J'aime et abonnement sans rechargement ----- */
  const majBascule = (form, data) => {
    const bouton = form.querySelector("button");
    bouton.classList.toggle("actif", data.actif);
    bouton.setAttribute("aria-pressed", String(data.actif));
    const labelActif = bouton.dataset.labelOn;
    const labelInactif = bouton.dataset.labelOff;
    if (labelActif && labelInactif) {
      bouton.setAttribute("aria-label", data.actif ? labelActif : labelInactif);
    }
    const icone = form.querySelector("i[data-on]");
    if (icone) {
      icone.classList.remove(icone.dataset.on, icone.dataset.off);
      icone.classList.add(data.actif ? icone.dataset.on : icone.dataset.off);
    }
    const compteur = form.querySelector("[data-compteur]");
    if (compteur) compteur.textContent = data.total;
    const libelle = form.querySelector("[data-label]");
    if (libelle) libelle.textContent = data.actif ? libelle.dataset.on : libelle.dataset.off;
  };
  document.querySelectorAll("form.js-toggle").forEach((form) =>
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const bouton = form.querySelector("button");
      bouton.disabled = true;
      try {
        const rep = await fetch(form.action, {
          method: "POST",
          credentials: "same-origin",
          headers: { "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": csrf() },
        });
        if (!rep.ok) throw new Error("échec");
        const data = await rep.json();
        document
          .querySelectorAll('form.js-toggle[action="' + form.getAttribute("action") + '"]')
          .forEach((f) => majBascule(f, data));
      } catch (err) {
        window.plumeToast("Connexion instable, nouvelle tentative…", "erreur");
        form.submit(); // repli : envoi classique du formulaire
        return;
      }
      bouton.disabled = false;
    })
  );

  /* ----- partage ----- */
  const enregistrerPartage = (url, plateforme) => {
    const corps = new URLSearchParams({ plateforme: plateforme });
    fetch(url, {
      method: "POST", keepalive: true, credentials: "same-origin",
      headers: { "X-CSRFToken": csrf(), "Content-Type": "application/x-www-form-urlencoded" },
      body: corps,
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d) document.querySelectorAll("[data-compteur-partages]").forEach((e) => (e.textContent = d.total));
      })
      .catch(() => {});
  };
  document.querySelectorAll("[data-partage]").forEach((lien) =>
    lien.addEventListener("click", () => enregistrerPartage(lien.dataset.urlPartage, lien.dataset.partage))
  );
  document.querySelectorAll("[data-copier]").forEach((bouton) =>
    bouton.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(bouton.dataset.copier);
        enregistrerPartage(bouton.dataset.urlPartage, "lien");
        const libelle = bouton.querySelector("[data-libelle]");
        const ancien = libelle.textContent;
        libelle.textContent = "Lien copié !";
        window.plumeToast("Lien copié dans le presse-papiers");
        setTimeout(() => (libelle.textContent = ancien), 1800);
      } catch (e) {
        window.prompt("Copiez ce lien :", bouton.dataset.copier);
      }
    })
  );
  document.querySelectorAll("[data-partage-natif]").forEach((bouton) => {
    if (!navigator.share) { bouton.classList.add("d-none"); return; }
    bouton.addEventListener("click", () =>
      navigator
        .share({ title: bouton.dataset.titre, url: bouton.dataset.partageNatif })
        .then(() => enregistrerPartage(bouton.dataset.urlPartage, "autre"))
        .catch(() => {})
    );
  });

  /* ----- réponse à un commentaire ----- */
  const formCommentaire = document.getElementById("form-commentaire");
  if (formCommentaire) {
    const parent = formCommentaire.querySelector("[name=parent]");
    const bandeau = document.getElementById("bandeau-reponse");
    document.querySelectorAll("[data-repondre]").forEach((b) =>
      b.addEventListener("click", () => {
        parent.value = b.dataset.repondre;
        bandeau.querySelector("[data-cible]").textContent = b.dataset.nom;
        bandeau.classList.remove("d-none");
        formCommentaire.scrollIntoView({ behavior: "smooth", block: "center" });
        formCommentaire.querySelector("textarea").focus({ preventScroll: true });
      })
    );
    const annuler = document.getElementById("annuler-reponse");
    if (annuler) annuler.addEventListener("click", () => { parent.value = ""; bandeau.classList.add("d-none"); });
  }

  /* ----- éditeur : compteur de mots ----- */
  const zone = document.querySelector("[data-compte-mots]");
  const sortie = document.getElementById("compte-mots");
  if (zone && sortie) {
    const compter = () => {
      const mots = zone.value.trim() ? zone.value.trim().split(/\s+/).length : 0;
      sortie.textContent = mots + " mot" + (mots > 1 ? "s" : "") + " · " + zone.value.length + " caractères · ~" + Math.max(1, Math.round(mots / 200)) + " min de lecture";
    };
    zone.addEventListener("input", compter);
    compter();
  }

  /* ----- menus déroulants natifs (<details>) : fermeture au clic extérieur ----- */
  document.addEventListener("click", (e) => {
    document.querySelectorAll("details.menu-deroulant[open]").forEach((d) => {
      if (!d.contains(e.target)) d.removeAttribute("open");
    });
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") document.querySelectorAll("details.menu-deroulant[open]").forEach((d) => d.removeAttribute("open"));
  });

  /* ----- photo de profil : aperçu immédiat ----- */
  const entreePhoto = document.getElementById("id_photo_profil");
  if (entreePhoto) {
    entreePhoto.addEventListener("change", () => {
      const fichier = entreePhoto.files && entreePhoto.files[0];
      if (!fichier) return;
      if (fichier.size > 5 * 1024 * 1024) {
        window.plumeToast("La photo dépasse 5 Mo.", "erreur");
        entreePhoto.value = "";
        return;
      }
      const lecteur = new FileReader();
      lecteur.onload = (ev) => {
        const img = document.getElementById("apercu-photo");
        img.src = ev.target.result;
        img.classList.remove("d-none");
        const lettres = document.getElementById("apercu-lettres");
        if (lettres) lettres.classList.add("d-none");
        const coche = document.getElementById("id_supprimer_photo");
        if (coche) coche.checked = false;
        window.plumeToast("Photo prête : cliquez sur « Enregistrer ».");
      };
      lecteur.readAsDataURL(fichier);
    });
  }

  /* ----- les messages disparaissent seuls ----- */
  document.querySelectorAll(".alert-dismissible[data-auto]").forEach((a) =>
    setTimeout(() => { if (window.bootstrap) bootstrap.Alert.getOrCreateInstance(a).close(); }, 6000)
  );
})();
