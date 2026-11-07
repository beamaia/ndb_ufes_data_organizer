"""zoom-review: a page on localhost to set the zoom of every picture (10x or 40x), helped by the SIFT relations.

SIFT gives only relative zoom: which of two related pictures is the close-up, and by how much. Pictures joined by usable
relations form a group with a level each (0 = widest). Setting one picture of a group derives the zoom of the others from
their levels; a verdict always wins over a derived zoom. Every click is saved to the sheet at once, and verdicts already in
the sheet are kept, so the review can be done over several sittings.
"""
from __future__ import annotations

import argparse
import errno
import io
import json
import math
import urllib.parse
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import cv2 as cv
import matplotlib
import pandas as pd

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from src.phase0_dataset_builder.matching import parse_homography, read_bgr  # noqa: E402
from src.phase0_dataset_builder.sources import DEFAULT_NDB_ORIGIN_DIR, PICTURE_RELATIONS, PICTURE_TABLE_LAB, ZOOM_REVIEW  # noqa: E402
from src.phase2_report.atlas import (  # noqa: E402
    DISPLAY_PX, GAP_IN, PAGE_WIDTH_IN, _draw_block, _ordered_relations, _picture_path, _relation_block, _scale_and_rotation,
)
from src.utils.logger import logger  # noqa: E402

ZOOMS = ("10x", "40x")
VERDICTS = ZOOMS + ("cant_tell",)
STEP = 4.0  # the two objectives are 40 / 10 = 4 times apart
TOLERANCE = 0.25  # in steps of 4x: same zoom up to x1.41, one step from x2.83 to x5.66; a relation in between is shown but not used
COLUMNS = ["histopath_id", "group", "level", "sift", "relative_zoom", "relative_to", "verdict", "derived", "possible_zoom", "evidence", "note"]
IMAGE_DPI = 130
THUMB_PX = 420  # longest side of the same-patient pictures shown as references


def _steps(relation) -> float:
    """Zoom of picture a minus zoom of picture b, in steps of 4x (+1: a is a 4x close-up of b)."""
    scale, _ = _scale_and_rotation(parse_homography(relation.homography))  # pixels of b per pixel of a
    return -math.log(scale, STEP)


def _spread(ids: list[str], links: dict[str, list[tuple[str, float]]]) -> tuple[dict[str, float], dict[str, int], set[int]]:
    """Breadth-first over the links (picture -> [(other, its value minus mine)]): a value per picture relative to the first
    picture of its component, the component, and the components where a loop reaches a picture with a second value."""
    value, component, conflicted = {}, {}, set()
    for start in ids:
        if start in value:
            continue
        number = len(set(component.values()))
        value[start], component[start], queue = 0, number, [start]
        while queue:
            node = queue.pop()
            for other, step in links[node]:
                if other not in value:
                    value[other], component[other] = value[node] + step, number
                    queue.append(other)
                elif value[other] != value[node] + step:
                    conflicted.add(number)
    return value, component, conflicted


