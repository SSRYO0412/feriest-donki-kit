# _video-core — 動画クローン系スキル群の共通ファイル正本（2026-07-02 作成）

**これはスキルではない**（SKILL.md を置かない）。クローン系スキル・ファミリーがフォークコピーで共有している
agents / references / scripts の**正本置き場**と、drift 検出・配布のための同期機構。

> ★**2026-08-08 に実体を repo 側へ移した**。正本は `video-ops-framework/core/` で、
> `~/.claude/skills/_video-core` はそこへの **symlink**。どちらを編集しても同じ実体を触る。
>
> 移設前は「ローカルに実体（remote 無しの git repo）、repo にコピー」の二重管理で、
> 2つのリポジトリの間に git の線が無かった。そのため
> ①どちらが新しいか git が教えてくれない ②両側で同時に編集でき後から cp した側が黙って勝つ
> ③ローカル側の30コミットの履歴がどこにも push されない、という問題があった。
> 実際 2026-08-08 に逆ドリフトが4件見つかっている（PRINCIPLES §14＝46行／
> TELOP-CRAFT 縦組み節＝63行／同 prproj節＝24行／notion-db-contract §10-2 の方針逆転）。
>
> **編集したら repo でコミットして push する**。これで履歴も保全される。
> 移設前のローカル履歴（30コミット）は
> `~/Backups/video-core/_video-core_pre-move_20260808.tar.gz` に退避してある。

## なぜ在るか
reference-video-clone → faceless-video-clone → swap系 → lp とフォークで派生した結果、
同一ファイルのコピーが6+スキルに散らばり、**片方で入った改善が他方に届かないドリフト**が実際に起きていた
（例: tone-library のトーン12種追加が faceless 系に未反映 / verification の逐語照合節が未反映 /
deai_filmify の新 video パスが本家に未反映 / kling_person_swap の frontal_image_url 修正が swap-clone に未反映）。

## 使い方
```bash
~/.claude/skills/_video-core/sync_core.sh check          # drift レポート（変更しない）
~/.claude/skills/_video-core/sync_core.sh push           # core → 全スキルへ配布
~/.claude/skills/_video-core/sync_core.sh push <skill>   # 1スキルだけ配布
~/.claude/skills/_video-core/sync_core.sh pull <skill> <relpath>  # スキル側の改善を core へ回収
```
**運用ルール（重要）**: 共有ファイル（下記グループに含まれるもの）を改善したら、
①そのスキルで動作確認 → ② `pull` で core へ回収 → ③ `push` で家系全体へ配布 → ④各スキル repo でコミット。
スキル側だけ直して放置するとドリフトが再発する。定期的に `check` を回す。

## ★実行時の正本＝symlink の実体（2026-08-10 の事故と恒久対処）

スキル文書が正本として参照する `_video-core/...` の実体は **symlink 先の作業ツリー**
（通常はメインチェックアウト `~/video-ops-framework/core`）である。したがって:

**master にマージしただけでは実行時の正本は変わらない。メインチェックアウトを pull するまで、
全スキルは古い正本を読み続ける。**

```bash
cd ~/video-ops-framework && git pull --ff-only   # ★マージ後に必ずやる
```

**事故（2026-08-10）**: PR をマージし、worktree から `sync_core.sh check` を回して
「drift なし」を確認した。しかし check が見ていたのは worktree の core であり、
symlink の実体であるメインチェックアウトは **9コミット古いまま**（`core/audio` が存在せず
`PRINCIPLES §15` も無い）だった。**スキルが実際に読むものは一度も検査されていなかった。**
これは「配布元が無いグループが黙って検査対象から消える」（同ファイル冒頭の事故）と同じ型の、
*検査範囲の外側に本体がある*バグ。

**恒久対処（2段）**:

1. **検出**: `check` が実行時の正本（`<skills>/_video-core` の実体）と自分が検査している core を
   突き合わせ、内容が違えば**終了コード2で止める**（`runtime_core_diff()`）。
   worktree やブランチ違いから回しても、実行時に効いていない core についての「drift なし」を
   報告できなくなった。
2. **自己修復**: `ops/scripts/doctor.py` が実行時正本の状態（symlink 解決可否・ブランチ・
   origin との差・更新可否）を診断し、`--fix` で安全なときだけ `git pull --ff-only` する。
   **セッション開始時に自動実行**する（`~/.claude/settings.json` の SessionStart hook）:

   ```json
   "command": "test -f ~/.claude/skills/_video-core/ops/scripts/doctor.py && python3 ~/.claude/skills/_video-core/ops/scripts/doctor.py --fix --quiet 2>&1 || true"
   ```

   健全なら無音・遅れていれば黙って追いつく・危険なら理由を出して止まる。
   「マージ後に pull を忘れない」という意思のルールを機構に置き換えた。

   - 更新可否は**git 自身に判定させる**（`--ff-only` は合流も巻き戻しもしない）。
     こちらで「作業ツリーが汚れているから」と先回りして止めると、追跡外ファイルが1個
     あるだけで永久に自己修復しなくなる（実際に踏んだ: `?? .claude/`）
   - master/main 以外のブランチに居るときは自動更新せず警告する（全スキルがそのブランチの
     内容を読む＝非決定的な状態なので、人が気づくべき）
   - ★**ブートストラップだけは手動**: doctor.py 自身が実行時正本に届くまでは hook が空振りする
     （script 不在時は無音で no-op）。初回だけ `cd <repo> && git pull --ff-only` が要る

