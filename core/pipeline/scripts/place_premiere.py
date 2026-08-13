#!/usr/bin/env python3
"""place_premiere.py — 正本(cutlist/broll)から Premiere 配置用の ExtendScript を生成する（案件非依存）。

★★★ トリム投入（PRINCIPLES §16・絶対厳守）
    素材を ffmpeg で切り出したファイルを作って置かない。**元素材を取り込み、
    イン点/アウト点だけを打って敷く**。前後がハンドルとして残るので、投入後に人が
    クリップの端を掴んで伸ばす・スリップするという手直しの余地が保たれる。
    切り出し方式ではこれが原理的に不可能で、「あと0.3秒前から」の一言で
    ffmpeg からやり直しになる（＝修正のたび工程を巻き戻す構造そのものが事故の温床）。

    cut.py（core/common/scripts/cut.py）は Remotion / CapCut 用。Premiere では使わない。
    cutlist の {src_in, src_out, tl} はそのままこのスクリプトの入力になる。

入力（project.json の artifacts を読む・render_proxy.py と同じ正本形式）:
    cutlist: {"cuts": [{"src_in","src_out","tl"}...]}          → V1/A1（source.aroll）
    broll:   {"inserts": [{"src","src_in","dur","tl_in"}...]}  → V2（source.broll_dir/src）

出力:
    配置用の .jsx（既定 work/place_premiere.jsx）。これを premiere-bridge-ops の
    pr.sh / prq.py で投げる。生成された jsx は:
      - documentID + path の2点照合で対象を固定し、一致が1件でなければ中断する
      - 素材を getMediaPath() で照合（NFC/NFD 両形）し、無ければ importFiles
      - setInPoint/setOutPoint（★2引数）を打ってから overwriteClip
      - 時刻はフレーム格子に丸める（サブフレームの隙間を作らない）
      - 敷いた後に **end - start** で尺を機械検算する（outPoint の読み戻しは信用しない）

使い方:
    python3 place_premiere.py <project.json> --doc-id <documentID> --proj-path <.prproj> \\
        --seq <シーケンス名> [--out work/place_premiere.jsx] [--fps 30] [--no-broll]

    # documentID は premiere-bridge-ops/templates/list_projects.jsx で採る
    # 投げる:  bash ~/.claude/skills/premiere-bridge-ops/scripts/pr.sh work/place_premiere.jsx 300000

★生成された jsx を流したあとの検証（省略厳禁）:
    配置の検算（クリップ数・尺）は jsx が返す。**効いているかは書き出した実ファイルの画素**で
    判定する（PRINCIPLES §12 / premiere-bridge-ops §4）。実写素材は焼き込みTCが無いので
    「書き出しフレーム vs 元素材の該当フレーム」を SSIM で突合し、必ず対照実験を置く。
"""

# --- VIDEO OPS ライセンスゲート（仕様§4.2・ローカル読取のみ・ネットワークなし） ---
def _vops_require(_feat):
    import sys as _s
    from pathlib import Path as _P
    _h = _P(__file__).resolve()
    _cands = [q for p in _h.parents for q in (p / "ops" / "license", p / "core" / "ops" / "license")]
    _cands.append(_P.home() / ".claude" / "skills" / "_video-core" / "ops" / "license")
    for _c in _cands:
        if (_c / "vops_license.py").exists():
            _s.path.insert(0, str(_c))
            import vops_license as _v
            _v.require(_feat)
            return
    print("⚠ VIDEO OPS: ライセンス機構が見つからない（導通不備）— 続行", file=_s.stderr)


_vops_require("pipeline")
# --- ゲートここまで ---
import json, os, sys, argparse, unicodedata, subprocess


_DUR_CACHE = {}


def media_duration(path):
    """素材の実尺（秒）。ffprobe で実測する（決め打ち・推定はしない）。"""
    if path in _DUR_CACHE:
        return _DUR_CACHE[path]
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", path],
                           capture_output=True, text=True, check=True)
        d = float(r.stdout.strip())
    except Exception as e:
        print(f"⚠ 尺を測れなかった（ガードを掛けられない）: {path} / {e}", file=sys.stderr)
        d = None
    _DUR_CACHE[path] = d
    return d


