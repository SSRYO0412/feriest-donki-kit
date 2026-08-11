# この案件の編集・修正に最小限必要なもの

---

## 0. 結論

| | 状態 |
|---|---|
| **原本フッテージ**（5商材 188本・34.5GB） | ⚠️ **リポジトリに入らない**。手元の原本を `FERIEST_ROOT` で指す（`scripts/check_links.py` で検査）|
| **案件 jsx 98本** | ✅ `work/jsx_20260809/` に**同梱済み**（絶対パスはトークン化・v20参照5本は `_rejected/`）|
| **作業 prproj**（0801 採用版＋却下版） | ✅ `work/premiere/` に**同梱済み**（`<RelativePath>` 保持で自動再リンク）|
| **SSD の中身**（窓DB・構成設計・参考分析） | ✅ リポジトリに同梱済み |
| **MOGRT `telop_3slot_v22.mogrt`** | ✅ このスキルの `assets/` に**同梱済み** |
| **Twemoji `1f447.png` / `1f364.png`** | ✅ 同梱済み |
| **CEP Bridge 拡張**（100KB・5ファイル） | ✅ `assets/MCPBridgeCEP/` に**同梱済み** |
| **`pr.sh`**（jsx投入スクリプト） | ✅ `skill/donki-feriest/scripts/pr.sh` に**同梱済み**（★正本）|
| **判断の正本 15ファイル**（下記） | ✅ **このキットに同梱済み**（`core/` と `skills/` に全15本。実在を検算済み 2026-08-11）|
| **フォント3種** | ❌ Adobe Fonts で有効化（マシン側） |

★**CEP Bridge は video-ops-framework に入っていません。**
このマシンの `~/Library/Application Support/Adobe/CEP/extensions/MCPBridgeCEP` にしか無かったので、
**SSD側に同梱しました**。

---

## 1. CEP Bridge の導入（SSD同梱物から）

```bash
# 1. 拡張を配置
ditto "skill/donki-feriest/assets/MCPBridgeCEP" \
      "$HOME/Library/Application Support/Adobe/CEP/extensions/MCPBridgeCEP"

# 2. ★未署名拡張を許可（これが無いとパネルが出ない）
defaults write com.adobe.CSXS.11 PlayerDebugMode 1
defaults write com.adobe.CSXS.12 PlayerDebugMode 1

# 3. Premiere を再起動
```

**中身**（5ファイル・100KB）

| | |
|---|---|
| `CSXS/manifest.xml` | 拡張の宣言。`com.mcp.premiere.cepbridge.panel` / 対応 PPRO `[14.0, 99.9]` |
| `.debug` | 未署名で動かすための宣言（Port 8801） |
| `bridge-cep.js` | ブリッジ本体。`/tmp/premiere-mcp-bridge` を250ms間隔で監視 |
| `CSInterface.js` | Adobe の CEP ライブラリ |
| `index.html` | パネルのUI（Start Bridge ボタン） |

**使い方**: `ウィンドウ > 拡張機能 > MCP Bridge (CEP)` → **Start Bridge**（毎セッション手動）

★**ブリッジの制約**（実装を読んで確認済み）
- コマンドは `readdirSync()` の**最初の1件だけ**処理する＝**同時実行は不可**
- その順序は**時系列ではない**
- `require(` `process.` `eval(` `new Function(` などを含むと**コメント内でもスクリプトが拒否される**
- タイムアウト既定45秒（`timeoutMs` はそれより大きいときだけ採用される）

---

## 2. 判断の正本 15ファイル（すべて同梱済み）

★以前は「framework から取り出す」手順だったが、**このキットは15本とも既に含んでいる**。
下の表は「どれが効くか」を示す索引として残す。取り出し作業は不要。

### A. Premiere を触るなら必須（4ファイル）

| ファイル | なぜ要るか |
|---|---|
| `skills/premiere-bridge-ops/SKILL.md` | 接続・並列・編集の全知見（52KB） |
| `skills/premiere-bridge-ops/references/API-TRAPS.md` | ★**実機で踏んだAPI罠の一覧**。これが無いと同じ罠を踏む |
| `skills/premiere-bridge-ops/references/VERIFY-METHOD.md` | ★**検証の型**（読み戻しだけで「できた」と言わない・測定器の盲点） |
| `skills/premiere-bridge-ops/references/TELOP-WORKFLOW.md` | テロップの通し手順 |

### B. テロップを作るなら必須（2ファイル）

| ファイル | なぜ要るか |
|---|---|
| `core/telop/references/TELOP-CRAFT.md` | ★テロップ完全再現の6工程（40KB） |
| `skills/premiere-bridge-ops/references/DESIGN-BOUNDARY.md` | Premiere側とAE側の境界・原理的に無理なもの |

