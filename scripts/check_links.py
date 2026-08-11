#!/usr/bin/env python3
"""着手前チェック — このマシンで案件を始められる状態か（素材リンク＋前提ソフト）。

なぜ要るか
----------
原本フッテージ（5商材 188本・34.5GB）はリポジトリに入っていない。クライアント側が別で持っている
原本と結ぶのが前提で、結び方は「FERIEST_ROOT を1つ教える」だけ。
ただし **リンク切れは Premiere 側で無言に起きる**（オフラインクリップとして黙って並ぶ）。
着手前にここで落としておかないと、組み上げた後に気づくことになる。

フォントも同じ性質を持つ。★**未インストールの書体は Premiere が警告なしに別書体へ差し替える**
（PROJECT-RULES 4節）。この案件で最大の失敗もそこから始まっているので、ここで見る。

    python3 scripts/check_links.py            # 全案件＋前提ソフト
    python3 scripts/check_links.py 0801       # 案件を指定
    python3 scripts/check_links.py --fix-dirs # 足りない書き出し先ディレクトリを作る
    python3 scripts/check_links.py --verify-media  # ★原本を全数照合（新規ダウンロード時）

★原本を今から用意する／ダウンロードした場合は `--verify-media` を必ず通すこと。
  同梱の在庫表 media_manifest.json（188クリップの名前と実尺）と突合して
  「落とし切れているか」を機械照合できる。
  Google Drive からの取得では **268本と出るが実際は315本** という取りこぼしを実際に踏んでいる
  （HANDBOOK 1節）。★**落とし切れていないのに落とし切れたように見える**のが怖いところ。

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


MANIFEST = os.path.join(KIT_ROOT, "data/asset_db/media_manifest.json")
DUR_TOL = 0.10   # 秒。DBの max(t1) と実尺の許容差（実測は12本抽出で全て 0.00 差）


def _expected_clips():
    """在庫表 media_manifest.json から「商材ごとにあるべきクリップ名と尺」を引く。

    尺は素材解析時の実測で、原本の実尺と一致することを確認済み（12本抽出で全て差 0.00秒）。
    ★在庫表がそのままチェックサムになる。
    """
    m = json.load(open(MANIFEST, encoding="utf-8"))
    out = {}
    for prod, v in m["products"].items():
        out[prod] = {_nfc(clip): dur for clip, dur in v["clips"].items()}
    return out


def _probe_dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def verify_media(tokens, want):
    """原本を全数照合する。名前の欠け／余りと、尺のズレ（＝途中で切れた・取り違え）を出す。"""
    from concurrent.futures import ThreadPoolExecutor

    if not os.path.exists(MANIFEST):
        print("  NG  在庫表が無い: %s" % MANIFEST)
        return 1
    if not shutil.which("ffprobe"):
        print("  NG  ffprobe が無いので尺を検査できない")
        return 1

    exp = _expected_clips()
    ng = 0
    print("\n== 原本の全数照合（在庫表と突合）==")

    for path in sorted(glob.glob(os.path.join(KIT_ROOT, "projects", "*.json"))):
        proj = json.load(open(path, encoding="utf-8"))
        vid, prod = proj["video_id"], proj["product"]
        if want and vid not in want:
            continue
        if prod not in exp:
            print("  NG  %s  在庫表に product が無い: %s" % (vid, prod))
            ng += 1
            continue

        media_dir = proj["media_dir"]
        for tok, val in tokens.items():
            media_dir = media_dir.replace(tok, val)
        if not os.path.isdir(media_dir):
            print("  NG  %s  素材フォルダが無い" % vid)
            ng += 1
            continue

        have = {}   # 拡張子を落とした名前 -> 実パス
        for b, p in _listdir_nfc(media_dir).items():
            have[os.path.splitext(b)[0]] = p

        wants = exp[prod]
        missing = sorted(set(wants) - set(have))
        extra = sorted(set(have) - set(wants))

        # ★尺は並列で測る。par15 を超えない（ExFAT のマウントが落ちる・恒久ルール5）
        targets = [(n, have[n], wants[n]) for n in sorted(set(wants) & set(have))]
        with ThreadPoolExecutor(max_workers=8) as ex:
            durs = list(ex.map(lambda t: _probe_dur(t[1]), targets))

        bad = []
        for (name, _p, t1), real in zip(targets, durs):
            if real is None:
                bad.append((name, t1, None))
            elif abs(real - t1) > DUR_TOL:
                bad.append((name, t1, real))

        okn = len(targets) - len(bad)
        mark = "OK" if not (missing or extra or bad) else "NG"
        print("  %s  %s  %-26s %d/%d本 照合" % (mark, vid, prod[:24], okn, len(wants)))
        for n in missing[:8]:
            print("      欠け      %s" % n)
        if len(missing) > 8:
            print("      欠け      …ほか %d本" % (len(missing) - 8))
        for n in extra[:5]:
            print("      DBに無い  %s" % n)
        for n, t1, real in bad[:8]:
            if real is None:
                print("      読めない  %s（破損の可能性）" % n)
            else:
                print("      尺ズレ    %s  DB %.2f秒 / 実測 %.2f秒（差 %+.2f）"
                      % (n, t1, real, real - t1))
        if missing or extra or bad:
            ng += 1

    if ng:
        print("\n  ★取りこぼし・破損の可能性があります。**落とし切れていないのに"
              "落とし切れたように見える**のが一番危ないので、ここは通してから着手してください。")
    return ng


def main(argv):
    fix_dirs = "--fix-dirs" in argv
    skip_fonts = "--no-fonts" in argv
    do_verify = "--verify-media" in argv
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

    if do_verify:
        ng += verify_media(tokens, want)
    else:
        print("\n  ヒント: 原本を今から用意した／ダウンロードした場合は "
              "--verify-media で全数照合できます")

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
