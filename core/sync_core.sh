#!/bin/bash
# _video-core 同期スクリプト — 動画クローン系スキル群の共通ファイルの正本管理
#
# 使い方:
#   sync_core.sh check                 # 全スキル×全coreファイルの drift レポート（変更しない）
#   sync_core.sh push [skill]          # core → スキルへ配布（省略時は全対象スキル）
#   sync_core.sh pull <skill> <path>   # スキル側の改善を core へ回収（path 例: references/tone-library.md）
#
#   sync_core.sh snapshot check [skill]   # repo skills/ とローカル ~/.claude/skills の drift レポート
#   sync_core.sh snapshot pull  [skill]   # ローカルの改善・新規ファイルを repo へ回収（旧方向）
#   sync_core.sh snapshot apply [skill]   # repo の内容をローカルへ配布（新方向・merge後に実行）
#   ※ DISTRIBUTION.md §5: 「drift なし」と報告できるのは check と snapshot check の両方PASSのみ。
#   ※ 除外パターンは core/ops/snapshot_ignore.txt（意図的なローカル専用ファイルを登録）
#
# ルール:
#  - mode=existing-only のグループは「配布先に同名ファイルが既にある場合のみ」上書き（新規作成しない）
#  - mode=create は無ければ作成（PRINCIPLES.md）
#  - skill固有で意図的に分岐しているファイルは core-manifest.json に載せない（同期しない）
#  - snapshot はどの方向でも削除しない（片側にしか無いファイルはレポート/コピーのみ）
set -euo pipefail
CORE_DIR="$(cd "$(dirname "$0")" && pwd)"
export CORE_DIR
exec python3 - "$@" <<'PYEOF'
import json, hashlib, os, shutil, subprocess, sys
from pathlib import Path

CORE = Path(os.environ["CORE_DIR"])
manifest = json.loads((CORE / "core-manifest.json").read_text())
SKILLS = Path(manifest["skills_root"].replace("~", str(Path.home())))

def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()

MISSING_SRC = []   # 配布元ディレクトリごと存在しないグループ

IGNORE_DIRS = {"__pycache__", ".git", ".venv", "node_modules", ".DS_Store"}

RUNTIME_FILES = {".DS_Store", ".last_harvest"}  # 生成物・運用状態ファイル（配布物ではない）


def IGNORED(p) -> bool:
    """生成物・VCS・依存物・運用状態は同期対象にしない。
    .last_harvest は収穫チェックのマーカーで DISTRIBUTION.md §2 の非配布物。
    ディレクトリ丸ごと配布するグループに置いてあるため、明示除外が要る。"""
    if p.name in RUNTIME_FILES or p.suffix in (".pyc", ".pyo"):
        return True
    return any(part in IGNORE_DIRS for part in p.parts)

def iter_pairs():
    """yield (group, core_file, target_skill, target_path, mode)"""
    for gname, g in manifest["groups"].items():
        src = CORE / g["src"]
        # ★配布元が丸ごと無い場合、rglob は「空」を返すだけでエラーにならない。
        #   放置するとそのグループが黙って検査対象から消え、未検査なのに
        #   「drift なし」と表示される（repo に一部グループしか置いていない時に実際に起きた）。
        if not src.is_dir():
            MISSING_SRC.append((gname, g["src"], len(g["targets"])))
            continue
        if "files" in g:
            files = [src / f for f in g["files"]]
        else:
            # ★生成物は配布しない。__pycache__ を除外していなかったため .pyc が
            #   配布物として数えられ、実際に3スキルへ36個ばら撒かれていた（2026-08-08 発見）
            files = [p for p in src.rglob("*") if p.is_file() and not IGNORED(p)]
        dest_map = g.get("dest_map", {})
        for cf in files:
            if not cf.exists():
                print(f"WARN: core file missing (manifest stale?): {cf}", file=sys.stderr)
                continue
            rel = str(cf.relative_to(src))
            dest_rel = dest_map.get(rel, rel)
            for skill in g["targets"]:
                yield gname, cf, skill, SKILLS / skill / dest_rel, g["mode"]