### C. カットを選ぶなら必須（1ファイル）

| ファイル | なぜ要るか |
|---|---|
| `skills/reference-video-clone/references/CUT-QC-RULES.md` | ★**着手前に全文読む**のが恒久ルール。3〜5候補スコアリング＋Codex敵対レビュー（26KB） |

### D. Notion 台帳を触るなら必須（2ファイル）

| ファイル | なぜ要るか |
|---|---|
| `core/revision/references/REVISION-LEDGER.md` | ★**修正台帳の正本**（何を書く台帳か・作り方） |
| `core/revision/references/notion-db-contract.md` | DB運用契約（キー文法・不変条件・正規語彙） |

### E. 横断原則・入口（3ファイル）

| ファイル | なぜ要るか |
|---|---|
| `core/PRINCIPLES.md` | ★横断原則（実測主義・§12 書き出した実ファイルで確かめる・§15 案件文書を先に読む） |
| `skills/video-ops/SKILL.md` | 入口ルーター（5問で型を確定） |
| `core/pipeline/references/PROJECT-ROUTER.md` | ルーティングの判定表 |

### F. 検品（1ファイル）

| ファイル | なぜ要るか |
|---|---|
| `skills/short-video-qc/SKILL.md` | 納品前検品の全工程（三大禁止：観察の捏造・自己採点・工程スキップ） |

### G. 運用ツール（2ファイル・任意）

| ファイル | なぜ要るか |
|---|---|
| `core/sync_core.sh` | 正本の同期・drift検査 |
| `core/ops/scripts/install.sh` | 導入（vops・skillリンク・SessionStart hook） |

---

## 3. 取り出しコマンド（★不要。framework しか無い環境へ渡すとき用に残す）

```bash
SRC=~/video-ops-framework
DST="/Volumes/Extreme SSD/FERIEST/_skill/_framework_minimal"

for f in \
  skills/premiere-bridge-ops/SKILL.md \
  skills/premiere-bridge-ops/references/API-TRAPS.md \
  skills/premiere-bridge-ops/references/VERIFY-METHOD.md \
  skills/premiere-bridge-ops/references/TELOP-WORKFLOW.md \
  skills/premiere-bridge-ops/references/DESIGN-BOUNDARY.md \
  skill/donki-feriest/scripts/pr.sh \

  core/telop/references/TELOP-CRAFT.md \
  skills/reference-video-clone/references/CUT-QC-RULES.md \
  core/revision/references/REVISION-LEDGER.md \
  core/revision/references/notion-db-contract.md \
  core/PRINCIPLES.md \
  skills/video-ops/SKILL.md \
  core/pipeline/references/PROJECT-ROUTER.md \
  skills/short-video-qc/SKILL.md \
  core/sync_core.sh \
  core/ops/scripts/install.sh ; do
  mkdir -p "$DST/$(dirname "$f")"
  cp -p "$SRC/$f" "$DST/$f"
done
```

---

## 4. ★ただし、clone した方が早い

repo 全体でも **33MB / 437ファイル**です。

```bash
git clone <repo> ~/video-ops-framework
cd ~/video-ops-framework && bash core/ops/scripts/install.sh
```

`install.sh` が **vops のリンク・`_video-core` の正本リンク・スキルの登録・SessionStart hook のマージ**
まで全部やります（冪等・既存設定はバックアップされる）。

**最小セットの切り出しが要るのは、repo にアクセスできない環境へ渡すときだけ**です。
その場合、**上の15ファイル＋SSD** で編集・修正は回ります。
ただし `vops` コマンドと正本の自動追従は使えなくなるので、**学びの回収（harvest）と
納品ゲート（notion_gate.py）は手動になります**。

---

## 5. 依存関係のまとめ

```
    このキット ─────┬─ 窓DB・構成設計・参考分析・conte
                    ├─ 案件 jsx 98本（work/jsx_20260809/・トークン化済み）
                    ├─ 作業 prproj（work/premiere/・RelativePath 保持）
                    ├─ MOGRT v22 / Twemoji / CEP拡張 / pr.sh
                    ├─ 判断の正本 15ファイル（core/ と skills/）
                    └─ この案件専用スキル（donki-feriest）

    手元の原本 ─────── フッテージ 188本・34.5GB（FERIEST_ROOT で指す）

    マシン ─────────┬─ Premiere Pro 2026 + Adobe Media Encoder
                    ├─ Adobe Fonts: mplus-1p-heavy / HeiseiMinStd-W9 / Makinas-4-Square
                    ├─ PlayerDebugMode = 1（未署名CEP拡張の許可）
                    └─ Codex CLI（敵対レビュー用・任意）

    クラウド ───────── Notion（修正台帳・修正記録DB・11DB）
```
