/* dhivehi.js — client-side Dhivehi (Thaana) engine.
 *
 * Ported from the Python dhivehi_spell/dhivehi_tools engine:
 *   DV.parseUnits(word)        -> {units:[[cons,fili]], errors:[...]}
 *   DV.latinToThaana(text)     Malé Latin -> Thaana (IME backbone)
 *   DV.thaanaToLatin(text)
 *   DV.Spell                   lexicon + edit-1 suggestions, fully in-browser
 *   DV.attachIME(el, isOn)     convert Latin word to Thaana on space/enter
 */
(function (global) {
"use strict";
var DV = {};

/* ---------- script data ---------- */
var SUKUN = "ް", NOONU = "ނ", ALIFU = "އ";
var PRENASAL = { "ބ": 1, "ޑ": 1, "ދ": 1, "ގ": 1 }; // b d dh g
function isCons(ch) { var c = ch.charCodeAt(0); return (c >= 0x0780 && c <= 0x07A5) || c === 0x07B1; }
function isFili(ch) { var c = ch.charCodeAt(0); return c >= 0x07A6 && c <= 0x07B0; }
function isThaana(ch) { var c = ch.charCodeAt(0); return c >= 0x0780 && c <= 0x07B1; }

var FILI_PAIRS = {
  "ަ": "ާ", "ާ": "ަ", "ި": "ީ", "ީ": "ި",
  "ު": "ޫ", "ޫ": "ު", "ެ": "ޭ", "ޭ": "ެ",
  "ޮ": "ޯ", "ޯ": "ޮ"
};
var CONFUSION = ["ހޙޚ", "ސޘޞ", "ށޝ", "ޒޛޟޡޜ", "ތޠ", "އޢ", "ގޣ", "ކޤ", "ވޥ", "ނޏޱ"];
var CONF_MAP = {};
CONFUSION.forEach(function (g) {
  for (var i = 0; i < g.length; i++) CONF_MAP[g[i]] = g;
});

/* ---------- unit parsing / validation ---------- */
DV.parseUnits = function (word) {
  var units = [], errors = [], i = 0;
  while (i < word.length) {
    var ch = word[i];
    if (isCons(ch)) {
      if (i + 1 < word.length && isFili(word[i + 1])) {
        units.push([ch, word[i + 1]]); i += 2; continue;
      }
      var nxt = i + 1 < word.length ? word[i + 1] : null;
      units.push([ch, null]);
      if (!(ch === NOONU && nxt && PRENASAL[nxt]))
        errors.push({ index: i, code: "missing-fili" });
      i += 1;
    } else if (isFili(ch)) {
      units.push([null, ch]);
      errors.push({ index: i, code: "orphan-fili" });
      i += 1;
    } else {
      errors.push({ index: i, code: "non-thaana" });
      i += 1;
    }
  }
  return { units: units, errors: errors };
};

/* ---------- transliteration ---------- */
var LAT_CONS = [
  ["lh", "ޅ"], ["sh", "ށ"], ["th", "ތ"], ["dh", "ދ"], ["gn", "ޏ"],
  ["ch", "ޗ"], ["kh", "ޚ"], ["gh", "ޣ"], ["zh", "ޜ"],
  ["h", "ހ"], ["n", "ނ"], ["r", "ރ"], ["b", "ބ"], ["k", "ކ"],
  ["v", "ވ"], ["m", "މ"], ["f", "ފ"], ["l", "ލ"], ["g", "ގ"],
  ["s", "ސ"], ["d", "ޑ"], ["z", "ޒ"], ["t", "ޓ"], ["y", "ޔ"],
  ["p", "ޕ"], ["j", "ޖ"], ["w", "ޥ"], ["q", "ޤ"]
];
var LAT_VOWELS = [
  ["aa", "ާ"], ["ee", "ީ"], ["oo", "ޫ"], ["ey", "ޭ"], ["oa", "ޯ"],
  ["ai", "ަ" + "އ" + "ި"],
  ["a", "ަ"], ["i", "ި"], ["u", "ު"], ["e", "ެ"], ["o", "ޮ"]
];
var TO_LATIN = {
  "ހ": "h", "ށ": "sh", "ނ": "n", "ރ": "r", "ބ": "b", "ޅ": "lh", "ކ": "k",
  "އ": "", "ވ": "v", "މ": "m", "ފ": "f", "ދ": "dh", "ތ": "th", "ލ": "l",
  "ގ": "g", "ޏ": "gn", "ސ": "s", "ޑ": "d", "ޒ": "z", "ޓ": "t", "ޔ": "y",
  "ޕ": "p", "ޖ": "j", "ޗ": "ch", "ޘ": "th", "ޙ": "h", "ޚ": "kh", "ޛ": "z",
  "ޜ": "zh", "ޝ": "sh", "ޞ": "s", "ޟ": "z", "ޠ": "t", "ޡ": "z", "ޢ": "a",
  "ޣ": "gh", "ޤ": "q", "ޥ": "w", "ޱ": "n",
  "ަ": "a", "ާ": "aa", "ި": "i", "ީ": "ee", "ު": "u", "ޫ": "oo",
  "ެ": "e", "ޭ": "ey", "ޮ": "o", "ޯ": "oa", "ް": ""
};

DV.thaanaToLatin = function (text) {
  var out = "";
  for (var i = 0; i < text.length; i++)
    out += (TO_LATIN[text[i]] !== undefined) ? TO_LATIN[text[i]] : text[i];
  return out;
};

DV.latinToThaana = function (text) {
  var out = [], i = 0, n = text.length, pending = null;
  var lower = text.toLowerCase();
  function flush(v) { if (pending !== null) { out.push(pending + (v || SUKUN)); pending = null; } }
  function isAlpha(ch) { return ch >= "a" && ch <= "z"; }
  outer:
  while (i < n) {
    if (lower.substr(i, 2) === "n'") { flush(); out.push("ނ"); i += 2; continue; }
    for (var c = 0; c < LAT_CONS.length; c++) {
      var lat = LAT_CONS[c][0];
      if (lower.substr(i, lat.length) === lat) {
        flush();
        var cons = LAT_CONS[c][1];
        if (lat === "h" && (i + 1 >= n || !isAlpha(lower[i + 1]))) cons = "ށ";
        pending = cons; i += lat.length; continue outer;
      }
    }
    for (var v = 0; v < LAT_VOWELS.length; v++) {
      var lv = LAT_VOWELS[v][0], fili = LAT_VOWELS[v][1];
      if (lower.substr(i, lv.length) === lv) {
        if (pending !== null) {
          if (fili.length > 1) { out.push(pending + fili); pending = null; }
          else flush(fili);
        } else out.push("އ" + fili);
        i += lv.length; continue outer;
      }
    }
    flush(); out.push(text[i]); i += 1;
  }
  flush();
  return out.join("");
};

/* ---------- spell engine (lexicon + edit-1 deletes index) ---------- */
function unitsToKey(units) {
  var s = "";
  for (var i = 0; i < units.length; i++)
    s += (units[i][0] || "\x01") + (units[i][1] || "\x00");
  return s;
}
function subCost(a, b) {
  if (a === b) return 0;
  var ca = a[0], cb = b[0], fa = a[1], fb = b[1], cost = 0;
  if (ca !== cb)
    cost += (ca && cb && CONF_MAP[ca] && CONF_MAP[ca].indexOf(cb) >= 0) ? 0.5 : 1.0;
  if (fa !== fb)
    cost += (fa && FILI_PAIRS[fa] === fb) ? 0.4 : 0.7;
  return Math.min(cost, 1.5);
}
function unitDistance(a, b, maxCost) {
  var la = a.length, lb = b.length;
  if (Math.abs(la - lb) > maxCost) return maxCost + 1;
  var prev2 = null, prev = [], cur, i, j;
  for (j = 0; j <= lb; j++) prev[j] = j;
  for (i = 1; i <= la; i++) {
    cur = [i];
    var best = cur[0];
    for (j = 1; j <= lb; j++) {
      var cost = Math.min(prev[j] + 1, cur[j - 1] + 1,
                          prev[j - 1] + subCost(a[i - 1], b[j - 1]));
      if (i > 1 && j > 1 &&
          a[i - 1][0] === b[j - 2][0] && a[i - 1][1] === b[j - 2][1] &&
          a[i - 2][0] === b[j - 1][0] && a[i - 2][1] === b[j - 1][1])
        cost = Math.min(cost, prev2[j - 2] + 0.8);
      cur[j] = cost;
      if (cost < best) best = cost;
    }
    if (best > maxCost) return maxCost + 1;
    prev2 = prev; prev = cur;
  }
  return prev[lb];
}

DV.Spell = function () {
  this.words = new Map();      // word -> freq
  this.index = new Map();      // delete-key -> word | [words]
};
DV.Spell.prototype.load = function (textBlob) {
  var lines = textBlob.split("\n");
  for (var i = 0; i < lines.length; i++) {
    var line = lines[i];
    if (!line || line[0] === "#") continue;
    var tab = line.indexOf("\t");
    var word = tab >= 0 ? line.slice(0, tab) : line;
    var freq = tab >= 0 ? parseInt(line.slice(tab + 1), 10) || 1 : 1;
    if (this.words.has(word)) {
      if (freq > this.words.get(word)) this.words.set(word, freq);
      continue;
    }
    this.words.set(word, freq);
    var parsed = DV.parseUnits(word);
    if (parsed.errors.length) continue;
    var key = unitsToKey(parsed.units);
    this._put(key, word);
    for (var k = 0; k < key.length; k += 2)
      this._put(key.slice(0, k) + key.slice(k + 2), word);
  }
};
DV.Spell.prototype._put = function (key, word) {
  var cur = this.index.get(key);
  if (cur === undefined) this.index.set(key, word);
  else if (typeof cur === "string") { if (cur !== word) this.index.set(key, [cur, word]); }
  else if (cur.indexOf(word) < 0) cur.push(word);
};
DV.Spell.prototype.check = function (word) {
  var parsed = DV.parseUnits(word);
  if (this.words.has(word)) return { status: "ok" };
  if (parsed.errors.length)
    return { status: "structure", errors: parsed.errors,
             suggestions: this.suggest(word) };
  return { status: "unknown", suggestions: this.suggest(word) };
};
DV.Spell.prototype.suggest = function (word, limit) {
  limit = limit || 5;
  var parsed = DV.parseUnits(word);
  var key = unitsToKey(parsed.units);
  var cands = new Set(), self = this;
  function take(hit) {
    if (hit === undefined) return;
    if (typeof hit === "string") cands.add(hit);
    else hit.forEach(function (w) { cands.add(w); });
  }
  take(this.index.get(key));
  for (var k = 0; k < key.length; k += 2)
    take(this.index.get(key.slice(0, k) + key.slice(k + 2)));
  var scored = [];
  cands.forEach(function (cand) {
    var d = unitDistance(parsed.units, DV.parseUnits(cand).units, 2.0);
    if (d <= 2.0) scored.push([d, -(self.words.get(cand) || 0), cand]);
  });
  scored.sort(function (x, y) {
    return x[0] - y[0] || x[1] - y[1] || (x[2] < y[2] ? -1 : 1);
  });
  return scored.slice(0, limit).map(function (s) {
    return { word: s[2], cost: Math.round(s[0] * 100) / 100 };
  });
};

/* ---------- IME: convert the Latin word before the caret ---------- */
DV.attachIME = function (el, isOn) {
  el.addEventListener("keydown", function (ev) {
    if (!isOn() || (ev.key !== " " && ev.key !== "Enter")) return;
    var pos = el.selectionStart;
    if (pos !== el.selectionEnd) return;
    var text = el.value, start = pos;
    while (start > 0 && /[a-zA-Z']/.test(text[start - 1])) start--;
    if (start === pos) return;
    var converted = DV.latinToThaana(text.slice(start, pos));
    el.value = text.slice(0, start) + converted + text.slice(pos);
    var caret = start + converted.length;
    el.setSelectionRange(caret, caret);
    el.dispatchEvent(new Event("input", { bubbles: true }));
  });
};

global.DV = DV;
})(typeof window !== "undefined" ? window : this);
