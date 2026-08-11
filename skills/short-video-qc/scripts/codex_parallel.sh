#!/bin/bash
# Codex 並列全数観察（★MCP経由は使わない。MCPサーバはリクエストを直列化するため）
#
# 実測（2026-07-29 / 17_v21.mov 2949枚）:
#   MCP経由（1本ずつ）      : 0.36枚/秒 → 2949枚で約2.3時間
#   CLI 10並列（20枚/本）   : 2.9枚/秒  → 約17分
#   CLI 20並列（148枚/本）  : 10.8枚/秒 → 4分33秒・被覆率100%（欠番0）
#   ★スライスは大きいほど良い。1プロセスの起動に約20秒かかるため、
#     20枚/本では0.35秒/枚、148枚/本では0.093秒/枚と約4倍の差が出る。
#
# 使い方:
#   codex_parallel.sh <フレームディレクトリ> <出力ディレクトリ> [並列数=20] [動画の説明]
#
# 前提:
#   - フレームは1パス抽出で作る（seekを毎回やる方式は桁違いに遅い）:
#       ffmpeg -v error -y -i <mp4> -vf "fps=30,scale=300:-2" -q:v 4 <dir>/f%05d.jpg
#     （2949枚で約2秒）
#   - model は gpt-5.5 固定。既定の gpt-5.3-codex は ChatGPT アカウントで400エラー
#
# 出力:
#   <出力ディレクトリ>/w<NN>.txt  … 各スライスの生応答
#   <出力ディレクトリ>/_done.log  … 各スライスの完了時刻
#   終了後に必ず coverage_verify.py で全ファイル名の列挙を機械照合すること
#     （COUNT= の自己申告だけでは水増しできるため）

set -u
SRC="${1:?フレームディレクトリを指定}"
OUT="${2:?出力ディレクトリを指定}"
NPAR="${3:-20}"
DESC="${4:-縦型ショート動画}"

[ -d "$SRC" ] || { echo "★フレームディレクトリが無い: $SRC"; exit 2; }
mkdir -p "$OUT"

# ---- スライス分割（既存のwNNがあれば作り直す）----
python3 - "$SRC" "$NPAR" <<'PY'
import sys, os, shutil, math, re
SRC, N = sys.argv[1], int(sys.argv[2])
# 既存スライスを解体して平坦化
for d in sorted(os.listdir(SRC)):
    p = os.path.join(SRC, d)
    if os.path.isdir(p) and re.fullmatch(r"w\d+", d):
        for f in os.listdir(p):
            shutil.move(os.path.join(p, f), os.path.join(SRC, f))
        os.rmdir(p)
files = sorted(f for f in os.listdir(SRC) if f.lower().endswith((".jpg", ".jpeg", ".png")))
if not files:
    print("★画像が無い"); sys.exit(2)
per = math.ceil(len(files) / N)
for s in range(N):
    chunk = files[s*per:(s+1)*per]
    if not chunk: continue
    d = os.path.join(SRC, f"w{s:02d}"); os.makedirs(d, exist_ok=True)
    for f in chunk:
        shutil.move(os.path.join(SRC, f), os.path.join(d, f))
print(f"{len(files)}枚 → {min(N, math.ceil(len(files)/per))}スライス × 最大{per}枚")
PY
[ $? -eq 0 ] || exit 2

# ---- 並列起動 ----
rm -f "$OUT/_done.log"
S=$(date +%s)
echo "並列 $NPAR 本 開始 $(date '+%H:%M:%S')"
for d in "$SRC"/w*/; do
  s=$(basename "$d")
  (
    codex exec --skip-git-repo-check --sandbox read-only -m gpt-5.5 \
      "$d のJPEG/PNG画像を全数見て、各画像を「ファイル名: 被写体 / テロップ文言」の1行で列挙してください。1枚も飛ばさないこと。テロップが無い場合は「テロップなし」と書いてください。最後に COUNT=<見た枚数>/<総枚数> を出力。これは${DESC}の全フレーム検品です。列挙のみで、レビューや指摘は不要です。" \
      > "$OUT/$s.txt" 2>&1
    echo "$s $(date +%s)" >> "$OUT/_done.log"
  ) &
done
wait
E=$(date +%s)
N_IMG=$(find "$SRC" -type f \( -name '*.jpg' -o -name '*.jpeg' -o -name '*.png' \) | wc -l | tr -d ' ')
echo "並列 終了 $(date '+%H:%M:%S') / 総所要 $((E-S))秒 / ${N_IMG}枚"
python3 -c "d=$E-$S; n=$N_IMG; print(f'  {d/n:.3f} 秒/枚 / スループット {n/d:.1f} 枚/秒')"
echo "★次は必ず coverage_verify.py で全ファイル名の列挙を機械照合すること（自己申告のCOUNTは証拠にならない）"
