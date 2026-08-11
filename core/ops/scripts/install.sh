#!/bin/bash
# install.sh — VIDEO OPS の導入（配布物のルートで実行する）
#
# やること（全て冪等・既存を壊さない）:
#   [1] 依存の確認（必須と任意を分けて報告）
#   [2] `vops` を PATH の通った場所へリンク
#   [3] `~/.claude/skills/_video-core` → <root>/core のリンク（正本の実行時参照）
#   [4] 各スキルを ~/.claude/skills/ へリンク（Claude Code から見えるようにする）
#   [5] SessionStart hook を ~/.claude/settings.json へマージ（既存設定は保全）
#   [6] 音声環境（任意・--with-audio）
#   [7] 導通確認（vops doctor / check）
#
# 使い方:
#   ./install.sh                 # 標準導入
#   ./install.sh --with-audio    # 音声解析の venv も作る（数分かかる）
#   ./install.sh --prefix ~/bin  # vops の設置先（既定: ~/.local/bin）
#   ./install.sh --home <dir>    # 導入先ホーム（既定: $HOME）。検証や非標準ホーム用
#   ./install.sh --dry-run       # 何をするかだけ表示
set -u

# ★このスクリプトは2箇所に置かれる: 正本 core/ops/scripts/install.sh と、
#   クライアントが最初に叩くルート直下の複製。どちらから起動されても配布物ルートを
#   特定できるよう、自分の位置から上へ辿って core/ を探す（決め打ちしない）
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT=""
d="$SELF_DIR"
for _ in 1 2 3 4; do
  if [ -d "$d/core/ops" ]; then ROOT="$d"; break; fi
  d="$(dirname "$d")"
done
[ -n "$ROOT" ] || { echo "★配布物のルートが特定できない（core/ops が見つからない）: $SELF_DIR から上へ探索" >&2; exit 2; }

# 導入先ホーム。--home で差し替え可能にしてあるのは、
# ①クリーン環境での導通検証 ②非標準ホーム運用 の2つを成立させるため
HOME_DIR="$HOME"
PREFIX=""
WITH_AUDIO=0
DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --with-audio) WITH_AUDIO=1 ;;
    --prefix) PREFIX="$2"; shift ;;
    --home) HOME_DIR="$2"; shift ;;
    --dry-run) DRY=1 ;;
    -h|--help) sed -n '2,21p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "不明な引数: $1" >&2; exit 2 ;;
  esac
  shift
done
[ -n "$PREFIX" ] || PREFIX="$HOME_DIR/.local/bin"

run() { if [ "$DRY" = 1 ]; then echo "  [dry-run] $*"; else eval "$@"; fi; }
ok()   { echo "  ✅ $*"; }
warn() { echo "  ⚠  $*"; }
ng()   { echo "  ❌ $*"; }

echo "=== VIDEO OPS 導入 ==="
echo "配布物: ${ROOT}"
[ -f "$ROOT/VERSION" ] && echo "バージョン: $(cat "$ROOT/VERSION")"
echo

# ---------------------------------------------------------------- [1] 依存
echo "[1] 依存の確認"
MISSING=0
check_req() {
  if command -v "$1" >/dev/null 2>&1; then ok "$1 ($(command -v "$1"))"; else ng "$1 が無い — $2"; MISSING=1; fi
}
check_opt() {
  if command -v "$1" >/dev/null 2>&1; then ok "$1（任意）"; else warn "$1 が無い — $2"; fi
}
check_req python3 "必須。python.org か Homebrew で導入する"
check_req git     "必須。正本の更新に使う"
check_opt ffmpeg  "音声・映像の実測に必要。無いと audio 系と検品の一部が動かない"

if command -v python3 >/dev/null 2>&1; then
  PYV="$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null || echo 0.0)"
  case "$PYV" in
    3.1[0-9]|3.[2-9][0-9]) ok "python3 $PYV" ;;
    *) warn "python3 $PYV — 3.10以上を推奨（音声系は3.10〜3.13）" ;;
  esac
