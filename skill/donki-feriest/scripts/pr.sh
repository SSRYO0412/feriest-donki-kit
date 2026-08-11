#!/bin/bash
# pr.sh — Premiere Pro CEP Bridge (hetpatel版) に .jsx をファイル渡しで投げる。
#
# usage:
#   pr.sh <script.jsx> [timeoutMs]
#   PR_BRIDGE_DIR=/tmp/premiere-mcp-bridge-kavy pr.sh probe.jsx 240000
#
# 案件 jsx（work/jsx_20260809/）は絶対パスをトークンで持つ。実パスは投入直前に解決する:
#   @@FERIEST_ROOT@@  素材SSDの根        env FERIEST_ROOT / .feriest-paths / 既定 /Volumes/Extreme SSD/FERIEST
#   @@KIT_ROOT@@      このキットの根      pr.sh の位置から自動導出（env KIT_ROOT で上書き可）
#   @@BRIDGE_DIR@@    ブリッジの受け渡し  PR_BRIDGE_DIR（既定 /tmp/premiere-mcp-bridge）
#   @@AME_PRESET@@    書き出しプリセット  env AME_PRESET / /Applications から自動検出
#
# 前提: Premiere で `ウィンドウ > 拡張機能 > MCP Bridge (CEP)` を開き
#       Temp Directory を確認 → Save Configuration → **Start Bridge** 済みであること。
#       これをやらないと応答が来ず TIMEOUT になる（毎セッション手動・詳細は SKILL.md）。
#
# 設計上の約束:
#   - 標準出力にはブリッジの生レスポンス JSON をそのまま出す
#   - スクリプトの実結果は .jsx 側から <bridge dir>/<好きな名前>.txt に書き出して Bash で読む
#     （evalScript の戻り値は長いと切れる。かつ execute_extendscript は戻り値を返さない）
#   - 終了コード: 0=応答あり / 1=引数や環境の誤り / 2=タイムアウト（★処理は成功していることがある）

set -u

D="${PR_BRIDGE_DIR:-/tmp/premiere-mcp-bridge}"
SRC="${1:-}"
TO="${2:-120000}"

if [ -z "$SRC" ]; then
  echo "usage: pr.sh <script.jsx> [timeoutMs]" >&2
  exit 1
fi
if [ ! -f "$SRC" ]; then
  echo "ERROR: script not found: $SRC" >&2
  exit 1
fi
if [ ! -d "$D" ]; then
  echo "ERROR: bridge dir not found: $D" >&2
  echo "  → Premiere の MCP Bridge (CEP) パネルで Temp Directory を作成し Save Configuration してください" >&2
  echo "  → /tmp はOS再起動で消えます" >&2
  exit 1
fi

# ★ブリッジの validateScript が問答無用で弾く語を、投げる前に検出する。
#   弾かれると返るのは "Script validation failed" だけで、どの語が原因か分からない。
#   コメント内でもアウト。prq.py は投入時に検査しているが、pr.sh は素通りだったため
#   実際に `eval(` を書いて時間を溶かした（2026-08-08）。同じ検査をここにも置く。
BAD=""
for w in 'require(' 'process.' 'eval(' 'new Function(' '__dirname' '__filename' 'child_process'; do
  if grep -qF -- "$w" "$SRC"; then BAD="$BAD $w"; fi
done
if [ -n "$BAD" ]; then
  echo "ERROR: ブリッジの validateScript に弾かれる語が入っています:$BAD" >&2
  echo "  （コメント内でもアウト。書き換えてから投げてください）" >&2
  echo "  例: JSONの解析に eval( を使わない → 正規表現で取り出す" >&2
  exit 1
fi

# ── トークン解決 ────────────────────────────────────────────────
# 案件の .jsx はマシン非依存にするため絶対パスを @@…@@ で持つ。投入直前にここで実パスへ戻す。
#
# ★ExtendScript 側で環境変数を読む手は使えない（2つの理由で塞がっている）:
#   1. Premiere は GUI から起動するのでシェルの export が届かない
#   2. ブリッジの validateScript が `process.` をコメント内でも弾く
#   したがって「投入直前に Bash 側で置換する」のが唯一の経路。
#
# 優先順位: 環境変数 > 設定ファイル(.feriest-paths) > 既定値/自動検出
KIT_ROOT_ENV="${KIT_ROOT:-}"
FERIEST_ROOT_ENV="${FERIEST_ROOT:-}"
AME_PRESET_ENV="${AME_PRESET:-}"

KIT_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
CONF="${FERIEST_CONF:-$KIT_ROOT/.feriest-paths}"
# shellcheck source=/dev/null
[ -f "$CONF" ] && . "$CONF"

[ -n "$KIT_ROOT_ENV" ]     && KIT_ROOT="$KIT_ROOT_ENV"
[ -n "$FERIEST_ROOT_ENV" ] && FERIEST_ROOT="$FERIEST_ROOT_ENV"
[ -n "$AME_PRESET_ENV" ]   && AME_PRESET="$AME_PRESET_ENV"

FERIEST_ROOT="${FERIEST_ROOT:-/Volumes/Extreme SSD/FERIEST}"