def runtime_core_diff():
    """★実行時に読まれる正本（`<skills>/_video-core` の実体）と、このスクリプトが検査している
    CORE が同じ内容かを確かめる。

    なぜ要るか（2026-08-10 実際に発生）: スキル文書は `_video-core/...` を正本として参照するが、
    その実体はシンボリックリンク先（通常はメインチェックアウトの作業ツリー）である。
    worktree やブランチ違いの core から check を回すと、**スキルが実際に読むものとは別の core**
    について「drift なし」と報告してしまう。実際、メインチェックアウトが9コミット古いまま
    （core/audio が存在しない・PRINCIPLES §15 が無い）で、全スキルが旧正本を読んでいたのに
    check は drift 0 を返していた。

    戻り値: (実体パス or None, 食い違いファイルの一覧)
    """
    link = SKILLS / "_video-core"
    if not link.exists():
        return None, []          # symlink 運用でない環境では検査しない
    rt = link.resolve()
    if rt == CORE.resolve():
        return rt, []            # 同一実体＝問題なし
    diffs = []
    for p in CORE.rglob("*"):
        rel = p.relative_to(CORE)
        if not p.is_file() or IGNORED(rel) or IGNORED(p):
            continue
        q = rt / rel
        if not q.exists():
            diffs.append(f"{rel}  (実行時側に無い)")
        elif md5(p) != md5(q):
            diffs.append(str(rel))
    return rt, diffs


def check():
    drift, absent, same = [], [], 0
    for gname, cf, skill, tp, mode in iter_pairs():
        if not tp.exists():
            absent.append((gname, skill, str(tp.relative_to(SKILLS / skill)), mode))
        elif md5(cf) != md5(tp):
            drift.append((gname, skill, str(tp.relative_to(SKILLS / skill))))
        else:
            same += 1
    print(f"SAME: {same}")
    if drift:
        print(f"\nDRIFT ({len(drift)}):")
        for g, s, r in drift:
            print(f"  [{g}] {s}/{r}")
    if absent:
        print(f"\nABSENT ({len(absent)}):  (existing-onlyグループでは配布されない / createグループはpushで作成される)")
        for g, s, r, m in absent:
            print(f"  [{g}:{m}] {s}/{r}")
    if MISSING_SRC:
        n = sum(t for _, _, t in MISSING_SRC)
        print(f"\n★配布元が無いグループ ({len(MISSING_SRC)}): このcoreは不完全で、下記は一切検査していない")
        for gname, src, t in MISSING_SRC:
            print(f"  [{gname}] {src}/ が無い（配布先{t}スキルぶん未検査）")
        print("  → この状態の『drift なし』は無効。配布元を揃えてから読むこと")
        return 2

    rt, rt_diffs = runtime_core_diff()
    if rt_diffs:
        print(f"\n★実行時の正本がこのcoreと違う ({len(rt_diffs)}ファイル): "
              f"上の結果は『スキルが実際に読むもの』の保証になっていない")
        print(f"  検査したcore : {CORE}")
        print(f"  実行時の実体 : {rt}   ← スキル文書の `_video-core/...` はこちらを読む")
        for f in rt_diffs[:15]:
            print(f"    {f}")
        if len(rt_diffs) > 15:
            print(f"    … 他 {len(rt_diffs) - 15} 件")
        print("  → 実体側を最新にする（例: cd <実体のリポジトリ> && git pull --ff-only）か、"
              "\n     symlink を正しい core へ張り替えてから再実行すること")
        return 2
    if rt and rt != CORE.resolve():
        print(f"（実行時の正本 {rt} は内容一致）")

    if not drift:
        print("\n✅ drift なし（core と全スキルのコピーが一致）")
    return 1 if drift else 0

def push(only_skill=None):
    changed = {}
    for gname, cf, skill, tp, mode in iter_pairs():
        if only_skill and skill != only_skill:
            continue
        if not tp.exists():
            if mode != "create":
                continue
            tp.parent.mkdir(parents=True, exist_ok=True)
        elif md5(cf) == md5(tp):
            continue
        shutil.copy2(cf, tp)
        changed.setdefault(skill, []).append(str(tp.relative_to(SKILLS / skill)))
    if MISSING_SRC:
        # 配布元が欠けたまま push すると、そのグループだけ古いまま取り残される
        print(f"★配布元が無いグループ ({len(MISSING_SRC)}): 下記は配布していない")
        for gname, src, t in MISSING_SRC:
            print(f"  [{gname}] {src}/ が無い（配布先{t}スキルぶん未配布）")
        print()
    if not changed:
        print("✅ 配布対象の差分なし")
        return 0
    for skill, files in sorted(changed.items()):
        print(f"\n== {skill} ({len(files)} files updated) ==")
        for f in files:
            print(f"  {f}")
        gitdir = SKILLS / skill / ".git"
        if gitdir.exists():
            out = subprocess.run(["git", "-C", str(SKILLS / skill), "status", "--short"],
                                 capture_output=True, text=True).stdout
            print("  --- git status ---")
            for line in out.splitlines()[:20]:
                print(f"  {line}")
    print("\n※各スキルは独立 git repo。内容確認のうえ各 repo でコミットすること。")
    return 0