def _sift_groups(ids: list[str], ordered: list) -> tuple[pd.DataFrame, dict[str, list[dict]]]:
    """Per picture its group, its level inside the group, what SIFT says and its measured zoom; and the relations touching each picture."""
    levels: dict[str, list[tuple[str, int]]] = {i: [] for i in ids}
    measured: dict[str, list[tuple[str, float]]] = {i: [] for i in ids}
    touching: dict[str, list[dict]] = {i: [] for i in ids}
    for number, _, relation in ordered:
        steps = _steps(relation)
        used = abs(steps - round(steps)) <= TOLERANCE
        for i in (relation.a, relation.b):
            touching[i].append({"relation": number, "used": used, "magnification": round(STEP ** abs(steps), 2)})
        measured[relation.a].append((relation.b, -steps))
        measured[relation.b].append((relation.a, steps))
        if used:
            levels[relation.a].append((relation.b, -round(steps)))
            levels[relation.b].append((relation.a, round(steps)))

    level, group, conflicted = _spread(ids, levels)  # usable relations only, in whole steps: the 10x / 40x levels
    log_zoom, linked, _ = _spread(ids, measured)  # every strong relation, measured steps; in a loop the first path reached is kept

    sheet = pd.DataFrame({"histopath_id": ids, "group": [group[i] for i in ids], "level": [level[i] for i in ids]})
    zooms = pd.DataFrame({"histopath_id": ids, "linked": [linked[i] for i in ids], "log_zoom": [log_zoom[i] for i in ids]})
    widest = zooms.loc[zooms.groupby("linked")["log_zoom"].idxmin()].set_index("linked")
    alone = zooms.groupby("linked")["histopath_id"].transform("size") == 1
    sheet["relative_zoom"] = ["" if lone else round(STEP ** (z - widest.loc[c, "log_zoom"]), 2) for c, z, lone in zip(zooms["linked"], zooms["log_zoom"], alone)]
    sheet["relative_to"] = ["" if lone else widest.loc[c, "histopath_id"] for c, lone in zip(zooms["linked"], alone)]
    sheet["level"] -= sheet.groupby("group")["level"].transform("min")
    span = sheet.groupby("group")["level"].transform("max")
    size = sheet.groupby("group")["level"].transform("size")
    sheet["sift"] = [
        "conflict" if g in conflicted or s > 1 else ZOOMS[lvl] if s == 1 else "same zoom as its group" if n > 1 else "no relation"
        for g, s, n, lvl in zip(sheet["group"], span, size, sheet["level"])
    ]
    return sheet, touching


def _derive(sheet: pd.DataFrame) -> None:
    """Fill `derived` and `zoom` from the verdicts: one verdict in a group sets the others through their levels."""
    sheet["derived"] = ""
    for _, members in sheet.groupby("group"):
        if (members["sift"] == "conflict").any():
            continue
        bases = {ZOOMS.index(v) - lvl for v, lvl in zip(members["verdict"], members["level"]) if v in ZOOMS}
        if not bases:
            continue
        base = bases.pop() if len(bases) == 1 else None
        sheet.loc[members.index, "derived"] = [
            ZOOMS[base + lvl] if base is not None and 0 <= base + lvl < len(ZOOMS) else "disagrees" for lvl in members["level"]
        ]
    sheet["possible_zoom"] = [v if v in ZOOMS else d if d in ZOOMS else "" for v, d in zip(sheet["verdict"], sheet["derived"])]
    sheet["evidence"] = [_evidence(v, d, sift) for v, d, sift in zip(sheet["verdict"], sheet["derived"], sheet["sift"])]


def _evidence(verdict: str, derived: str, sift: str) -> str:
    """Where a possible zoom comes from, strongest first. Every one is a non-expert reading, not checked by a pathologist."""
    if verdict in ZOOMS:
        if sift in ZOOMS:
            return "by_eye_agrees_with_sift" if verdict == sift else "by_eye_against_sift"
        return "by_eye_in_sift_group" if sift != "no relation" else "by_eye_only"
    return "derived_from_sift" if derived in ZOOMS else ""


def _sheet(pictures: pd.DataFrame, ordered: list, path: Path) -> tuple[pd.DataFrame, dict[str, list[dict]]]:
    """One row per picture: related pictures first, in atlas order and by level, then the pictures SIFT relates to none."""
    related = list(dict.fromkeys(i for _, _, relation in ordered for i in (relation.a, relation.b)))
    rest = pictures[~pictures["histopath_id"].isin(related)].sort_values(["case_group", "picture_group", "histopath_id"])["histopath_id"].tolist()
    sheet, touching = _sift_groups(related + rest, ordered)
    judged = pd.read_csv(path, dtype=str, keep_default_na=False)[["histopath_id", "verdict", "note"]] if path.exists() else pd.DataFrame(columns=["histopath_id", "verdict", "note"])
    sheet = sheet.merge(judged, on="histopath_id", how="left").fillna({"verdict": "", "note": ""})
    unknown = set(sheet["verdict"]) - set(VERDICTS) - {""}
    if unknown:
        raise ValueError(f"{path}: verdicts must be one of {VERDICTS}, found {sorted(unknown)}")
    sheet = sheet.sort_values(["group", "level", "histopath_id"], kind="stable").reset_index(drop=True)
    _derive(sheet)
    return sheet[COLUMNS], touching


