#!/usr/bin/env python3
"""着手前チェック — このマシンで案件を始められる状態か（素材リンク＋前提ソフト）。

なぜ要るか
----------
原本フッテージ（227本・38GB）はリポジトリに入っていない。クライアント側が別で持っている
原本と結ぶのが前提で、結び方は「FERIEST_ROOT を1つ教える」だけ。
ただし **リンク切れは Premiere 側で無言に起きる**（オフラインクリップとして黙って並ぶ）。
着手前にここで落としておかないと、組み上げた後に気づくことになる。

フォントも同じ性質を持つ。★**未インストールの書体は Premiere が警告なしに別書体へ差し替える**
（PROJECT-RULES 4節）。この案件で最大の失敗もそこから始まっているので、ここで見る。

    python3 scripts/check_links.py            # 全案件＋前提ソフト
    python3 scripts/check_links.py 0801       # 案件を指定
    python3 scripts/check_links.py --fix-dirs # 足りない書き出し先ディレクトリを作る

★ExFAT の NFD 問題を踏むので、ファイル名は正規化して突き合わせる。
  日本語フォルダ名（例 20260807_新素材_8月掲載分）は NFC/NFD の差で
  os.path.exists が False を返すことがある——実際に踏んだ罠。
"""
import json
import os
import sys
import glob
import shutil
import subprocess
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


FONTS = [("mplus-1p-heavy", "通常テロップ 68.948 / 商品名2行組"),
         ("HeiseiMinStd-W9", "感嘆・言い切り 109・129"),
         ("Makinas-4-Square", "ロックアップ（左下の常時表示）35")]

# jsx が書き出し先として使うディレクトリ。無いと exportAsMediaDirect が落ちる
# （98本中 Folder.create() を持つのは1本だけ）。
OUT_DIRS = ["02_work/premiere/verify_20260809", "03_render/premiere_202608"]

CEP_DIR = os.path.expanduser(
    "~/Library/Application Support/Adobe/CEP/extensions/MCPBridgeCEP")


def _fonts_installed():
    """Adobe Fonts で有効化済みかを見る。★未インストールの書体は Premiere が
    警告なしに別書体へ差し替えるので、ここで検出する価値が高い（10秒ほどかかる）。"""
    try:
        out = subprocess.run(["system_profiler", "SPFontsDataType"],
                             capture_output=True, text=True, timeout=120).stdout.lower()
    except Exception:
        return None
    return {name: (name.lower() in out) for name, _ in FONTS}


def check_prereq(tokens, fix_dirs, skip_fonts):
    """前提ソフト・拡張・書き出し先。NG件数を返す。"""
    root = tokens["@@FERIEST_ROOT@@"]
    ng = 0
    print("\n== 前提 ==")

    for cmd in ("ffmpeg", "ffprobe"):
        if shutil.which(cmd):
            print("  OK  %s" % cmd)
        else:
            print("  NG  %s が無い（検品スクリプトが動かない）" % cmd)
            ng += 1

    pr = sorted(glob.glob("/Applications/Adobe Premiere Pro *"))
    print("  %s  Premiere Pro %s" % ("OK" if pr else "NG",
                                     os.path.basename(pr[-1]) if pr else "が見つからない"))
    ng += 0 if pr else 1

    ame = tokens["@@AME_PRESET@@"]
    if ame and os.path.exists(ame):
        print("  OK  AME 書き出しプリセット（%s）"
              % ame.split("/Applications/")[-1].split("/")[0])
    else:
        print("  NG  AME 書き出しプリセットが見つからない（AME_PRESET で明示できる）")
        ng += 1

    if os.path.isdir(CEP_DIR):
        print("  OK  CEP拡張 MCPBridgeCEP を導入済み")
    else:
        print("  NG  CEP拡張が未導入 → ditto skill/donki-feriest/assets/MCPBridgeCEP "
              "\"%s\"" % CEP_DIR)
        ng += 1

    dbg = []
    for v in ("10", "11", "12"):
        r = subprocess.run(["defaults", "read", "com.adobe.CSXS." + v, "PlayerDebugMode"],
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip() in ("1", "true"):
            dbg.append(v)
    if dbg:
        print("  OK  PlayerDebugMode=1（CSXS %s）" % "/".join(dbg))
    else:
        print("  NG  PlayerDebugMode が未設定 → defaults write com.adobe.CSXS.12 "
              "PlayerDebugMode 1（11/10 も入れる）")
        ng += 1

    if skip_fonts:
        print("  --  フォント3種の確認は省略（--no-fonts）")
    else:
        print("  ..  フォント3種を確認中（10秒ほどかかります）")
        got = _fonts_installed()
        if got is None:
            print("  NG  フォントを確認できませんでした（system_profiler が使えない）")
            ng += 1
        else:
            for name, use in FONTS:
                if got[name]:
                    print("  OK  %-18s %s" % (name, use))
                else:
                    print("  NG  %-18s 未有効化。★Premiere は警告なしに別書体へ差し替える"
                          % name)
                    ng += 1

    print("\n== 書き出し先（FERIEST_ROOT 配下）==")
    for d in OUT_DIRS:
        p = os.path.join(root, d)
        if os.path.isdir(p):
            print("  OK  %s" % d)
        elif fix_dirs:
            os.makedirs(p, exist_ok=True)
            print("  作成  %s" % d)
        else:
            print("  NG  %s が無い → --fix-dirs で作成できる" % d)
            ng += 1

    p = os.path.join(root, "02_work/premiere", "FERIEST_0801_ebi_v1.prproj")
    if os.path.exists(p):
        print("  OK  0801 の prproj が FERIEST_ROOT/02_work/premiere/ に置かれている")
    else:
        print("  --  0801 の prproj が未配置。0801 を開くなら先にコピーする:")
        print("        cp work/premiere/FERIEST_0801_ebi_v1.prproj "
              "\"%s/02_work/premiere/\"" % root)
        print("      ★リポジトリ内の位置のまま開くと相対パスが外れて全クリップが"
              "オフラインになる")
    return ng


def main(argv):
    fix_dirs = "--fix-dirs" in argv
    skip_fonts = "--no-fonts" in argv
    argv = [a for a in argv if not a.startswith("-")]

    tokens = resolve()
    root = tokens["@@FERIEST_ROOT@@"]
    print("FERIEST_ROOT = %s" % root)
    if not os.path.isdir(root):
        print("\n★見つかりません。素材SSDをマウントするか、.feriest-paths / 環境変数で"
              "実際の場所を指してください。", file=sys.stderr)
        return 1

    want = set(argv) or None
    ng = 0
    print("\n== 素材 ==")

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

    ng += check_prereq(tokens, fix_dirs, skip_fonts)

    if ng:
        print("\n★%d 件が未達です。このまま着手すると、リンク切れや書体の無言差し替えに"
              "気づかないまま進みます。HANDOFF.md の該当節を見てください。"
              % ng, file=sys.stderr)
        return 1
    print("\nすべてリンク可能です。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