def pull(skill, rel):
    sp = SKILLS / skill / rel
    if not sp.exists():
        print(f"ERROR: {sp} が存在しない"); return 1
    # rel が属するグループを探す（skill が targets に含まれ、core側に同名ファイルがあるもの）
    for gname, g in manifest["groups"].items():
        if skill not in g["targets"]:
            continue
        src = CORE / g["src"]
        dest_map = g.get("dest_map", {})
        inv = {v: k for k, v in dest_map.items()}
        core_rel = inv.get(rel, rel)
        cf = src / core_rel
        if cf.exists():
            shutil.copy2(sp, cf)
            print(f"pulled: {skill}/{rel} -> core:{g['src']}/{core_rel}")
            print("次に sync_core.sh push で他スキルへ配布すること。")
            return 0
    print(f"ERROR: {rel} は manifest のどのグループにも該当しない（skill固有=同期対象外の可能性）")
    return 1

# ------------------------------------------------------------------
# snapshot: repo skills/ ↔ ローカル ~/.claude/skills の同期（DISTRIBUTION.md §5）
# 歴史的に「ローカルが正本・repoは手動cpのコピー」だった二重管理が第三のドリフト源
# になった（2026-08-09 実測: 3スキル54行差・REVISION-LEDGER.md 欠落）。
# 2026-08-10 以降 repo が upstream 正本。ローカルの改善は pull で回収してから repo 経由で配る。

# ★CORE は symlink 経由（~/.claude/skills/_video-core）で起動されると論理パスのままになり、
#   CORE.parent/"skills" が ~/.claude/skills/skills という存在しない場所を指す。
#   放置すると snapshot は0件比較で「drift なし」を返す（2026-08-10 実際に発生）。
#   実体へ解決してから repo の skills/ を求める。
REPO_SKILLS = CORE.resolve().parent / "skills"
SNAP_IGNORE = CORE / "ops" / "snapshot_ignore.txt"


def snap_ignored(skill: str, rel: str) -> bool:
    import fnmatch
    if not SNAP_IGNORE.exists():
        return False
    for raw in SNAP_IGNORE.read_text().splitlines():
        pat = raw.strip()
        if not pat or pat.startswith("#"):
            continue
        if fnmatch.fnmatch(f"{skill}/{rel}", pat):
            return True
    return False


SNAP_IGNORE_DIRS = IGNORE_DIRS | {".claude"}  # スキル内の .claude/worktrees 等は同期対象外
                                              # ※判定は skill 内相対パスに対して行う（絶対パスだと
                                              #   ~/.claude/skills 自身が弾かれて全ファイル無視になる）


def snap_files(root: Path):
    if not root.is_dir():
        return {}
    out = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if p.name == ".DS_Store" or p.suffix in (".pyc", ".pyo"):
            continue
        if any(part in SNAP_IGNORE_DIRS for part in rel.parts):
            continue
        out[str(rel)] = p
    return out


def snap_pairs(only_skill=None):
    # ★repo の skills/ が見つからないまま進むと「0件比較して drift なし」になる。
    #   同じ型の事故を2度踏んでいる（配布元欠落・実行時core不一致）ので、ここでも黙って通さない。
    if not REPO_SKILLS.is_dir():
        print(f"★repo の skills/ が見つからない: {REPO_SKILLS}\n"
              f"  （CORE={CORE}）このままでは1件も比較できず『drift なし』は無意味。\n"
              "  → repo の作業ツリー内の core から実行すること", file=sys.stderr)
        sys.exit(2)
    skills = sorted(d.name for d in REPO_SKILLS.iterdir() if d.is_dir())
    if only_skill:
        if only_skill not in skills:
            print(f"ERROR: repo skills/ に {only_skill} が無い（対象: {', '.join(skills)}）"); sys.exit(2)
        skills = [only_skill]
    for skill in skills:
        repo_map = snap_files(REPO_SKILLS / skill)
        local_map = snap_files(SKILLS / skill)
        yield skill, repo_map, local_map