def _save(sheet: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    sheet.to_csv(temporary, index=False)
    temporary.replace(path)  # a crash while writing never leaves a half-written sheet


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Zoom review</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 0; background: #f6f6f6; color: #222; }
  header { position: sticky; top: 0; z-index: 1; background: #fff; border-bottom: 1px solid #ddd; padding: 10px 16px; }
  #chips { display: flex; flex-wrap: wrap; gap: 2px; margin-top: 8px; max-height: 92px; overflow-y: auto; }
  .chip { width: 14px; height: 14px; border: 1px solid #bbb; border-radius: 2px; background: #fff; cursor: pointer; padding: 0; }
  .chip.z10x { background: #7fb3e0; } .chip.z40x { background: #9b7fd0; } .chip.derived { opacity: 0.45; }
  .chip.cant_tell { background: #ffe08a; } .chip.problem { background: #f08080; } .chip.current { outline: 2px solid #222; }
  .chip.gap { margin-left: 8px; }
  h2 { margin: 4px 0; font-size: 18px; } #sift { font-size: 15px; margin: 2px 0; }
  #controls { display: flex; gap: 8px; align-items: center; margin-top: 8px; flex-wrap: wrap; }
  button.verdict { font-size: 15px; padding: 6px 14px; border-radius: 4px; border: 1px solid #999; cursor: pointer; }
  button.verdict.chosen { border: 3px solid #222; } button.verdict.proposed { box-shadow: 0 0 0 3px #2ca02c; }
  #z10x { background: #7fb3e0; } #z40x { background: #9b7fd0; color: #fff; } #cant_tell { background: #ffe08a; }
  #note { width: 300px; padding: 5px; }
  main { padding: 12px 16px; text-align: center; }
  main img { max-width: 100%; background: #fff; margin-bottom: 12px; }
  #members { font-size: 13px; color: #444; margin: 4px 0; }
  .hint { color: #666; font-size: 12px; }
  #mates h3 { font-size: 15px; margin: 8px 0; text-align: left; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 8px; margin-bottom: 16px; }
  .grid figure { margin: 0; background: #fff; border: 3px solid #ddd; } .grid img { width: 100%; margin: 0; }
  .grid figure.z10x { border-color: #7fb3e0; } .grid figure.z40x { border-color: #9b7fd0; } .grid figure.sift { outline: 2px dashed #2ca02c; }
  .grid figcaption { font-size: 12px; padding: 3px; }
</style></head><body>
<header>
  <div><b id="progress"></b> <span class="hint">keys: Enter = take SIFT's zoom, 1 = 10x, 2 = 40x, 3 = can't tell, arrows to move.
  Possible zoom: a non-expert reading (by eye, helped by SIFT), not checked by a pathologist.
  Chips: blue 10x, purple 40x (faded = derived), yellow can't tell, red conflict; a gap starts a new SIFT group</span></div>
  <h2 id="title"></h2>
  <div id="sift"></div>
  <div id="members"></div>
  <div id="controls">
    <button class="verdict" id="z10x">1 10x</button>
    <button class="verdict" id="z40x">2 40x</button>
    <button class="verdict" id="cant_tell">3 can't tell</button>
    <input id="note" placeholder="note (optional, saved with the verdict)">
    <button id="prev">&larr; previous</button><button id="next">next &rarr;</button><button id="todo">next without a zoom</button>
    <label><input type="checkbox" id="unsure" checked> only pictures without a possible zoom</label>
  </div>
  <div id="chips"></div>
</header>
<main><img id="picture" alt="picture"><div id="mates"></div><div id="relations"></div></main>
<script>
let rows = [], index = 0;
const $ = id => document.getElementById(id);
const problem = r => r.sift === 'conflict' || r.derived === 'disagrees';
const shown = r => !$('unsure').checked || !r.possible_zoom;
const open = r => !r.possible_zoom && ($('unsure').checked || r.verdict !== 'cant_tell');  // in the second pass the can't-tell pictures are the ones to do
function step(direction) { for (let k = index + direction; k >= 0 && k < rows.length; k += direction) if (shown(rows[k])) { show(k); return true; } return false; }
async function load() { rows = await (await fetch('/rows')).json(); show(Math.max(0, rows.findIndex(open))); }
function siftText(row) {
  if (row.sift === 'conflict') return 'SIFT: conflict, the relations of this group do not add up to two zoom levels';
  if (row.sift === 'no relation') return 'SIFT: no relation to any other picture, judge by eye';
  if (row.sift === 'same zoom as its group') return 'SIFT: same zoom as the rest of its group, set one and the group follows';
  return `SIFT proposes ${row.sift}`;
}
function show(i) {
  index = Math.max(0, Math.min(rows.length - 1, i)); const row = rows[index];
  $('title').textContent = `picture ${row.histopath_id}` + (row.possible_zoom ? ` | possible zoom ${row.possible_zoom}${row.verdict ? '' : ' (derived)'}` : '') +
    (row.relative_to ? ` | measured x${row.relative_zoom}` + (row.relative_to === row.histopath_id ? ' (the widest of its SIFT pictures)' : ` of ${row.relative_to}`) : '');
  $('sift').textContent = siftText(row) + (row.derived === 'disagrees' ? ' | your verdicts in this group disagree with SIFT' : '');
  const group = rows.filter(r => r.group === row.group && r.histopath_id !== row.histopath_id);
  $('members').textContent = group.length ? 'same group: ' + group.map(r => `${r.histopath_id} (level ${r.level}${r.possible_zoom ? ', ' + r.possible_zoom : ''})`).join(', ') + ` | this one: level ${row.level}` : '';
  $('picture').src = `/picture/${encodeURIComponent(row.histopath_id)}`; $('note').value = row.note;
  for (const [id, v] of [['z10x', '10x'], ['z40x', '40x'], ['cant_tell', 'cant_tell']]) {
    $(id).classList.toggle('chosen', row.verdict === v); $(id).classList.toggle('proposed', row.sift === v);
  }
  const mates = row.case ? rows.filter(r => r.case === row.case && r.histopath_id !== row.histopath_id) : [];
  mates.sort((x, y) => (y.group === row.group) - (x.group === row.group));  // the same SIFT group first
  $('mates').innerHTML = !mates.length ? '<div class="hint">no other pictures of this patient</div>' :
    `<h3>Same patient: ${mates.length} other pictures (border: blue 10x, purple 40x; dashed green: same SIFT group; click to open full size)</h3><div class="grid">` +
    mates.map(r => `<a href="/picture/${encodeURIComponent(r.histopath_id)}" target="_blank"><figure class="${r.possible_zoom ? 'z' + r.possible_zoom : ''} ${r.group === row.group ? 'sift' : ''}">` +
      `<img src="/thumb/${encodeURIComponent(r.histopath_id)}" loading="lazy"><figcaption>${r.histopath_id} | ${r.possible_zoom ? r.possible_zoom + (r.verdict ? '' : ' (derived)') : r.verdict === 'cant_tell' ? "can't tell" : 'no zoom'}</figcaption></figure></a>`).join('') + '</div>';
  $('relations').innerHTML = row.relations.map(r => `<div class="hint">relation ${r.relation}, x${r.magnification}${r.used ? '' : ': not used, neither same zoom nor 4x'}</div><img src="/relation/${r.relation}">`).join('');
  const set = rows.filter(r => r.possible_zoom).length, mine = rows.filter(r => r.verdict).length;
  $('progress').textContent = `${set} of ${rows.length} pictures have a possible zoom (${mine} set by you, ${set - rows.filter(r => r.verdict && r.possible_zoom).length} derived)`;
  $('chips').innerHTML = rows.map((r, k) => !shown(r) ? '' : (() => {
    const kind = problem(r) ? 'problem' : r.possible_zoom ? 'z' + r.possible_zoom + (r.verdict ? '' : ' derived') : r.verdict;
    const gap = k > 0 && r.group !== rows[k - 1].group && (r.sift !== 'no relation' || rows[k - 1].sift !== 'no relation') ? 'gap' : '';
    return `<button class="chip ${kind} ${gap} ${k === index ? 'current' : ''}" title="${r.histopath_id}" onclick="show(${k})"></button>`;
  })()).join('');
  window.scrollTo(0, 0);
}
async function judge(verdict) {
  const row = rows[index];
  await fetch('/verdict', { method: 'POST', body: JSON.stringify({ histopath_id: row.histopath_id, verdict, note: $('note').value }) });
  rows = await (await fetch('/rows')).json();  // the derived zooms change, so the next picture is found after reloading
  const next = rows.findIndex((r, j) => j > index && open(r));
  show(next < 0 ? index : next);
}
$('z10x').onclick = () => judge('10x'); $('z40x').onclick = () => judge('40x'); $('cant_tell').onclick = () => judge('cant_tell');
$('prev').onclick = () => step(-1); $('next').onclick = () => step(1);
$('unsure').onchange = () => shown(rows[index]) ? show(index) : (step(1) || step(-1));
$('todo').onclick = () => { const k = rows.findIndex((r, j) => j > index && open(r)); show(k < 0 ? rows.findIndex(open) : k); };
document.onkeydown = e => {
  if (e.target === $('note')) return;
  const row = rows[index];
  ({ Enter: () => { if (row.sift === '10x' || row.sift === '40x') judge(row.sift); }, '1': () => judge('10x'), '2': () => judge('40x'), '3': () => judge('cant_tell'),
     ArrowLeft: () => step(-1), ArrowRight: () => step(1) }[e.key] || (() => {}))();
};
load();
</script></body></html>"""


def run_zoom_review(args: argparse.Namespace) -> dict:
    pictures = pd.read_csv(args.picture_table, dtype=str, keep_default_na=False)
    relations = pd.read_csv(args.relations)
    ordered = _ordered_relations(pictures, relations[relations["strong"].astype(bool)])
    picture_rows = {row["histopath_id"]: row for _, row in pictures.iterrows()}
    by_number = {number: relation for number, _, relation in ordered}
    case_of = dict(zip(pictures["histopath_id"], pictures["case_group"]))  # the patient, for the reference pictures
    sheet, touching = _sheet(pictures, ordered, args.zoom_review)

    def rgb(histopath_id: str):
        return cv.cvtColor(read_bgr(_picture_path(picture_rows[histopath_id], args.ndb_origin_dir)), cv.COLOR_BGR2RGB)

    @lru_cache(maxsize=128)
    def picture_image(histopath_id: str, longest: int) -> bytes:
        bgr = read_bgr(_picture_path(picture_rows[histopath_id], args.ndb_origin_dir))
        shrink = min(1.0, longest / max(bgr.shape[:2]))
        return cv.imencode(".jpg", cv.resize(bgr, None, fx=shrink, fy=shrink, interpolation=cv.INTER_AREA), [cv.IMWRITE_JPEG_QUALITY, 90])[1].tobytes()

    @lru_cache(maxsize=16)
    def relation_image(number: int) -> bytes:
        relation = by_number[number]
        block = _relation_block(relation, number, picture_rows, {i: rgb(i) for i in (relation.a, relation.b)})
        page_height = block.height_in + GAP_IN
        fig = plt.figure(figsize=(PAGE_WIDTH_IN, page_height))
        _draw_block(fig, block, GAP_IN / 2, PAGE_WIDTH_IN, page_height)
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", dpi=IMAGE_DPI)
        plt.close(fig)
        return buffer.getvalue()

    class Handler(BaseHTTPRequestHandler):
        def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            kind, _, key = self.path.lstrip("/").partition("/")
            key = urllib.parse.unquote(key)
            if self.path == "/":
                self._send(PAGE.encode(), "text/html; charset=utf-8")
            elif self.path == "/rows":
                rows = [row | {"relations": touching[row["histopath_id"]], "case": case_of[row["histopath_id"]]} for row in sheet.to_dict(orient="records")]
                self._send(json.dumps(rows).encode(), "application/json")
            elif kind in ("picture", "thumb") and key in picture_rows:
                self._send(picture_image(key, DISPLAY_PX if kind == "picture" else THUMB_PX), "image/jpeg")
            elif kind == "relation" and key.isdigit() and int(key) in by_number:
                self._send(relation_image(int(key)), "image/png")
            else:
                self._send(b"not found", "text/plain", 404)

        def do_POST(self) -> None:
            if self.path != "/verdict":
                return self._send(b"not found", "text/plain", 404)
            answer = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if answer["verdict"] not in VERDICTS or answer["histopath_id"] not in picture_rows:
                return self._send(b"bad verdict", "text/plain", 400)
            row = sheet["histopath_id"] == answer["histopath_id"]
            sheet.loc[row, ["verdict", "note"]] = [answer["verdict"], answer["note"].strip()]
            _derive(sheet)
            _save(sheet, args.zoom_review)
            self._send(b"saved", "text/plain")

        def log_message(self, *_) -> None:  # keep the terminal for the progress lines below
            pass

    try:
        server = HTTPServer(("127.0.0.1", args.port), Handler)  # this machine only: the pictures include SAB-only ones
    except OSError as error:
        if error.errno != errno.EADDRINUSE:
            raise
        raise SystemExit(f"Port {args.port} is taken, most likely by an earlier zoom-review still running (its verdicts are saved).\n"
                         f"Stop it with Ctrl+C in its terminal, or run:  kill $(lsof -tiTCP:{args.port} -sTCP:LISTEN)") from None
    _save(sheet, args.zoom_review)  # only once the port is ours, so an earlier server still running is not raced
    groups = sheet[sheet["sift"] != "no relation"]["group"].nunique()
    logger.info(f"{len(sheet)} pictures, {groups} SIFT groups, {(sheet['sift'] == 'conflict').sum()} pictures in conflicting groups")
    logger.info(f"Zoom review on http://127.0.0.1:{args.port} ({(sheet['possible_zoom'] != '').sum()} of {len(sheet)} have a possible zoom); Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
    counts = sheet.groupby(["possible_zoom", "evidence"]).size()
    return {"sheet": str(args.zoom_review), **{f"{zoom or 'no zoom'} {evidence or '(not set)'}": int(n) for (zoom, evidence), n in counts.items()}}


def zoom_review_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Page on localhost to set the zoom (10x or 40x) of every picture, helped by the SIFT relations.")
    parser.add_argument("--picture-table", type=Path, default=PICTURE_TABLE_LAB)
    parser.add_argument("--relations", type=Path, default=PICTURE_RELATIONS)
    parser.add_argument("--ndb-origin-dir", type=Path, default=DEFAULT_NDB_ORIGIN_DIR)
    parser.add_argument("--zoom-review", type=Path, default=ZOOM_REVIEW, help="The sheet; verdicts already in it are kept.")
    parser.add_argument("--port", type=int, default=8877)
    return parser