def guard_range(path, src_in, src_out, label, errors):
    """★素材尺を超える in/out を生成前に落とす（2026-08-13 実測で必要と判明）。

    Premiere は素材尺を超える out 点を **エラーにもクランプもしない**。
    要求どおりの長さのクリップが出来てしまい、配置の機械検算（clips数・end-start）は
    PASS する。存在しない区間に何が映るかは書き出すまで分からない。
    ＝「検算は通ったのに絵が違う」を作る典型なので、生成の時点で止める。
    """
    dur = media_duration(path)
    if dur is None:
        return
    if src_in < 0:
        errors.append(f"{label}: src_in={src_in:.3f} が負")
    if src_out > dur + 1e-6:
        errors.append(f"{label}: src_out={src_out:.3f} が素材尺 {dur:.3f}秒 を超える "
                      f"({os.path.basename(path)})")
    if src_out <= src_in:
        errors.append(f"{label}: src_out={src_out:.3f} <= src_in={src_in:.3f}")


def codes(s):
    """ExtendScript へ日本語パスを安全に渡すための charcode 配列（NFD罠の回避）。"""
    return ",".join(str(ord(c)) for c in s)


def jsx_path_pair(path):
    """NFC/NFD 両形を s([...]) 形式で返す。Premiere は getMediaPath() を NFD で返す。"""
    return (f"s([{codes(unicodedata.normalize('NFC', path))}])",
            f"s([{codes(unicodedata.normalize('NFD', path))}])")


def build(prof, root, doc_id, proj_path, seq_name, fps, use_broll):
    def p(rel):
        return rel if os.path.isabs(rel) else os.path.join(root, rel)

    art = prof["artifacts"]
    cl = json.load(open(p(art["cutlist"]), encoding="utf-8"))
    cuts = cl["cuts"] if isinstance(cl, dict) else cl

    aroll = prof["source"]["aroll"]
    if not os.path.exists(aroll):
        sys.exit(f"★A-roll が無い: {aroll}")

    errors = []
    rows = []          # (nfc, nfd, src_in, src_out, tl, track_kind, label)
    a_nfc, a_nfd = jsx_path_pair(aroll)
    for i, c in enumerate(cuts):
        si, so = float(c["src_in"]), float(c["src_out"])
        guard_range(aroll, si, so, f"cutlist.cuts[{i}]", errors)
        rows.append((a_nfc, a_nfd, si, so, float(c["tl"]), "V1", f"aroll{i:03d}"))

    brolls = []
    if use_broll and art.get("broll") and os.path.exists(p(art["broll"])):
        br = json.load(open(p(art["broll"]), encoding="utf-8"))
        inserts = br["inserts"] if isinstance(br, dict) else br
        bdir = prof["source"].get("broll_dir", "")
        for i, x in enumerate(inserts):
            f = x["src"] if os.path.isabs(x["src"]) else os.path.join(bdir, x["src"])
            if not os.path.exists(f):
                sys.exit(f"★B-roll が無い: {f}")
            n, d = jsx_path_pair(f)
            si = float(x["src_in"])
            guard_range(f, si, si + float(x["dur"]), f"broll.inserts[{i}]", errors)
            brolls.append((n, d, si, si + float(x["dur"]), float(x["tl_in"]), "V2",
                           f"broll{i:03d}"))

    if errors:
        # ★ここで止めないと「黒＋無音」が黙って焼き込まれる（2026-08-13 実測）
        sys.exit("★中断: 素材尺を超えるトリム指定がある（Premiereはエラーもクランプもせず、\n"
                 "        超過分を【完全な黒＋無音】で埋める。配置の機械検算もPASSしてしまう）\n"
                 + "\n".join("  - " + e for e in errors))

    def emit(rs):
        out = []
        for (nfc, nfd, si, so, tl, _k, label) in rs:
            out.append(f'  {{ nfc: {nfc}, nfd: {nfd}, src_in: {si:.4f}, '
                       f'src_out: {so:.4f}, tl: {tl:.4f}, label: "{label}" }}')
        return ",\n".join(out)

    proj_nfc, proj_nfd = jsx_path_pair(proj_path)
    tpl = JSX_TEMPLATE
    tpl = tpl.replace("__DOCID__", doc_id)
    tpl = tpl.replace("__PROJ_NFC__", proj_nfc).replace("__PROJ_NFD__", proj_nfd)
    tpl = tpl.replace("__SEQNAME_CODES__", f"s([{codes(unicodedata.normalize('NFC', seq_name))}])")
    tpl = tpl.replace("__SEQNAME_CODES_NFD__", f"s([{codes(unicodedata.normalize('NFD', seq_name))}])")
    tpl = tpl.replace("__FPS__", repr(float(fps)))
    tpl = tpl.replace("__AROLL_CUTS__", emit(rows))
    tpl = tpl.replace("__BROLL_CUTS__", emit(brolls))
    return tpl, len(rows), len(brolls)


