/**
 * The film look A/B page: shows pairs, stores the votes, draws the result.
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
    config = await (await fetch("config.json")).json();
  } catch (error) {
    $("compare").innerHTML = '<p class="prompt">The photo list (config.json) did not load. Run build.py and publish its output folder.</p>';
    return;
  }
  const LOOKS = config.looks;
  const SCENES = config.scenes;
  const N = LOOKS.length;
  const STORE = "look-ab:" + config.id; // a new photo set starts with no votes
  const image = (sceneId, look) => `img/s${sceneId}_${LOOKS[look].key}.jpg`;
  const sceneById = (id) => SCENES.find((scene) => scene.id === id);
  document.title = config.title;
  $("title").textContent = config.title;

  // ---- state -------------------------------------------------------------------------------
  const state = { votes: [], target: 40, names: false };
  let pair = null; // the pair on screen: {s, a, b}
  let view = "compare";

  function load() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORE));
      if (saved && Array.isArray(saved.votes)) Object.assign(state, saved);
    } catch (error) {
      // No storage (private window): the page works, it only forgets on reload.
    }
  }
  function save() {
    try {
      localStorage.setItem(STORE, JSON.stringify(state));
    } catch (error) {
      // See load().
    }
  }

  // ---- compare view ------------------------------------------------------------------------
  function showPair() {
    pair = R.nextPair(state.votes, SCENES.map((scene) => scene.id), N, Math.random);
    const scene = sceneById(pair.s);
    $("pair").classList.toggle("wide-photo", scene.wide);
    $("sceneName").textContent = scene.name;
    $("imgA").src = image(pair.s, pair.a);
    $("imgB").src = image(pair.s, pair.b);
    paintNames();
  }
  function paintNames() {
    if (!pair) return;
    $("nameA").textContent = state.names ? LOOKS[pair.a].name : "";
    $("nameB").textContent = state.names ? LOOKS[pair.b].name : "";
  }
  function paintBar() {
    $("count").textContent = state.votes.length + " / " + state.target;
    $("prog").style.width = Math.min(100, (100 * state.votes.length) / state.target) + "%";
    $("undo").disabled = !state.votes.length;
    $("toResults").textContent = view === "results" ? "Back to pairs" : "Results";
    $("toResults").disabled = view !== "results" && state.votes.length < 4;
  }
  /** Record a choice for the pair on screen: 1 = A, 0 = B, 0.5 = no preference. */
  function vote(w) {
    if (view !== "compare" || !pair) return;
    state.votes.push({ s: pair.s, a: pair.a, b: pair.b, w });
    save();
    if (state.votes.length >= state.target) {
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
  function verdictText(result) {
    const name = (look) => `<em>${escapeHtml(LOOKS[look].name)}</em>`;
    const p = result.strengths;
    switch (result.kind) {
      case "early":
        return [`Early lead: ${name(result.top)}.`, `Only ${state.votes.length} choices so far. Rate more pairs before you trust this.`];
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
  function renderResults() {
    const result = R.verdict(state.votes, SCENES, N);
    const [headline, detail] = verdictText(result);
    $("verdict").innerHTML = headline;
    $("verdictSub").textContent = `${detail} Based on ${state.votes.length} choices.`;

    const strengths = result.strengths;
    const ranked = R.order(strengths);
    const records = R.record(state.votes, N);
    const strongest = Math.max(...strengths);
    $("rank").innerHTML = ranked
      .map((look, place) => {
        const row = records[look];
        return `<div class="name">${place + 1}. ${escapeHtml(LOOKS[look].name)}<small>${escapeHtml(LOOKS[look].menu)}</small></div>
          <div class="barcell"><i class="${place === 0 ? "top" : ""}" style="width:${(100 * strengths[look]) / strongest}%"></i></div>
          <div class="num">${percent(strengths[look])} · ${row.w}W ${row.l}L${row.t ? " " + row.t + "T" : ""}</div>`;
      })
      .join("");

    $("sit").innerHTML = R.situations(state.votes, SCENES, N)
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

    const head = ranked.map((look) => `<th>${escapeHtml(LOOKS[look].menu)}</th>`).join("");
    const body = SCENES.map((scene) => {
      const votes = state.votes.filter((v) => v.s === scene.id);
      const cells = ranked.map((look) => {
        const rate = R.winRate(votes, look);
        if (!rate) return '<td class="none">·</td>';
        const alpha = (0.08 + 0.72 * rate.rate).toFixed(2);
        const title = `${LOOKS[look].name}, ${scene.name}: ${rate.won} of ${rate.played}`;
        return `<td style="background:rgba(232,178,58,${alpha})" title="${escapeHtml(title)}">${Math.round(100 * rate.rate)}</td>`;
      });
      return `<tr><th>${escapeHtml(scene.name)}</th>${cells.join("")}</tr>`;
    }).join("");
    $("heat").innerHTML = `<thead><tr><th></th>${head}</tr></thead><tbody>${body}</tbody>`;
    $("out").hidden = true;
    $("copied").textContent = "";
  }
  /** The result as plain text, with every vote, so that it can be pasted and analysed again. */
  function resultsText() {
    const strengths = R.bradleyTerry(state.votes, N, 0.5);
    const records = R.record(state.votes, N);
    const lines = [`${config.title}: ${state.votes.length} choices`, "", "Overall (chance to beat an average look, wins-losses-ties)"];
    R.order(strengths).forEach((look, place) => {
      const row = records[look];
      lines.push(`${place + 1}. ${LOOKS[look].name}: ${percent(strengths[look])}, ${row.w}-${row.l}-${row.t}`);
    });
    lines.push("", "By situation (favourite, runner-up, choices)");
    for (const s of R.situations(state.votes, SCENES, N)) {
      if (!s.votes) continue;
      lines.push(`${s.tag}: ${LOOKS[s.order[0]].name}, ${LOOKS[s.order[1]].name}, ${s.votes}${s.votes < R.WEAK_BELOW ? " (weak)" : ""}`);
    }
    const votes = state.votes.map((v) => {
      const a = LOOKS[v.a].key;
      const b = LOOKS[v.b].key;
      return v.s + ":" + (v.w === 0.5 ? `${a}=${b}` : v.w === 1 ? `${a}>${b}` : `${b}>${a}`);
    });
    lines.push("", "Votes (scene:winner>loser, = is no preference)", votes.join(" "));
    return lines.join("\n");
  }

  // ---- controls ----------------------------------------------------------------------------
  $("pickA").addEventListener("click", () => vote(1));
  $("pickB").addEventListener("click", () => vote(0));
  $("tie").addEventListener("click", () => vote(0.5));
  $("undo").addEventListener("click", () => {
    if (!state.votes.length) return;
    state.votes.pop();
    save();
    show("compare");
  });
  $("toResults").addEventListener("click", () => show(view === "results" ? "compare" : "results"));
  $("more").addEventListener("click", () => {
    state.target = Math.max(state.target, state.votes.length) + 16;
    save();
    show("compare");
  });
  // "Start over" erases the votes, so it asks for a second tap (the viewer shows no confirm dialog).
  let armed = false;
  $("reset").addEventListener("click", () => {
    if (!armed) {
      armed = true;
      $("reset").textContent = "Tap again to erase";
      setTimeout(() => {
        armed = false;
        $("reset").textContent = "Start over";
      }, 3000);
      return;
    }
    armed = false;
    $("reset").textContent = "Start over";
    state.votes = [];
    state.target = Number($("len").value);
    save();
    show("compare");
  });
  $("len").addEventListener("change", () => {
    state.target = Number($("len").value);
    save();
    if (view === "compare" && state.votes.length >= state.target) show("results");
    else paintBar();
  });
  $("names").addEventListener("change", () => {
    state.names = $("names").checked;
    save();
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
    } else if (event.key === "z" || event.key === "Z") {
      $("undo").click();
    }
  });

  // ---- start -------------------------------------------------------------------------------
  load();
  const lengths = $("len");
  if (![...lengths.options].some((option) => Number(option.value) === state.target)) {
    lengths.add(new Option(state.target + " pairs", state.target));
  }
  lengths.value = state.target;
  $("names").checked = Boolean(state.names);
  show(state.votes.length >= state.target ? "results" : "compare");
})();
