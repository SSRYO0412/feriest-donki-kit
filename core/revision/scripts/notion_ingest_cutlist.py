#!/usr/bin/env python3
"""カットリストJSON → カット台帳・素材使用DB・テロップチェックDB 一括機械起票（契約§9。手転記の廃止）。

入力形式(check_variant_dupes.pyと同じ): {"<video_id>": [ {sid,rel,tin,dur,text} | [sid,rel,tin,dur,text], ... ]}
- cut_key = <video_id>_c<NN> をsid順で自動採番
- 動画内開始秒 = durの累積 / 素材tin・尺・テロップ文言を投入
- テロップ行: 文字数(全半角スペース除く)・表示秒数・字/秒 を自動計算
- 素材ごとに素材DB(編集制約台帳)へ upsert(--clips で verified_clips.json のverdict要約も転記)
- **冪等**: cut_key(テロップは video_id+行No)で既存行を検索し、あれば更新・なければ作成
- 既定dry-run。--apply で書き込み。--video で1動画だけ(1本検証→全展開の原則)

使い方:
  python3 notion_ingest_cutlist.py <project_page_id> <cutlists.json> \
      [--video 0290_01] [--clips verified_clips.json] [--apply] [--log <path>]
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from notion_rest import Notion, rt
from notion_model import Project, PatchLogger, rt_payload, rel_payload, default_log_path


def norm_cut(c, i):
    if isinstance(c, dict):
        return {"sid": str(c.get("sid", i + 1)), "rel": c["rel"],
                "tin": c.get("tin"), "dur": c.get("dur"), "text": c.get("text", "")}
    return {"sid": str(c[0]), "rel": c[1], "tin": c[2] if len(c) > 2 else None,
            "dur": c[3] if len(c) > 3 else None, "text": c[4] if len(c) > 4 else ""}


def char_count(text):
    return len(re.sub(r"[ 　\n]", "", str(text or "")))


def cached_rows(p, role):
    if role not in p._cache:
        p._cache[role] = p.rows(role)
    return p._cache[role]


def upsert(p, log, role, match_logical, match_value, props, title_text, note):
    """論理キーで既存行を探し、あればpatch(差分のみ)・なければcreate。"""
    rows = cached_rows(p, role)
    hit = next((r for r in rows if (r.get(match_logical) or "") == match_value), None)
    schema_props = p.schema(role)["properties"]
    title_prop = next(k for k, v in schema_props.items() if v["type"] == "title")
    if hit:
        for prop_name, payload in props.items():
            log.patch(hit["_id"], prop_name, payload, note=f"{note}(更新)")
        return hit["_id"]
    props = dict(props)
    props[title_prop] = {"title": rt(title_text)}
    return log.create(p.dbs[role], props, note=f"{note}(新規)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_page_id")
    ap.add_argument("cutlists")
    ap.add_argument("--video", help="この動画だけ起票(1本検証→全展開)")
    ap.add_argument("--clips", help="verified_clips.json(verdict要約の転記)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--log", default=None)
    a = ap.parse_args()

    n = Notion()
    p = Project(n, a.project_page_id)
    p._cache = {}
    log = PatchLogger(n, a.log or default_log_path("ingest"), dry_run=not a.apply)
    data = json.loads(Path(a.cutlists).read_text())
    clips = json.loads(Path(a.clips).read_text()).get("clips", {}) if a.clips else {}

    vid_index = {}
    for v in p.rows("video"):
        from notion_model import extract_video_id
        vid = v.get("video_id") or extract_video_id(v.get("title"))
        if vid:
            vid_index[vid] = v

    from notion_model import extract_video_id as _resolve
    for vid_raw, cuts in data.items():
        vid = vid_raw if vid_raw in vid_index else (_resolve(vid_raw, set(vid_index)) or vid_raw)
        if a.video and a.video not in (vid, vid_raw):
            continue
        video_row = vid_index.get(vid)
        vrel = rel_payload(video_row["_id"]) if video_row else None
        if not video_row:
            print(f"WARN: 動画台帳に {vid} が無い(先に動画行を起票すること)。relationなしで続行")
        cum = 0.0
        for i, raw in enumerate(cuts):
            c = norm_cut(raw, i)
            ck = f"{vid}_c{int(re.sub(r'[^0-9]', '', c['sid']) or i + 1):02d}"
            # カット台帳
            props = {p.prop("cut", "cut_key"): rt_payload(ck),
                     p.prop("cut", "video_id"): rt_payload(vid)}
            if p.prop("cut", "cut_id"):
                props[p.prop("cut", "cut_id")] = rt_payload(ck)
            for logical, val in (("動画内開始秒", cum), ("素材内開始秒 tin", c["tin"]), ("尺", c["dur"])):
                name = logical if logical in p.schema("cut")["properties"] else None
                if name and val is not None:
                    props[name] = {"number": round(float(val), 3)}
            if "テロップ文言" in p.schema("cut")["properties"] and c["text"]:
                props["テロップ文言"] = rt_payload(c["text"])
            if "使用素材名" in p.schema("cut")["properties"]:
                props["使用素材名"] = rt_payload(c["rel"])
            if vrel and p.prop("cut", "video_rel"):
                props[p.prop("cut", "video_rel")] = vrel
            cut_page = upsert(p, log, "cut", "cut_key", ck, props,
                              f"{ck} {str(c['text'])[:25]}", f"ingest: カット{ck}")
            # 素材使用DB
            uprops = {p.prop("asset_use", "cut_key"): rt_payload(ck),
                      p.prop("asset_use", "video_id"): rt_payload(vid)}
            if "素材名" in p.schema("asset_use")["properties"]:
                uprops["素材名"] = rt_payload(c["rel"])
            if vrel and p.prop("asset_use", "video_rel"):
                uprops[p.prop("asset_use", "video_rel")] = vrel
            if cut_page and p.prop("asset_use", "cut_rel"):
                uprops[p.prop("asset_use", "cut_rel")] = rel_payload(cut_page)
            upsert(p, log, "asset_use", "cut_key", ck, uprops,
                   f"{ck} ← {Path(c['rel']).name}", f"ingest: 素材使用{ck}")
            # テロップチェック
            if c["text"]:
                chars = char_count(c["text"])
                tprops = {p.prop("telop", "video_id"): rt_payload(vid),
                          p.prop("telop", "line_no"): {"number": i + 1}}
                if p.prop("telop", "cut_id"):
                    tprops[p.prop("telop", "cut_id")] = rt_payload(ck)
                sp = p.schema("telop")["properties"]
                for name, val in (("文字数", chars), ("文字数(スペース除く)", chars),
                                  ("表示秒数", c["dur"]),
                                  ("字/秒", round(chars / float(c["dur"]), 2) if c["dur"] else None)):
                    if name in sp and val is not None:
                        tprops[name] = {"number": val}
                if vrel and p.prop("telop", "video_rel"):
                    tprops[p.prop("telop", "video_rel")] = vrel
                # 冪等キー: cut_id一致 → 無ければレガシー照合(同一動画+同一行テキスト)
                trows = cached_rows(p, "telop")
                hit = next((r for r in trows if (r.get("cut_id") or "") == ck), None)
                if not hit:
                    from notion_model import extract_video_id as _ev
                    hit = next((r for r in trows
                                if str(r.get("title") or "").strip() == str(c["text"]).strip()
                                and (_ev(str(r.get("legacy_video_name") or ""), {vid}) == vid
                                     or r.get("video_id") == vid)), None)
                if hit:
                    for prop_name, payload in tprops.items():
                        log.patch(hit["_id"], prop_name, payload, note=f"ingest: テロップ{ck}(レガシー行を更新)")
                    if p.prop("telop", "cut_id") and (hit.get("cut_id") or "") != ck:
                        log.patch(hit["_id"], p.prop("telop", "cut_id"), rt_payload(ck),
                                  note=f"ingest: テロップ{ck} cut_id正規化")
                else:
                    sp2 = p.schema("telop")["properties"]
                    ttl = next(k for k, v in sp2.items() if v["type"] == "title")
                    tprops2 = dict(tprops)
                    if p.prop("telop", "cut_id"):
                        tprops2[p.prop("telop", "cut_id")] = rt_payload(ck)
                    tprops2[ttl] = {"title": rt(str(c["text"]))}
                    created = log.create(p.dbs["telop"], tprops2, note=f"ingest: テロップ{ck}(新規)")
                    trows.append({"_id": created or "dry", "cut_id": ck, "title": str(c["text"]), "video_id": vid})
            # 素材DB(編集制約台帳)
            if "asset" in p.dbs:
                arows = cached_rows(p, "asset")
                sp = p.schema("asset")["properties"]
                aprops = {}
                if "素材rel" in sp:
                    aprops["素材rel"] = rt_payload(c["rel"])
                if "素材パス" in sp:
                    aprops["素材パス"] = rt_payload(c["rel"])
                info = clips.get(c["rel"])
                if info and "verdict要約" in sp:
                    ws = "; ".join(f"tin={w.get('tin')} {w.get('t_range') or ''} {w.get('notes') or ''}".strip()
                                   for w in info.get("windows", [])[:3])
                    aprops["verdict要約"] = rt_payload(f"{info.get('verdict')} | {ws}"[:1900])
                atitle = next(k for k, v in sp.items() if v["type"] == "title")
                hit = next((r for r in arows if (r["_props"].get("素材rel") and
                            "".join(x.get("plain_text", "") for x in r["_props"]["素材rel"]["rich_text"]) == c["rel"])
                           or (r["_props"].get("素材パス") and
                            "".join(x.get("plain_text", "") for x in r["_props"].get("素材パス", {}).get("rich_text", [])) == c["rel"])), None)
                if hit:
                    for prop_name, payload in aprops.items():
                        log.patch(hit["_id"], prop_name, payload, note=f"ingest: 素材{Path(c['rel']).name}(更新)")
                else:
                    aprops[atitle] = {"title": rt(Path(c["rel"]).name)}
                    created = log.create(p.dbs["asset"], aprops, note=f"ingest: 素材{Path(c['rel']).name}(新規)")
                    arows.append({"_id": created or "dry", "_props": {
                        "素材rel": {"rich_text": [{"plain_text": c["rel"]}]}}})
            cum += float(c["dur"] or 0)

    print(f"\n{'✅ APPLY' if a.apply else '(dry-run)'} patch/create数={log.count} / log={log.log_path}")
    print("次: レンダー時に notion_log_render.py / 納品前に notion_gate.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