def snapshot_check(only_skill=None):
    same = 0
    drift, repo_only, local_only, ignored = [], [], [], 0
    for skill, repo_map, local_map in snap_pairs(only_skill):
        for rel in sorted(set(repo_map) | set(local_map)):
            if snap_ignored(skill, rel):
                ignored += 1
                continue
            if rel not in local_map:
                repo_only.append(f"{skill}/{rel}")
            elif rel not in repo_map:
                local_only.append(f"{skill}/{rel}")
            elif md5(repo_map[rel]) != md5(local_map[rel]):
                drift.append(f"{skill}/{rel}")
            else:
                same += 1
    print(f"SAME: {same}" + (f"  (ignore: {ignored})" if ignored else ""))
    for label, items, hint in (
            ("DRIFT(内容差)", drift, "pull(ローカル→repo) か apply(repo→ローカル) で解消"),
            ("REPO-ONLY(ローカルに無い)", repo_only, "apply で配布"),
            ("LOCAL-ONLY(repoに無い)", local_only, "改善なら pull で回収／意図的ローカル専用なら snapshot_ignore.txt へ")):
        if items:
            print(f"\n{label} ({len(items)}): {hint}")
            for it in items[:40]:
                print(f"  {it}")
            if len(items) > 40:
                print(f"  … 他 {len(items) - 40} 件")
    if same == 0 and not (drift or repo_only or local_only):
        # 比較0件は「一致」ではなく「検査していない」。無言のPASSを出さない
        print(f"★1件も比較していない（REPO_SKILLS={REPO_SKILLS}）。この『drift なし』は無効",
              file=sys.stderr)
        return 2
    bad = len(drift) + len(repo_only) + len(local_only)
    if bad:
        print(f"\n★snapshot drift {bad} 件。REVISION-LEDGER.md 欠落事故(2026-08-09)はこの検査の不在が原因。")
        return 1
    print("\n✅ snapshot drift なし（repo skills/ とローカルが一致）")
    return 0


def snapshot_copy(direction: str, only_skill=None, only_rel=None):
    """direction: 'pull'=local→repo / 'apply'=repo→local。削除はしない。
    only_rel を渡すとそのファイル1つだけコピー（DRIFTを方向別に選り分けたい時。
    例: repo側の改訂を守りつつローカル専用の新規ファイルだけ回収する）。"""
    copied = []
    for skill, repo_map, local_map in snap_pairs(only_skill):
        src_map, dst_map, dst_root = (
            (local_map, repo_map, REPO_SKILLS / skill) if direction == "pull"
            else (repo_map, local_map, SKILLS / skill))
        for rel, sp in sorted(src_map.items()):
            if only_rel and rel != only_rel:
                continue
            if snap_ignored(skill, rel):
                continue
            dp = dst_root / rel
            if rel in dst_map and md5(sp) == md5(dst_map[rel]):
                continue
            dp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sp, dp)
            copied.append(f"{skill}/{rel}" + ("" if rel in dst_map else "  (新規)"))
    if not copied:
        print("✅ コピー対象の差分なし")
        return 0
    arrow = "ローカル→repo" if direction == "pull" else "repo→ローカル"
    print(f"{arrow} {len(copied)} 件コピー:")
    for c in copied:
        print(f"  {c}")
    if direction == "pull":
        print("\n※repo 側の差分を確認してコミットすること（git diff で回収内容を必ず読む）。")
    else:
        print("\n※ローカルスキルが独立 git repo の場合は各 repo でコミットすること。")
    return 0


args = sys.argv[1:]
USAGE = ("usage: sync_core.sh check | push [skill] | pull <skill> <relative-path>\n"
         "       sync_core.sh snapshot check|pull|apply [skill] [relative-path]")
if not args or args[0] not in ("check", "push", "pull", "snapshot"):
    print(USAGE); sys.exit(2)
if args[0] == "snapshot":
    if len(args) < 2 or args[1] not in ("check", "pull", "apply"):
        print(USAGE); sys.exit(2)
    only = args[2] if len(args) > 2 else None
    only_rel = args[3] if len(args) > 3 else None
    if args[1] == "check":
        sys.exit(snapshot_check(only))
    sys.exit(snapshot_copy(args[1], only, only_rel))
if args[0] == "check":
    sys.exit(check())
elif args[0] == "push":
    sys.exit(push(args[1] if len(args) > 1 else None))
else:
    if len(args) < 3:
        print("usage: sync_core.sh pull <skill> <relative-path>"); sys.exit(2)
    sys.exit(pull(args[1], args[2]))
PYEOF
