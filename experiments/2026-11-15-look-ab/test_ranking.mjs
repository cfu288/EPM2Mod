// Tests of page/ranking.js.   node --test experiments/2026-11-15-look-ab/
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import test from "node:test";

const R = createRequire(import.meta.url)("./page/ranking.js");
const N = 4;
const vote = (s, a, b, w) => ({ s, a, b, w });
/** A fixed sequence of "random" numbers, so that a test gives the same pair each run. */
const sequence = (...values) => {
  let i = 0;
  return () => values[i++ % values.length];
};

test("with no votes every look is at 0.5", () => {
  for (const p of R.bradleyTerry([], N, 0.5)) assert.ok(Math.abs(p - 0.5) < 1e-9);
});

test("a look that wins more is stronger, and the side does not matter", () => {
  const left = [vote(1, 0, 1, 1), vote(1, 0, 2, 1), vote(2, 0, 3, 1), vote(2, 1, 2, 1)];
  const right = left.map((v) => vote(v.s, v.b, v.a, 1 - v.w));
  const a = R.bradleyTerry(left, N, 0.5);
  const b = R.bradleyTerry(right, N, 0.5);
  assert.deepEqual(R.order(a), [0, 1, 2, 3].sort((x, y) => a[y] - a[x]));
  assert.equal(R.order(a)[0], 0);
  a.forEach((p, i) => assert.ok(Math.abs(p - b[i]) < 1e-9));
});

test("a tie moves neither look", () => {
  const p = R.bradleyTerry([vote(1, 0, 1, 0.5)], N, 0.5);
  assert.ok(Math.abs(p[0] - p[1]) < 1e-9);
});

test("the record counts wins, losses and ties", () => {
  const rows = R.record([vote(1, 0, 1, 1), vote(1, 1, 0, 1), vote(1, 0, 2, 0.5)], N);
  assert.deepEqual(rows[0], { w: 1, l: 1, t: 1, n: 3 });
  assert.deepEqual(rows[2], { w: 0, l: 0, t: 1, n: 1 });
  assert.deepEqual(rows[3], { w: 0, l: 0, t: 0, n: 0 });
});

test("the win rate counts a tie as half", () => {
  assert.equal(R.winRate([], 0), null);
  assert.deepEqual(R.winRate([vote(1, 0, 1, 1), vote(1, 2, 0, 0.5)], 0), { rate: 0.75, won: 1.5, played: 2 });
});

test("the next pair takes the scene with the fewest votes and two different looks", () => {
  const votes = [vote(1, 0, 1, 1), vote(2, 0, 1, 1)];
  const pair = R.nextPair(votes, [1, 2, 3], N, sequence(0.3));
  assert.equal(pair.s, 3);
  assert.notEqual(pair.a, pair.b);
});

test("the next pair is not one the scene has shown, while a new one exists", () => {
  const votes = [];
  const seen = new Set();
  for (let i = 0; i < 6; i++) {
    const pair = R.nextPair(votes, [1], N, Math.random);
    const key = [pair.a, pair.b].sort().join("-");
    assert.ok(!seen.has(key), "pair " + key + " came twice");
    seen.add(key);
    votes.push(vote(1, pair.a, pair.b, 1));
  }
  assert.equal(seen.size, 6); // all pairs of 4 looks
});

test("situations group the scenes by tag", () => {
  const scenes = [
    { id: 1, tags: ["sky"] },
    { id: 2, tags: ["sky", "greens"] },
  ];
  const rows = R.situations([vote(1, 0, 1, 1), vote(2, 2, 3, 1)], scenes, N);
  assert.deepEqual(rows.map((r) => [r.tag, r.sceneIds, r.votes]), [["sky", [1, 2], 2], ["greens", [2], 1]]);
  assert.equal(rows[1].order[0], 2);
});

test("the verdict is early, then consistent when one look leads everywhere", () => {
  const scenes = [{ id: 1, tags: ["sky"] }, { id: 2, tags: ["greens"] }];
  assert.equal(R.verdict([vote(1, 0, 1, 1)], scenes, N).kind, "early");
  const votes = [];
  for (let i = 0; i < 4; i++) for (const s of [1, 2]) for (const other of [1, 2, 3]) votes.push(vote(s, 0, other, 1));
  const result = R.verdict(votes, scenes, N);
  assert.equal(result.kind, "consistent");
  assert.equal(result.top, 0);
  assert.equal(result.leads, 2);
});

test("the verdict is situational when the favourite changes with the tag", () => {
  const scenes = [1, 2, 3, 4].map((id) => ({ id, tags: ["tag" + id] }));
  const votes = [];
  for (let i = 0; i < 3; i++) {
    for (const s of [1, 2]) for (const other of [1, 2, 3]) votes.push(vote(s, 0, other, 1)); // look 0 wins here
    for (const s of [3, 4]) for (const other of [0, 2, 3]) votes.push(vote(s, 1, other, 1)); // look 1 wins here
  }
  votes.push(vote(1, 0, 1, 1), vote(2, 0, 1, 1), vote(1, 0, 1, 1)); // look 0 is ahead overall
  const result = R.verdict(votes, scenes, N);
  assert.equal(result.top, 0);
  assert.equal(result.kind, "situational");
  assert.deepEqual(result.differs, [{ tag: "tag3", look: 1 }, { tag: "tag4", look: 1 }]);
});
