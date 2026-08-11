#!/usr/bin/env python3
"""トークン（@@FERIEST_ROOT@@ 等）を、このマシンの実パスへ解決する。

なぜトークンなのか
------------------
このキットの JSON と 案件 jsx は、素材SSDの場所・キットの置き場所・AME のバージョンが
マシンごとに違う。絶対パスを直に持つと別マシンで一切動かないので、根をトークンで持つ。

トークンのまま **コミットする** ことに意味がある:
  - projects/*.json の生成がマシン非依存になり `gen_projects.py --check` がどこでも通る
  - クライアントが素材をどこに置いても、根を1つ教えるだけでリンクできる

使い方
------
    python3 scripts/resolve_paths.py                      # 解決結果を一覧
    python3 scripts/resolve_paths.py projects/0801.json   # ファイル内のトークンを解決して出力

★pr.sh は同じ優先順位を **Bash で持っている**（ExtendScript へ投げる直前に置換する必要があり、
  Python を経由できないため）。優先順位を変えるときは両方直すこと:
  skill/donki-feriest/scripts/pr.sh の「トークン解決」ブロック。
"""
import os
import sys
import glob

KIT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FERIEST_ROOT = "/Volumes/Extreme SSD/FERIEST"
AME_GLOB = ("/Applications/Adobe Media Encoder */*.app/Contents/MediaIO/"
            "systempresets/*/H264 Match Source - High bitrate.epr")


def _conf():
    """.feriest-paths を読む。KEY="VALUE" 形式のみ受ける（sh としても読めるように）。"""
    path = os.environ.get("FERIEST_CONF", os.path.join(KIT_ROOT, ".feriest-paths"))
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def resolve():
    """優先順位: 環境変数 > .feriest-paths > 既定値/自動検出"""
    conf = _conf()

    def pick(name, fallback):
        return os.environ.get(name) or conf.get(name) or fallback

    ame = pick("AME_PRESET", "")
    if not ame:
        # ★AME はバージョンごとにパスが変わる。決め打ちにすると書き出し系が全滅する。
        hits = sorted(glob.glob(AME_GLOB))
        ame = hits[-1] if hits else ""

    return {
        "@@FERIEST_ROOT@@": pick("FERIEST_ROOT", DEFAULT_FERIEST_ROOT),
        "@@KIT_ROOT@@": pick("KIT_ROOT", KIT_ROOT),
        "@@BRIDGE_DIR@@": pick("PR_BRIDGE_DIR", "/tmp/premiere-mcp-bridge"),
        "@@AME_PRESET@@": ame,
    }


def main(argv):
    files = [a for a in argv if not a.startswith("-")]
    tokens = resolve()

    if not files:
        width = max(len(k) for k in tokens)
        bad = 0
        for k, v in tokens.items():
            mark = ""
            if not v:
                mark, bad = "  ← 未解決", bad + 1
            elif not os.path.exists(v):
                mark, bad = "  ← 実在しない", bad + 1
            print("%-*s = %s%s" % (width, k, v or "(空)", mark))
        if bad:
            print("\n%d 件が未解決です。.feriest-paths.example を写して "
                  ".feriest-paths を作るか、環境変数で指定してください。" % bad, file=sys.stderr)
            return 1
        return 0

    rc = 0
    for path in files:
        with open(path, encoding="utf-8") as f:
            body = f.read()
        for k, v in tokens.items():
            if k in body:
                if not v:
                    print("ERROR: %s を解決できません（%s）" % (k, path), file=sys.stderr)
                    rc = 1
                    continue
                body = body.replace(k, v)
        sys.stdout.write(body)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
