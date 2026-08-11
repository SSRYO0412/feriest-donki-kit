#!/bin/bash
# pr.sh — Premiere Pro CEP Bridge (hetpatel版) に .jsx をファイル渡しで投げる。
#
# usage:
#   pr.sh <script.jsx> [timeoutMs]
#   PR_BRIDGE_DIR=/tmp/premiere-mcp-bridge-kavy pr.sh probe.jsx 240000
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

"$PY" - "$SRC" "$D/command-$ID.json" "$ID" "$TO" "$WRAP" <<'PYEOF'
import json, sys, io
src = io.open(sys.argv[1], encoding="utf-8").read()
if sys.argv[5] != "0":
    src = "(function(){\n" + src + "\n})();\n"
payload = {"id": sys.argv[3], "script": src, "timeoutMs": int(sys.argv[4])}
with io.open(sys.argv[2], "w", encoding="utf-8") as f:
    f.write(json.dumps(payload, ensure_ascii=False))
PYEOF

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
