#!/usr/bin/env python3
"""素材リンクの検査 — このマシンの FERIEST_ROOT で、案件が必要とする素材が揃うか。

なぜ要るか
----------
原本フッテージ（227本・38GB）はリポジトリに入っていない。クライアント側が別で持っている
原本と結ぶのが前提で、結び方は「FERIEST_ROOT を1つ教える」だけ。
ただし **リンク切れは Premiere 側で無言に起きる**（オフラインクリップとして黙って並ぶ）。
着手前にここで落としておかないと、組み上げた後に気づくことになる。

    python3 scripts/check_links.py            # 全案件
    python3 scripts/check_links.py 0801       # 案件を指定

★ExFAT の NFD 問題を踏むので、ファイル名は正規化して突き合わせる。
  日本語フォルダ名（例 20260807_新素材_8月掲載分）は NFC/NFD の差で
  os.path.exists が False を返すことがある——実際に踏んだ罠。
"""
import json
import os
import sys
import glob
import unicodedata

KIT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resolve_paths import resolve  # noqa: E402

VIDEO_EXT = (".mp4", ".mov")


def _nfc(s):
    return unicodedata.normalize("NFC", s)


def _listdir_nfc(d):
    """ディレクトリ内の動画を {正規化名: 実パス} で返す。AppleDouble は除外する。"""
    out = {}
    for p in glob.glob(os.path.join(d, "*")):
        b = os.path.basename(p)
        if b.startswith("._") or not b.lower().endswith(VIDEO_EXT):
            continue
        out[_nfc(b)] = p
    return out


def main(argv):
    tokens = resolve()
    root = tokens["@@FERIEST_ROOT@@"]
    print("FERIEST_ROOT = %s" % root)
    if not os.path.isdir(root):
        print("\n★見つかりません。素材SSDをマウントするか、.feriest-paths / 環境変数で"
              "実際の場所を指してください。", file=sys.stderr)
        return 1

    want = set(argv) or None
    ng = 0

    for path in sorted(glob.glob(os.path.join(KIT_ROOT, "projects", "*.json"))):
        proj = json.load(open(path, encoding="utf-8"))
        vid = proj["video_id"]
        if want and vid not in want:
            continue

        media_dir = proj["media_dir"]
        for tok, val in tokens.items():
            media_dir = media_dir.replace(tok, val)

        if not os.path.isdir(media_dir):
            # NFD 差で直接 isdir が落ちることがある。親を舐めて拾い直す。
            parent, name = os.path.dirname(media_dir), _nfc(os.path.basename(media_dir))
            hit = [p for p in glob.glob(os.path.join(parent, "*"))
                   if _nfc(os.path.basename(p)) == name] if os.path.isdir(parent) else []
            if hit:
                media_dir = hit[0]
            else:
                print("  NG  %s  素材フォルダが無い: %s" % (vid, media_dir))
                ng += 1
                continue

        found = _listdir_nfc(media_dir)
        print("  OK  %s  %-28s 素材 %d本" % (vid, proj["product"][:26], len(found)))

        # 0801 は設計が確定しているので、使用素材が実在するかまで見る。
        build = os.path.join(KIT_ROOT, "design", "build_%s.json" % vid)
        if not os.path.exists(build):
            continue
        srcs = sorted({s["src"] for s in json.load(open(build, encoding="utf-8"))["shots"]})
        missing = [s for s in srcs
                   if not any(k.startswith(_nfc(s) + ".") for k in found)]
        if missing:
            print("      NG  設計が参照する素材が無い: %s" % ", ".join(missing))
            ng += 1
        else:
            print("      使用素材 %d/%d 本すべて実在" % (len(srcs), len(srcs)))

    if ng:
        print("\n★%d 件リンクできません。このまま Premiere を開くとオフラインクリップになります。"
              % ng, file=sys.stderr)
        return 1
    print("\nすべてリンク可能です。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