fi
[ "$MISSING" = 1 ] && { echo; echo "★必須の依存が足りないため中断した。上記を導入してから再実行する。" >&2; exit 2; }

# ★配布物が git 作業ツリーかどうかで「更新できるか」が決まる。
#   tar 展開だと自動追従(doctor --fix)も手動更新も経路が無く、初回の中身で固定される。
if git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  ok "git リポジトリとして配置されている（更新・自動追従が使える）"
else
  warn "git リポジトリではない（tar展開？）— 自動更新が使えず、この中身で固定される"
  warn "  更新を受け取るには配布元を clone して、そちらへ install.sh をやり直す"
fi
echo

# ---------------------------------------------------------------- [2] vops
echo "[2] vops コマンドの設置"
run "mkdir -p '$PREFIX'"
run "ln -sfn '$ROOT/core/ops/bin/vops' '$PREFIX/vops'"
ok "$PREFIX/vops → core/ops/bin/vops"
case ":${PATH}:" in
  *":${PREFIX}:"*) ok "PATH に ${PREFIX} が入っている" ;;
  *) warn "PATH に ${PREFIX} が無い。シェルの設定に追記する: export PATH=\"${PREFIX}:\$PATH\"" ;;
esac
echo

# ---------------------------------------------------------------- [3][4] Claude Code 連携
echo "[3] 正本リンク（_video-core）"
SK="$HOME_DIR/.claude/skills"
run "mkdir -p '$SK'"
if [ -e "$SK/_video-core" ] && [ ! -L "$SK/_video-core" ]; then
  ng "$SK/_video-core が実体ディレクトリとして存在する。退避してから再実行する"
  exit 2
fi
run "ln -sfn '$ROOT/core' '$SK/_video-core'"
ok "$SK/_video-core → ${ROOT}/core"
echo

echo "[4] スキルの登録"
COUNT=0
if [ -d "$ROOT/skills" ]; then
  for d in "$ROOT/skills"/*/; do
    [ -d "$d" ] || continue
    n="$(basename "$d")"
    if [ -e "$SK/$n" ] && [ ! -L "$SK/$n" ]; then
      warn "$n は実体ディレクトリとして既存 — 上書きせず飛ばした（手動で確認する）"
      continue
    fi
    run "ln -sfn '${d%/}' '$SK/$n'"
    COUNT=$((COUNT+1))
  done
fi
ok "${COUNT} 個のスキルをリンクした（リンクなので今後の更新は自動反映）"
echo

# ---------------------------------------------------------------- [5] hook
echo "[4b] サポート層（会社別スキル・任意）"
SUPPORT_DIR="$HOME_DIR/video-ops-support"
if [ -d "$SUPPORT_DIR" ]; then
  CNT=0
  for d in "$SUPPORT_DIR"/*/; do
    [ -d "$d" ] || continue
    n="$(basename "$d")"
    case "$n" in .*) continue ;; esac
    if [ -e "$SK/$n" ] && [ ! -L "$SK/$n" ]; then
      warn "$n は実体ディレクトリとして既存 — 上書きせず飛ばした"
      continue
    fi
    run "ln -sfn '${d%/}' '$SK/$n'"
    CNT=$((CNT+1))
  done
  ok "サポート層から ${CNT} 個をリンク（更新は手動: cd $SUPPORT_DIR && git pull）"
else
  warn "サポート層なし（配布元から support repo を受領したら $SUPPORT_DIR へ clone して再実行）"
fi
echo

echo "[4c] ライセンス設定ディレクトリ"
run "mkdir -p '$HOME_DIR/.config/video-ops'"
if [ -f "$HOME_DIR/.config/video-ops/license.json" ]; then
  ok "license.json 配置済み"
else
  warn "license.json 未配置。配布元から受領したら $HOME_DIR/.config/video-ops/license.json へ置く"
fi
echo

