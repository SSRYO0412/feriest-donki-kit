# <案件名> 素材DB クエリ集（テンプレ）

> 雛形: `_video-core/selection/references/asset-db-queries.template.md`。
> `footage-asset-db` でDBを構築したら、**案件ごとにこのファイルをコピーして埋める**（DB構築の標準成果物の一つ）。
> 選定フローは `SELECTION_PROTOCOL.md`（台帳→DB検索の順・二重検証）に従う。

DB: `<SQLiteファイルのフルパス>`。Notion「<案件名> 素材DB」(data_source_id: `<collection id>`)と同一データ。
実ファイルのルート: `<素材ルートのフルパス>`（relを連結して実パスになる）。

## スキーマ
```sql
CREATE TABLE assets(
 id INTEGER PRIMARY KEY, rel TEXT UNIQUE, product TEXT, subfolder TEXT, fname TEXT,
 category TEXT, device TEXT, cam_model TEXT, duration REAL, width INT, height INT,
 orientation TEXT, fps TEXT, vcodec TEXT, has_audio INT, acodec TEXT,
 size_mb REAL, ctime TEXT, n_frames INT,
 shot_type TEXT, subject TEXT, person TEXT, background TEXT, motion TEXT,
 usable_for TEXT, quality TEXT, description TEXT, vision_done INT DEFAULT 0);
```
- `rel`: 素材ルートからの相対パス。
- `orientation`: `縦`|`横`。**★iPhone .MOV等のローテーションメタデータを反映しないことがある**。列値だけで「横だから劣化する」と判断せず、必ずフレームを1枚抽出して表示向き・画質を実確認。
- `person`: `なし`|`全身1名`|`全身2名以上`|`手のみ`|`足のみ`（顔リスクの一次フィルタ。ただし実フレーム確認は省略しない）。
- `quality`: 自由記述。まれに「X-Y秒目シーンは使用不可」等の**使用制限注記**が入るので必ずSELECTして読む。
- `description`: vision解析の自由記述。**動画全体（の一部シーン）の代表描写**であり、指定in点の実際の絵とは限らない。

## 基本クエリ(コピペ用)
```bash
DB=<DBフルパス>
sqlite3 "$DB" -header -column "
SELECT id,rel,duration,shot_type,subject,quality,person,description
FROM assets
WHERE (description LIKE '%<キーワード>%' OR shot_type LIKE '%<種別>%')
LIMIT 15;
"
```
- ★候補が枯渇したカテゴリは、まず絞り込み（orientation・category等）を外して**全量再検索**するのが最優先の一手。

## 用途別キーワード早見表（案件ごとに埋める・実測で育てる）
| 訴求内容/カテゴリ | descriptionキーワード例 | 備考(合格条件は基準表へ) |
|---|---|---|
| <例: 質感マクロ> | `<語1>` `<語2>` | |
| <例: 機能実演> | | |
| <例: ブランド開示> | | |
| <例: 着用/引き> | | |

## 使用済みIDの除外(1カット=1素材ルール)
```sql
... AND id NOT IN (<確定済みID列挙>);
```
- バリアント制作時はバリアント間・バッチ横断の重複も対象（`check_variant_dupes.py`で機械チェック）。

## 既知の罠（案件ごとに追記して育てる）
- **フォルダ名の顔NG注記は目安に過ぎない**。注記付きフォルダでも安全なカットが大半を占め、逆に注記なしフォルダに顔が完全に映る素材が混在する。選定candidateごとに`ffmpeg -ss <in> -frames:v 1`でフレーム抽出→個別目視。
- **descriptionの動作語（なぞる/押す等）は実際には静止接触のことがある**。動作カテゴリは動画切り出し/フレーム差分で判定（SELECTION_PROTOCOL §3）。
- <案件固有の罠をここに追記: 使用禁止素材・同名別内容ファイル・焼き込みロゴ・窓依存クリップ等>

## Notion側で直接確認したいとき
```
mcp__notion__API-retrieve-a-database database_id=<id>
mcp__notion__API-query-data-source data_source_id=<id>  # filter構文が不安定な場合はAPI-post-searchでgrepの方が確実
```