# ★AME はバージョンごとにパスが変わる。2026 決め打ちだと他バージョンで書き出し系が全滅する。
#   実在するものを列挙して最新を採る。
if [ -z "${AME_PRESET:-}" ]; then
  AME_PRESET="$(ls -d "/Applications/Adobe Media Encoder "*/*.app/Contents/MediaIO/systempresets/*/"H264 Match Source - High bitrate.epr" 2>/dev/null | sort | tail -1)"
fi
AME_PRESET="${AME_PRESET:-}"

# 置換値に " や \ が混ざると jsx の文字列リテラルが壊れる。先に止める。
for v in "$KIT_ROOT" "$FERIEST_ROOT" "$D" "$AME_PRESET"; do
  case "$v" in
    *'"'*|*'\'*) echo "ERROR: パスに \" または \\ が含まれています: $v" >&2; exit 1;;
  esac
done

# 素材の根が実在しないまま投げると Premiere 側で無言のリンク切れになる。手前で落とす。
if grep -qF '@@FERIEST_ROOT@@' "$SRC" && [ ! -d "$FERIEST_ROOT" ]; then
  echo "ERROR: FERIEST_ROOT が見つかりません: $FERIEST_ROOT" >&2
  echo "  → export FERIEST_ROOT=/path/to/FERIEST するか $KIT_ROOT/.feriest-paths に書いてください" >&2
  echo "  → 雛形: $KIT_ROOT/.feriest-paths.example" >&2
  exit 1
fi

# id は応答ファイル名と対応する。衝突しないよう秒＋乱数。
ID="c$(date +%s)$RANDOM"

# JSON は python3 で組む（jsx 内の改行・引用符・日本語を正しくエスケープするため）。
# python3 は macOS 標準（Command Line Tools）にある。無い場合は PR_PYTHON で指定。
PY="${PR_PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "ERROR: python3 not found. PR_PYTHON=/path/to/python3 で指定してください" >&2
  exit 1
fi

# ★トップレベルの `return` は構文エラーになる。
#   CEP はスクリプトをそのまま evalScript に渡すだけで、関数に包んでくれない。
#   包まないまま `return` を書くと、返ってくるのは
#   "ExtendScript execution failed via CEP evalScript()" だけで原因が分からない（実際に踏んだ）。
#   templates/ の .jsx は `return` で中断・返却する書き方なので、既定で包む。
#   包むと **末尾の式は返らない**ので、末尾も `return <式>;` で書くこと。
#   包みたくない使い捨てスクリプト（末尾が裸の式）は PR_WRAP=0 を付ける。
WRAP="${PR_WRAP:-1}"

if ! "$PY" - "$SRC" "$D/command-$ID.json" "$ID" "$TO" "$WRAP" \
       "$FERIEST_ROOT" "$KIT_ROOT" "$D" "$AME_PRESET" <<'PYEOF'
import json, sys, io, re
src = io.open(sys.argv[1], encoding="utf-8").read()

# トークン → 実パス。未解決のまま投げると Premiere 側で無言に失敗するので必ずここで止める。
TOKENS = [("@@FERIEST_ROOT@@", sys.argv[6], "FERIEST_ROOT"),
          ("@@KIT_ROOT@@",     sys.argv[7], "KIT_ROOT"),
          ("@@BRIDGE_DIR@@",   sys.argv[8], "PR_BRIDGE_DIR"),
          ("@@AME_PRESET@@",   sys.argv[9], "AME_PRESET")]
for tok, val, name in TOKENS:
    if tok in src:
        if not val:
            sys.stderr.write("ERROR: %s を解決できません（%s が未設定）\n" % (tok, name))
            if name == "AME_PRESET":
                sys.stderr.write("  → Adobe Media Encoder が見つかりません。"
                                 "export AME_PRESET=/path/to/*.epr で明示してください\n")
            sys.exit(1)
        src = src.replace(tok, val)

left = sorted(set(re.findall(r"@@[A-Z0-9_]+@@", src)))
if left:
    sys.stderr.write("ERROR: 未知のトークンが残っています: %s\n" % " ".join(left))
    sys.exit(1)

if sys.argv[5] != "0":
    src = "(function(){\n" + src + "\n})();\n"
payload = {"id": sys.argv[3], "script": src, "timeoutMs": int(sys.argv[4])}
with io.open(sys.argv[2], "w", encoding="utf-8") as f:
    f.write(json.dumps(payload, ensure_ascii=False))
PYEOF
then
  echo "  → トークンの解決に失敗しました。投入していません。" >&2
  exit 1
fi

# 1秒間隔で応答ファイルを待つ
LIMIT=$(( TO / 1000 ))
[ "$LIMIT" -lt 1 ] && LIMIT=1
for _ in $(seq 1 "$LIMIT"); do
  if [ -f "$D/response-$ID.json" ]; then
    cat "$D/response-$ID.json"
    echo
    exit 0
  fi
  sleep 1
done

echo "TIMEOUT $ID"
echo "  ★タイムアウト＝失敗ではない。作り直す前に必ず読み戻して現状を確認する。" >&2
echo "  未消費の command-*.json が溜まっている場合は Start Bridge が落ちている:" >&2
ls -lat "$D" 2>/dev/null | head -6 >&2
exit 2
