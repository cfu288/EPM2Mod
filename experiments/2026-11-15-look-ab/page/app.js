/**
 * The film look A/B page: shows pairs, records the votes for the screen type in use, draws the result.
 * Data comes from config.json (written by build.py); the maths is in ranking.js.
 */
(async function () {
  "use strict";
  const R = window.Ranking;
  const $ = (id) => document.getElementById(id);
  const percent = (x) => Math.round(100 * x) + "%";
  const escapeHtml = (text) => String(text).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

  /** @type {{title: string, id: string, looks: Array<{key: string, name: string, menu: string}>,
   *          scenes: Array<{id: number, name: string, wide: boolean, tags: string[]}>}} */
  let config;
  try {
    config = await (await fetch("config.json", { cache: "no-store" })).json();
  } catch (error) {
    $("compare").innerHTML = '<p class="prompt">The photo list (config.json) did not load. Run build.py and serve its output folder.</p>';
    return;
  }
  const LOOKS = config.looks;
  const SCENES = config.scenes;
  const N = LOOKS.length;
  const image = (sceneId, look) => `img/s${sceneId}_${LOOKS[look].key}.jpg`;
  const sceneById = (id) => SCENES.find((scene) => scene.id === id);
  document.title = config.title;
  $("title").textContent = config.title;

  // ---- the screen in use -------------------------------------------------------------------
  /** Read the traits of the display in use; ranking.js makes the screen type from them. */
  function readScreen() {
    const matches = (query) => typeof matchMedia === "function" && matchMedia(query).matches;
    return R.screenIdentity({
      width: screen.width,
      height: screen.height,
      ratio: window.devicePixelRatio || 1,
      gamut: matches("(color-gamut: rec2020)") ? "Rec.2020" : matches("(color-gamut: p3)") ? "P3" : "sRGB",
      hdr: matches("(dynamic-range: high)"),
      depth: screen.colorDepth || 24,
    });
  }
  const SCREEN = readScreen();
  $("screenLabel").textContent = SCREEN.label;

  // ---- where the votes are kept ------------------------------------------------------------
  /**
   * A vote is {s, a, b, w, d, t}: scene, the two looks as shown, the result (see ranking.js),
   * the key of the screen type, the time. The store is the server (serve.py), which joins the votes
   * of all devices, or this browser when the page comes from a plain file server.
   */
  const store = { shared: false, votes: [], screens: {}, failed: false };
  const LOCAL = "look-ab:" + config.id;

  async function post(action, body) {
    const answer = await fetch("api/" + action, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!answer.ok) throw new Error("the server answered " + answer.status);
    return answer.json();
  }
  function adopt(state) {
    store.votes = state.votes;
    store.screens = state.screens;
  }
  function saveLocal() {
    try {
      localStorage.setItem(LOCAL, JSON.stringify({ votes: store.votes, screens: store.screens }));
    } catch (error) {
      // No storage (private window): the page works, it only forgets on reload.
    }
  }
  async function openStore() {
    try {
      const answer = await fetch("api/state", { cache: "no-store" });
      if (answer.ok && (answer.headers.get("content-type") || "").includes("json")) {
        adopt(await answer.json());
        store.shared = true;
        return;
      }
    } catch (error) {
      // No vote server: fall through to this browser.
    }
    try {
      const saved = JSON.parse(localStorage.getItem(LOCAL));
      if (saved && Array.isArray(saved.votes)) adopt({ votes: saved.votes.filter((v) => v.d), screens: saved.screens || {} });
    } catch (error) {
      // See saveLocal().
    }
  }
  /** Apply a change here at once, then tell the server; its answer is the truth. */
  async function change(action, body, applyHere) {
    applyHere();
    if (!store.shared) {
      saveLocal();
      return;
    }
    try {
      adopt(await post(action, body));
      store.failed = false;
    } catch (error) {
      store.failed = true; // shown in the bar; the vote stays on this page until a reload
    }
    paintBar();
  }
  const addVote = (vote) =>
    change("vote", { vote, label: SCREEN.label }, () => {
      store.votes.push(vote);
      store.screens[SCREEN.key] = SCREEN.label;
    });
  const undoVote = () =>
    change("undo", { d: SCREEN.key }, () => {
      const index = store.votes.map((v) => v.d).lastIndexOf(SCREEN.key);
      if (index >= 0) store.votes.splice(index, 1);
    });
  const resetScreen = () =>
    change("reset", { d: SCREEN.key }, () => {
      store.votes = store.votes.filter((v) => v.d !== SCREEN.key);
    });
  const ownVotes = () => store.votes.filter((v) => v.d === SCREEN.key);

  // ---- settings of this browser ------------------------------------------------------------
  // layout: "side" (two photos side by side), "flip" (one place, a tap switches), or null = by width
  const settings = { target: 40, names: false, layout: null };
  const SETTINGS = "look-ab-settings";
  try {
    Object.assign(settings, JSON.parse(localStorage.getItem(SETTINGS)) || {});
  } catch (error) {
    // Defaults.
  }
  function saveSettings() {
    try {
      localStorage.setItem(SETTINGS, JSON.stringify(settings));
    } catch (error) {
      // Defaults next time.
    }
  }

  // ---- compare view ------------------------------------------------------------------------
  let pair = null; // the pair on screen: {s, a, b}
  let view = "compare";
  let showing = "A"; // in the overlap layout: the photo that is visible

  const narrow = () => typeof matchMedia === "function" && matchMedia("(max-width: 640px)").matches;
  const layout = () => settings.layout || (narrow() ? "flip" : "side");
  /** Apply the layout and, in the overlap layout, which photo is visible. */
  function paintLayout() {
    const flip = layout() === "flip";
    $("pair").classList.toggle("flip", flip);
    $("pickA").classList.toggle("off", flip && showing !== "A");
    $("pickB").classList.toggle("off", flip && showing !== "B");
    $("chooseA").classList.toggle("showing", flip && showing === "A");
    $("chooseB").classList.toggle("showing", flip && showing === "B");
    $("layout").textContent = flip ? "Side by side" : "Overlap";
    $("how").textContent = flip ? "Tap the photo to switch between A and B, then choose below." : "Pick the one you like more.";
  }
  function switchPhoto() {
    showing = showing === "A" ? "B" : "A";
    paintLayout();
  }

  function showPair() {
    // Each screen gets its own balanced run of pairs, so that two screens can be compared.
    pair = R.nextPair(ownVotes(), SCENES.map((scene) => scene.id), N, Math.random);
    const scene = sceneById(pair.s);
    $("pair").classList.toggle("wide-photo", scene.wide);
    $("sceneName").textContent = scene.name;
    $("imgA").src = image(pair.s, pair.a);
    $("imgB").src = image(pair.s, pair.b);
    showing = "A";
    paintLayout();
    paintNames();
  }
  function paintNames() {
    if (!pair) return;
    $("nameA").textContent = settings.names ? LOOKS[pair.a].name : "";
    $("nameB").textContent = settings.names ? LOOKS[pair.b].name : "";
  }
  function paintBar() {
    const done = ownVotes().length;
    $("count").textContent = `${done} / ${settings.target}${store.failed ? " · not saved" : ""}`;
    $("prog").style.width = Math.min(100, (100 * done) / settings.target) + "%";
    $("undo").disabled = !done;
    $("toResults").textContent = view === "results" ? "Back to pairs" : "Stop, show results";
    $("toResults").disabled = view !== "results" && !store.votes.length;
  }
  /** Record a choice for the pair on screen: 1 = A, 0 = B, 0.5 = no preference. */
  function vote(w) {
    if (view !== "compare" || !pair) return;
    addVote({ s: pair.s, a: pair.a, b: pair.b, w, d: SCREEN.key, t: Date.now() });
    if (ownVotes().length >= settings.target) {
      show("results");
    } else {
      showPair();
      paintBar();
    }
  }
  function show(next) {
    view = next;
    $("compare").hidden = next !== "compare";
    $("compare").style.display = next === "compare" ? "flex" : "none";
    $("results").hidden = next !== "results";
    if (next === "results") renderResults();
    else showPair();
    paintBar();
    window.scrollTo(0, 0);
  }

  // ---- results view ------------------------------------------------------------------------
  const screenLabel = (key) => store.screens[key] || key;

  function verdictText(result, count) {
    const name = (look) => `<em>${escapeHtml(LOOKS[look].name)}</em>`;
    const p = result.strengths;
    switch (result.kind) {
      case "early":
        return [`Early lead: ${name(result.top)}.`, `Only ${count} choices so far. Rate more pairs before you trust this.`];
      case "close":
        return [
          `It is close between ${name(result.top)} and ${name(result.second)}.`,
          `They are ${percent(p[result.top])} and ${percent(p[result.second])} against an average look. More pairs will separate them, or you like both.`,
        ];
      case "consistent":
        return [
          `You prefer ${name(result.top)} for most situations.`,
          `It beats an average look ${percent(p[result.top])} of the time and leads in ${result.leads} of ${result.solid} situations with enough choices.`,
        ];
      default: {
        const where = result.differs.slice(0, 3).map((d) => `${LOOKS[d.look].name} for ${d.tag.toLowerCase()}`);
        return [
          `${name(result.top)} overall, but your pick changes with the scene.`,
          where.length ? `You lean to ${where.join(", ")}.` : "No situation has enough choices yet to say where it changes.",
        ];
      }
    }
  }
  /** One sentence on how the screens differ. */
  function screenSentence(comparison) {
    const { screens, compared, sameTop, lowestCorrelation } = comparison;
    if (screens.length === 1) return `All choices are from one screen (${screenLabel(screens[0].key)}). Open this page on another screen to compare.`;
    if (compared < 2) {
      const few = screens.filter((s) => !s.enough).map((s) => `${screenLabel(s.key)} has ${s.votes}`);
      return `Not enough choices to compare the screens yet: ${few.join(", ")}. A screen needs ${R.SCREEN_MIN}.`;
    }
    const solid = screens.filter((s) => s.enough);
    const agreement = lowestCorrelation > 0.8 ? "The rankings agree closely" : lowestCorrelation > 0.4 ? "The rankings agree in part" : "The rankings differ";
    const figure = `${agreement} (rank correlation ${lowestCorrelation.toFixed(2)}).`;
    if (sameTop) return `Your top pick is the same on ${solid.length === 2 ? "both" : "all " + solid.length} screens: ${LOOKS[solid[0].order[0]].name}. ${figure}`;
    const picks = solid.map((s) => `${LOOKS[s.order[0]].name} on ${screenLabel(s.key)}`);
    return `Your top pick differs by screen: ${picks.join(", ")}. ${figure}`;
  }
  function renderResults() {
    const votes = store.votes;
    const result = R.verdict(votes, SCENES, N);
    const [headline, detail] = verdictText(result, votes.length);
    const comparison = R.compareScreens(votes, N);
    $("verdict").innerHTML = headline;
    $("verdictSub").textContent = `${detail} Based on ${votes.length} choices on ${comparison.screens.length} screen${comparison.screens.length === 1 ? "" : "s"}.`;

    const strengths = result.strengths;
    const ranked = R.order(strengths);
    const records = R.record(votes, N);
    const strongest = Math.max(...strengths);
    $("rank").innerHTML = ranked
      .map((look, place) => {
        const row = records[look];
        return `<div class="name">${place + 1}. ${escapeHtml(LOOKS[look].name)}<small>${escapeHtml(LOOKS[look].menu)}</small></div>
          <div class="barcell"><i class="${place === 0 ? "top" : ""}" style="width:${(100 * strengths[look]) / strongest}%"></i></div>
          <div class="num">${percent(strengths[look])} · ${row.w}W ${row.l}L${row.t ? " " + row.t + "T" : ""}</div>`;
      })
      .join("");

    $("sit").innerHTML = R.situations(votes, SCENES, N)
      .filter((s) => s.votes > 0)
      .map((s) => {
        const [first, second] = s.order;
        const weak = s.votes < R.WEAK_BELOW;
        const scene = sceneById(s.sceneIds[0]);
        return `<article><img src="${image(scene.id, first)}" alt="${escapeHtml(LOOKS[first].name)} on ${escapeHtml(scene.name)}">
          <div><div class="where">${escapeHtml(s.tag)}</div><div class="fav">${escapeHtml(LOOKS[first].name)}</div>
          <div class="more ${weak ? "weak" : ""}">then ${escapeHtml(LOOKS[second].name)} · ${s.votes} choices${weak ? " · weak signal" : ""}</div></div></article>`;
      })
      .join("");

    $("screenNote").textContent = screenSentence(comparison);
    $("screens").innerHTML = comparison.screens
      .map((s) => {
        const top = s.order.slice(0, 3).map((look) => escapeHtml(LOOKS[look].name)).join(", ");
        const here = s.key === SCREEN.key ? ' <span class="here">this screen</span>' : "";
        return `<div class="label">${escapeHtml(screenLabel(s.key))}${here}</div><div class="n">${s.votes} choices</div>
          <div class="top ${s.enough ? "" : "weak"}">${top}${s.enough ? "" : " · too few to compare"}</div>`;
      })
      .join("");

    const head = ranked.map((look) => `<th>${escapeHtml(LOOKS[look].menu)}</th>`).join("");
    const body = SCENES.map((scene) => {
      const sceneVotes = votes.filter((v) => v.s === scene.id);
      const cells = ranked.map((look) => {
        const rate = R.winRate(sceneVotes, look);
        if (!rate) return '<td class="none">·</td>';
        const alpha = (0.08 + 0.72 * rate.rate).toFixed(2);
        const title = `${LOOKS[look].name}, ${scene.name}: ${rate.won} of ${rate.played}`;
        return `<td style="background:rgba(232,178,58,${alpha})" title="${escapeHtml(title)}">${Math.round(100 * rate.rate)}</td>`;
      });
      return `<tr><th>${escapeHtml(scene.name)}</th>${cells.join("")}</tr>`;
    }).join("");
    $("heat").innerHTML = `<thead><tr><th></th>${head}</tr></thead><tbody>${body}</tbody>`;

    $("storeNote").textContent = store.shared
      ? "The votes of every device that opens this address are kept together on the server."
      : "The votes are kept in this browser only, so another device starts empty. Run serve.py to join the devices.";
    $("out").hidden = true;
    $("copied").textContent = "";
  }
  /** The result as plain text, with every vote, so that it can be pasted and analysed again. */
  function resultsText() {
    const votes = store.votes;
    const strengths = R.bradleyTerry(votes, N, 0.5);
    const records = R.record(votes, N);
    const comparison = R.compareScreens(votes, N);
    const lines = [`${config.title}: ${votes.length} choices`, "", "Overall (chance to beat an average look, wins-losses-ties)"];
    R.order(strengths).forEach((look, place) => {
      const row = records[look];
      lines.push(`${place + 1}. ${LOOKS[look].name}: ${percent(strengths[look])}, ${row.w}-${row.l}-${row.t}`);
    });
    lines.push("", "By situation (favourite, runner-up, choices)");
    for (const s of R.situations(votes, SCENES, N)) {
      if (!s.votes) continue;
      lines.push(`${s.tag}: ${LOOKS[s.order[0]].name}, ${LOOKS[s.order[1]].name}, ${s.votes}${s.votes < R.WEAK_BELOW ? " (weak)" : ""}`);
    }
    lines.push("", "By screen (choices, top three)", screenSentence(comparison));
    comparison.screens.forEach((s, index) => {
      lines.push(`S${index + 1} ${screenLabel(s.key)}: ${s.votes}, ${s.order.slice(0, 3).map((look) => LOOKS[look].name).join(", ")}${s.enough ? "" : " (too few)"}`);
    });
    const screenNumber = new Map(comparison.screens.map((s, index) => [s.key, "S" + (index + 1)]));
    const coded = votes.map((v) => {
      const a = LOOKS[v.a].key;
      const b = LOOKS[v.b].key;
      return `${screenNumber.get(v.d)}/${v.s}:` + (v.w === 0.5 ? `${a}=${b}` : v.w === 1 ? `${a}>${b}` : `${b}>${a}`);
    });
    lines.push("", "Votes (screen/scene:winner>loser, = is no preference)", coded.join(" "));
    return lines.join("\n");
  }

  // ---- controls ----------------------------------------------------------------------------
  // A tap on a photo chooses it side by side, and switches photos in the overlap layout.
  $("pickA").addEventListener("click", () => (layout() === "flip" ? switchPhoto() : vote(1)));
  $("pickB").addEventListener("click", () => (layout() === "flip" ? switchPhoto() : vote(0)));
  $("chooseA").addEventListener("click", () => vote(1));
  $("chooseB").addEventListener("click", () => vote(0));
  $("layout").addEventListener("click", () => {
    settings.layout = layout() === "flip" ? "side" : "flip";
    saveSettings();
    paintLayout();
  });
  $("tie").addEventListener("click", () => vote(0.5));
  $("undo").addEventListener("click", () => {
    if (!ownVotes().length) return;
    undoVote();
    show("compare");
  });
  $("toResults").addEventListener("click", () => show(view === "results" ? "compare" : "results"));
  $("more").addEventListener("click", () => {
    settings.target = Math.max(settings.target, ownVotes().length) + 16;
    saveSettings();
    show("compare");
  });
  // "Start over" erases the votes of this screen, so it asks for a second tap (the artifact
  // viewer shows no confirm dialog).
  let armed = false;
  $("reset").addEventListener("click", () => {
    if (!armed) {
      armed = true;
      $("reset").textContent = "Tap again: erase this screen";
      setTimeout(() => {
        armed = false;
        $("reset").textContent = "Start over";
      }, 3000);
      return;
    }
    armed = false;
    $("reset").textContent = "Start over";
    settings.target = Number($("len").value);
    saveSettings();
    resetScreen();
    show("compare");
  });
  $("len").addEventListener("change", () => {
    settings.target = Number($("len").value);
    saveSettings();
    if (view === "compare" && ownVotes().length >= settings.target) show("results");
    else paintBar();
  });
  $("names").addEventListener("change", () => {
    settings.names = $("names").checked;
    saveSettings();
    paintNames();
  });
  $("copy").addEventListener("click", () => {
    const text = resultsText();
    const showText = () => {
      const box = $("out");
      box.hidden = false;
      box.value = text;
      box.focus();
      box.select();
      $("copied").textContent = "Select and copy the text below.";
    };
    try {
      navigator.clipboard.writeText(text).then(() => {
        $("copied").textContent = "Copied.";
      }, showText);
    } catch (error) {
      showText();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.target && /SELECT|TEXTAREA|INPUT/.test(event.target.tagName)) return;
    const choice = { ArrowLeft: 1, ArrowRight: 0, ArrowDown: 0.5 }[event.key];
    if (choice !== undefined) {
      vote(choice);
      event.preventDefault();
    } else if (event.key === " " && view === "compare" && layout() === "flip") {
      switchPhoto();
      event.preventDefault();
    } else if (event.key === "z" || event.key === "Z") {
      $("undo").click();
    }
  });

  // ---- start -------------------------------------------------------------------------------
  await openStore();
  const lengths = $("len");
  if (![...lengths.options].some((option) => Number(option.value) === settings.target)) {
    lengths.add(new Option(settings.target + " pairs", settings.target));
  }
  lengths.value = settings.target;
  $("names").checked = Boolean(settings.names);
  show(ownVotes().length >= settings.target ? "results" : "compare");
})();