JSX_TEMPLATE = r'''// place_premiere.jsx — place_premiere.py が生成（手で編集しない・正本はcutlist）
// ★トリム投入: 素材を切り出さず in点/out点で敷く（_video-core/PRINCIPLES.md §16）
function s(a) { var r = ""; for (var i = 0; i < a.length; i++) r += String.fromCharCode(a[i]); return r; }

var DOCID   = "__DOCID__";
var PROJ_NFC = __PROJ_NFC__, PROJ_NFD = __PROJ_NFD__;
var SEQ_NFC  = __SEQNAME_CODES__, SEQ_NFD = __SEQNAME_CODES_NFD__;
var FPS = __FPS__;

var AROLL = [
__AROLL_CUTS__
];
var BROLL = [
__BROLL_CUTS__
];

var out = [];
function T(sec) { var t = new Time(); t.seconds = sec; return t; }
function grid(sec) { return Math.round(sec * FPS) / FPS; }

// --- 対象の固定（documentID + path の2点照合。1件でなければ触らない） ---
var proj = null, hits = 0;
for (var j = 0; j < app.projects.numProjects; j++) {
    var q = app.projects[j];
    if (q.documentID === DOCID && (q.path === PROJ_NFC || q.path === PROJ_NFD)) { proj = q; hits++; }
}
if (hits !== 1) return "★中断: docID+path の一致が " + hits + " 件（0=未オープン / 2以上=コピーが開いている）";

var seq = null;
for (var i = 0; i < proj.sequences.numSequences; i++) {
    var nm = proj.sequences[i].name;
    if (nm === SEQ_NFC || nm === SEQ_NFD) seq = proj.sequences[i];
}
if (!seq) return "★中断: シーケンスが無い";
if (seq.videoTracks.numTracks < 2) return "★中断: V2 が無い（numTracks=" + seq.videoTracks.numTracks + "）";

// --- 素材の解決（名前ではなく getMediaPath で・無ければ取り込み） ---
function findByPath(nfc, nfd, bin) {
    for (var i = 0; i < bin.children.numItems; i++) {
        var it = bin.children[i];
        if (it.type === 2) { var r = findByPath(nfc, nfd, it); if (r) return r; }
        else { var mp = ""; try { mp = it.getMediaPath(); } catch (e) {} if (mp === nfc || mp === nfd) return it; }
    }
    return null;
}
function resolve(list) {
    var res = [], miss = 0;
    for (var k = 0; k < list.length; k++) {
        var c = list[k];
        var it = findByPath(c.nfc, c.nfd, proj.rootItem);
        if (!it) { proj.importFiles([c.nfc], false, proj.rootItem, false); it = findByPath(c.nfc, c.nfd, proj.rootItem); }
        if (!it) miss++;
        res.push(it);
    }
    return { items: res, miss: miss };
}
var ra = resolve(AROLL), rb = resolve(BROLL);
if (ra.miss || rb.miss)
    return "★中断: 素材の取り込みが未完（importFiles は非同期）。A欠け=" + ra.miss + " B欠け=" + rb.miss + " → もう一度実行する";

// --- 敷く（既存を掃除してから・ripple=false） ---
function layTrack(track, list, items) {
    for (var c2 = track.clips.numItems - 1; c2 >= 0; c2--) track.clips[c2].remove(false, false);
    for (var k = 0; k < list.length; k++) {
        var c = list[k], it = items[k];
        it.setInPoint (T(grid(c.src_in )), 4);   // ★2引数（mediaType 省略不可）
        it.setOutPoint(T(grid(c.src_out)), 4);
        track.overwriteClip(it, T(grid(c.tl)));  // ★素材の in/out を尊重して置かれる
    }
}
var V1 = seq.videoTracks[0], V2 = seq.videoTracks[1], A1 = seq.audioTracks[0];
for (var c2 = A1.clips.numItems - 1; c2 >= 0; c2--) A1.clips[c2].remove(false, false);
layTrack(V1, AROLL, ra.items);
if (BROLL.length) layTrack(V2, BROLL, rb.items);

// --- 機械検算（★尺は end - start。outPoint の読み戻しは信用しない） ---
var ng = 0;
function verify(track, list, tag) {
    if (track.clips.numItems !== list.length) {
        ng++; out.push("★NG " + tag + " クリップ数 " + track.clips.numItems + " / 設計 " + list.length);
    }
    for (var k = 0; k < track.clips.numItems && k < list.length; k++) {
        var q = track.clips[k], c = list[k];
        var gotF  = Math.round((q.end.seconds - q.start.seconds) * FPS);
        var wantF = Math.round((c.src_out - c.src_in) * FPS);
        var gotS  = Math.round(q.start.seconds * FPS), wantS = Math.round(grid(c.tl) * FPS);
        if (gotF !== wantF || gotS !== wantS) {
            ng++;
            out.push("★NG " + tag + "[" + k + "] " + c.label
                + " 開始F " + gotS + "/" + wantS + " 尺F " + gotF + "/" + wantF);
        }
    }
    out.push(tag + ": clips=" + track.clips.numItems + " 設計=" + list.length);
}
verify(V1, AROLL, "V1");
if (BROLL.length) verify(V2, BROLL, "V2");
out.push("A1: clips=" + A1.clips.numItems + "（A-rollのリンク音声・設計=" + AROLL.length + "）");
if (A1.clips.numItems !== AROLL.length) { ng++; out.push("★NG A1 のクリップ数が設計と違う"); }
out.push("seq.end=" + (seq.end / 254016000000).toFixed(4));
out.push(ng === 0 ? "機械検算: 全項目PASS" : "★機械検算: NG " + ng + " 件");
out.push("※これは配置の検算にすぎない。効いているかは【書き出した実ファイルの画素】で判定する");

proj.save();
return out.join("\n");
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("profile")
    ap.add_argument("--doc-id", required=True, help="list_projects.jsx で採った documentID")
    ap.add_argument("--proj-path", required=True, help="対象 .prproj のフルパス（2点照合用）")
    ap.add_argument("--seq", required=True, help="敷く先のシーケンス名")
    ap.add_argument("--out", default=None)
    ap.add_argument("--fps", type=float, default=None, help="省略時は profile.proxy.fps ではなく 30")
    ap.add_argument("--no-broll", action="store_true")
    a = ap.parse_args()

    prof = json.load(open(a.profile, encoding="utf-8"))
    root = prof.get("root") or os.path.dirname(os.path.abspath(a.profile))
    fps = a.fps or float(prof.get("premiere", {}).get("fps", 30))

    if str(prof.get("renderer", "premiere")).lower() != "premiere":
        print(f"⚠ profile の renderer が '{prof.get('renderer')}' です。"
              f"このスクリプトは Premiere 案件用（PRINCIPLES §16）", file=sys.stderr)

    jsx, na, nb = build(prof, root, a.doc_id, a.proj_path, a.seq, fps, not a.no_broll)
    out = a.out or os.path.join(root, "work", "place_premiere.jsx")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(jsx)
    print(f"生成: {out}")
    print(f"  A-roll {na} カット / B-roll {nb} 枚 / fps={fps}")
    print(f"  ★トリム投入（素材は切り出さない・PRINCIPLES §16）")
    print(f"  投げる: bash ~/.claude/skills/premiere-bridge-ops/scripts/pr.sh {out} 300000")
    print(f"  流した後: 書き出して【実ファイルの画素】で検証する（配置の検算だけで完了と言わない）")


if __name__ == "__main__":
    main()