## グループ構成（core-manifest.json が正）
| グループ | 配布先 | 内容 |
|---|---|---|
| `common/` | クローン系6スキル | agents 7体 / SCHEMA・tone-library・verification・telop-analysis-methodology・orchestration・asset-generation・editorial-template・file-structure・pipeline-notes・remotion-template / 共通 scripts 約22本（deai_filmify は89行版=720p再圧縮。旧挙動が要る時は `DEAI_SCALE=1080` 等の env で調整） |
| `faceless/` | faceless系4スキル | clone-spec 系 scripts（build_clone_spec/detect_cadence/compare_grid 等）・faceless版 mass-generation・ui-reproduction・chat-template |
| `footage/` | reference-video-clone / interview | footage版 mass-generation |
| `swap3/` | swap系3スキル | kling_person_swap.py（frontal_image_url 修正版） |
| `faithful_lp/` | faithful / lp | person-swap・BEFOREAFTER_RULES（汎用品質版）・jp-locations・parallel-mass-production・clone-from-reference・conditional-techniques・mass_*_parallel.sh |
| `PRINCIPLES.md` | 全7スキル（capcut含む）の references/ | 横断原則（実測主義・検証の鉄則・閉ループ選別・並列安全策・承認ゲート） |
| `revision/` | video-revision-db-workflow / 案件V-video-revision-workflow / project-v-ad-production | **バージョン管理・履歴保全の正本**（2026-07-11 追加）: VERSIONING.md（命名/ディレクトリ/履歴書式/更新トリガー/納品規約）・revision-checklist.md・check_adoption_sync.py（採用v突合検算）・check_variant_dupes.py（素材重複機械チェック）・new_revision_project.py（修正案件スカフォールド） |
| `selection/` | footage-asset-db / project-v-ad-production | **台本→素材選定・検証の正本**（2026-07-11 追加）: SELECTION_PROTOCOL.md（意味カテゴリ分類→基準表→台帳→二重検証・主張タイプ分類表・フック伝達力検証）・verified_clips.template.json（検証済みクリップ台帳スキーマ）・asset-db-queries.template.md（案件別クエリ集の雛形） |
| `compilation/` | project-v-ad-production | **ffmpegコンピレーション広告編集の正本**（2026-07-11 追加）: telop-ffmpeg-compilation.md（boxblur汚染/グロー濃度/concat無音化の3大バグと正解）・build_compilation.py（汎用ビルドハーネス。数値は案件ごと実測して設定） |
| `telop/` | short-telop-craft / reference-video-clone / short-video-pipeline | **テロップ完全再現・アニメ実装の正本**（2026-08-03 追加・Dec28_01から抽象化）: TELOP-CRAFT.md（区間定義→定常フレーム実測→テンプレートマッチング動き実測→PNGレンダー(base/emph分離)→Premiere配置+アニメ(敷き直し集約)→書き出し画素検証。測定器の罠3種・エフェクト実測値表・出現アニメ基本型） |
| `vo/` | project-v-ad-production / audio-emotion-voice-clone | **VO再構築・話速/音量修正の正本**（2026-07-11 追加）: onvoice-recipe.md（VO同期再構築の手順枠）・telop-pace-volume-method.md（全行一律retime・反復確定・RMS均一化・font_size_overrides） |

## 同期対象外（意図的にスキルごとに違うもの — 触るときは各スキルで個別に）
- `scripts/build.py`（RVC=verdict部分一致修正 / faceless系=faceless版 / interview=文節分割・二重字幕対策入り270行 — パイプラインが違うため別実装）
- `scripts/check_overlap.py`（NO_CAP 集合が各スキルの build.py の抑制集合∪Remotionテンプレの抑制集合と結合しているため同期しない。footage系=`{verdict,hook,cta,profile}`（interview版）/ faceless系=`{verdict,hook,cta}`）
- `scripts/fullframe_compare.py` / `scripts/check_linebreaks.py`（faceless-video-clone 固有）
- `scripts/multidim_workflow.js` の faceless 版（common に置いた RVC 版=防御パース入りを配布するが、faceless 版で独自拡張した場合は pull 前に diff を確認）
- swap-clone の before/after 専用モジュール（BEFOREAFTER_RULES 日本人フィットネス版・jp-ugc-before-after.md・body-matching.md・gen_*_jp_ugc.sh・body_compare.py・mass_*.sh の clone 版）
- reference-video-clone-capcut の verification.md / telop-analysis-methodology.md / build.py（CapCut パイプライン固有）＋ capcut_* / verify_capcut_* / build_capcut
- lp 固有: i2v_end.py・analysis-extension・decision-tree・negative-prompt-library・state-transition-generation・final-quality-match・verification-and-composite
- faceless-video-clone 固有: plots_batch_*.json（データ）

## tone-library の正本
「育てる資産」の正本は **core の `common/references/tone-library.md`**。
実運用コピーは各スキルの references/ と `~/Documents/video-projects/tone-library.md`（レンダー実行時に参照される方）。
新トーンを追記したら必ず `pull` → `push` で全コピーへ反映し、video-projects 側へも cp すること。
