/**
 * Paired-comparison maths for the film look A/B page. No DOM here: the same file runs in the
 * browser (as `window.Ranking`) and in Node (as a CommonJS module) for the tests.
 *
 * A vote is {s, a, b, w}: scene id, the two look indexes as shown (a on the left), and
 * w = 1 when a won, 0 when b won, 0.5 for "no preference".
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.Ranking = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  /**
   * Bradley-Terry strengths by the MM algorithm (Hunter 2004).
   * @param {Array} votes the votes to fit
   * @param {number} n number of looks
   * @param {number} prior virtual half-wins of each look against every other look. It keeps a
   *   look with few votes near 0.5 and makes the fit defined when a look never lost.
   * @returns {number[]} for each look, the chance that it beats an average look (0 to 1)
   */
  function bradleyTerry(votes, n, prior) {
    const wins = Array.from({ length: n }, () => new Array(n).fill(0));
    for (const v of votes) {
      wins[v.a][v.b] += v.w;
      wins[v.b][v.a] += 1 - v.w;
    }
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) if (i !== j) wins[i][j] += prior;
    let p = new Array(n).fill(1);
    for (let iteration = 0; iteration < 200; iteration++) {
      const next = p.map((_, i) => {
        let won = 0;
        let denominator = 0;
        for (let j = 0; j < n; j++) {
          if (j === i) continue;
          won += wins[i][j];
          denominator += (wins[i][j] + wins[j][i]) / (p[i] + p[j]);
        }
        return won / denominator;
      });
      // Scale to a geometric mean of 1, so that strength 1 is "an average look".
      const mean = Math.exp(next.reduce((sum, x) => sum + Math.log(x), 0) / n);
      p = next.map((x) => x / mean);
    }
    return p.map((x) => x / (x + 1));
  }

  /** Wins, losses, ties and matches of each look: [{w, l, t, n}]. */
  function record(votes, n) {
    const rows = Array.from({ length: n }, () => ({ w: 0, l: 0, t: 0, n: 0 }));
    for (const v of votes) {
      rows[v.a].n++;
      rows[v.b].n++;
      if (v.w === 0.5) {
        rows[v.a].t++;
        rows[v.b].t++;
      } else {
        const [winner, loser] = v.w === 1 ? [v.a, v.b] : [v.b, v.a];
        rows[winner].w++;
        rows[loser].l++;
      }
    }
    return rows;
  }

  /** Look indexes, strongest first. */
  function order(strengths) {
    return strengths.map((_, i) => i).sort((a, b) => strengths[b] - strengths[a]);
  }

  /** Win rate of one look in a set of votes (a tie counts half), or null with no match. */
  function winRate(votes, look) {
    let won = 0;
    let played = 0;
    for (const v of votes) {
      if (v.a === look) {
        won += v.w;
        played++;
      } else if (v.b === look) {
        won += 1 - v.w;
        played++;
      }
    }
    return played ? { rate: won / played, won, played } : null;
  }

  /**
   * The next pair to show: the scene with the fewest votes (not the last scene, if there is a
   * choice), then two looks that have few matches and are close in strength, which is where a
   * vote tells the most. A pair already shown for the scene comes last.
   * @param {Array} votes the votes so far
   * @param {number[]} sceneIds all scene ids
   * @param {number} n number of looks
   * @param {function(): number} random a source of numbers in [0, 1)
   * @returns {{s: number, a: number, b: number}} the scene and the looks, a on the left
   */
  function nextPair(votes, sceneIds, n, random) {
    const count = (id) => votes.filter((v) => v.s === id).length;
    const fewest = Math.min(...sceneIds.map(count));
    const candidates = sceneIds.filter((id) => count(id) === fewest);
    const last = votes.length ? votes[votes.length - 1].s : null;
    const fresh = candidates.filter((id) => id !== last);
    const pool = fresh.length ? fresh : candidates;
    const scene = pool[Math.floor(random() * pool.length)];

    const pairKey = (i, j) => Math.min(i, j) + "-" + Math.max(i, j);
    const shown = new Set(votes.filter((v) => v.s === scene).map((v) => pairKey(v.a, v.b)));
    const matches = record(votes, n).map((row) => row.n);
    const strengths = bradleyTerry(votes, n, 0.5);
    let best = null;
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const cost =
          (shown.has(pairKey(i, j)) ? 100 : 0) +
          matches[i] +
          matches[j] +
          6 * Math.abs(strengths[i] - strengths[j]) +
          1.5 * random();
        if (!best || cost < best.cost) best = { cost, i, j };
      }
    }
    const flip = random() < 0.5; // the side must not tell which look it is
    return { s: scene, a: flip ? best.j : best.i, b: flip ? best.i : best.j };
  }

  /**
   * One row per situation tag, in the order the tags first appear.
   * @param {Array} votes all votes
   * @param {Array<{id: number, tags: string[]}>} scenes the scenes
   * @param {number} n number of looks
   * @returns {Array<{tag: string, sceneIds: number[], votes: number, strengths: number[], order: number[]}>}
   */
  function situations(votes, scenes, n) {
    const tags = [];
    for (const scene of scenes) for (const tag of scene.tags) if (!tags.includes(tag)) tags.push(tag);
    return tags.map((tag) => {
      const sceneIds = scenes.filter((scene) => scene.tags.includes(tag)).map((scene) => scene.id);
      const subset = votes.filter((v) => sceneIds.includes(v.s));
      const strengths = bradleyTerry(subset, n, 1);
      return { tag, sceneIds, votes: subset.length, strengths, order: order(strengths) };
    });
  }

  /** Fewer votes than this in a situation is a weak signal. */
  const WEAK_BELOW = 6;

  /**
   * The headline of the result.
   * @returns {{kind: "early"|"close"|"consistent"|"situational", top: number, second: number,
   *   leads: number, solid: number, differs: Array<{tag: string, look: number}>}}
   */
  function verdict(votes, scenes, n) {
    const strengths = bradleyTerry(votes, n, 0.5);
    const [top, second] = order(strengths);
    const solid = situations(votes, scenes, n).filter((s) => s.votes >= WEAK_BELOW);
    const leads = solid.filter((s) => s.order[0] === top).length;
    const differs = solid.filter((s) => s.order[0] !== top).map((s) => ({ tag: s.tag, look: s.order[0] }));
    let kind = "situational";
    if (votes.length < 12) kind = "early";
    else if (strengths[top] - strengths[second] < 0.04) kind = "close";
    else if (solid.length && leads >= Math.ceil(solid.length * 0.6)) kind = "consistent";
    return { kind, top, second, leads, solid: solid.length, differs, strengths };
  }

  return { bradleyTerry, record, order, winRate, nextPair, situations, verdict, WEAK_BELOW };
});