echo "[5] SessionStart hook（正本の自動追従）"
SETTINGS="$HOME_DIR/.claude/settings.json"
# ★hook コマンドは HOME_DIR を実パスで焼き込む（旧実装は ~ 決め打ちで --home 指定と不整合だった）
HOOK_CMD="test -f $HOME_DIR/.claude/skills/_video-core/ops/scripts/doctor.py && python3 $HOME_DIR/.claude/skills/_video-core/ops/scripts/doctor.py --fix --quiet 2>&1 || true"
if [ "$DRY" = 1 ]; then
  echo "  [dry-run] $SETTINGS へ SessionStart hook をマージ"
else
  python3 - "$SETTINGS" "$HOOK_CMD" <<'PYEOF'
import json, os, sys
path, cmd = sys.argv[1], sys.argv[2]
os.makedirs(os.path.dirname(path), exist_ok=True)
data = {}
if os.path.exists(path):
    try:
        data = json.load(open(path))
    except Exception as e:
        print(f"  ❌ {path} が壊れていて読めない（{e}）。手で直してから再実行する")
        sys.exit(1)
    # 破壊しないよう必ずバックアップ
    import shutil, time
    bak = f"{path}.bak-{time.strftime('%Y%m%d%H%M%S')}"
    shutil.copy2(path, bak)
    print(f"  ✅ 既存設定をバックアップ: {bak}")
hooks = data.setdefault("hooks", {})
ss = hooks.setdefault("SessionStart", [])
# 重複判定はパス形式に依存させない（旧導入は ~ 形式・新導入は絶対パス形式のため、
# コマンド全文一致だと二重配線になる）。doctor 呼び出しの有無で判定する
marker = "doctor.py --fix --quiet"
if any(marker in (h.get("command") or "") for grp in ss for h in (grp.get("hooks") or [])):
    print("  ✅ hook は既に配線済み（重複追加しない）")
else:
    ss.append({"hooks": [{"type": "command", "command": cmd,
                          "timeout": 30, "statusMessage": "VIDEO OPS 正本を確認中"}]})
    json.dump(data, open(path, "w"), ensure_ascii=False, indent=2)
    print("  ✅ SessionStart hook を追加（既存の設定は保全）")
PYEOF
fi
echo

# ---------------------------------------------------------------- [6] 音声
echo "[6] 音声解析の環境（任意）"
VENV="$HOME_DIR/venvs/audio-precision"
if [ "$WITH_AUDIO" = 1 ]; then
  if [ -x "$VENV/bin/python" ]; then
    ok "既に存在: $VENV"
  else
    run "python3 -m venv '$VENV'"
    run "'$VENV/bin/pip' install -q --upgrade pip"
    run "'$VENV/bin/pip' install -q faster-whisper budoux 'fugashi[unidic-lite]' soundfile numpy scipy praat-parselmouth ten-vad"
    ok "作成: $VENV"
  fi
else
  if [ -x "$VENV/bin/python" ]; then ok "既に存在: $VENV"
  else warn "未構築。音声機能を使うなら ./install.sh --with-audio（数分かかる）"; fi
fi
echo

# ---------------------------------------------------------------- [7] 導通
echo "[7] 導通確認"
if [ "$DRY" = 1 ]; then
  echo "  [dry-run] vops doctor / vops check"
else
  "$ROOT/core/ops/bin/vops" version | sed 's/^/  /'
  # ★今導入したリンクを検査する。--link を省くと既定($HOME基準)を見に行き、
  #   別の場所に入っている正本を検査してしまう（--home 検証時に実際に踏んだ）
  "$ROOT/core/ops/bin/vops" doctor --link "$SK/_video-core" 2>&1 | sed 's/^/  /' || true
fi
echo
echo "=== 導入完了 ==="
echo "  vops help          コマンド一覧"
echo "  vops status        現在の状態"
echo "  INSTALL.md         詳しい手順とトラブルシュート"
# ★最終行を `[ cond ] && cmd` にしない: cond が偽だとそれがスクリプトの終了コードになり、
#   実導入（DRY=0）が成功しても rc=1 で「失敗」に見える（S7 E2E で実際に踏んだ）
if [ "$DRY" = 1 ]; then echo "（--dry-run のため何も変更していない）"; fi
exit 0
