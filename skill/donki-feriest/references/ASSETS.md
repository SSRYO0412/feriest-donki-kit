# 素材と素材DBの引き方

---

## 1. 素材DBの場所

**キット同梱**: `data/asset_db/feriest_0801-0805_windows.sqlite`（テーブル `asset_windows_v2` / 3,774窓）

元になった全案件DB（キットには入っていない）: `@@FERIEST_ROOT@@/01_assets/db_202608/feriest_202608_v5_fix.sqlite`

★**v5_fix が正本**。v1〜v4 は工程途中の版（残してあるが使わない）。

| テーブル | 中身 |
|---|---|
| `asset_windows_v2` | **1素材×時間窓 = 1行**。全 **4,658 窓** / 234クリップ / **71列** |
| `persons` | 人物レジストリ |

## 2. 窓のスキーマ（71列・よく使うもの）

| 列 | 中身 |
|---|---|
| `win` | `<商材>_<クリップ>#w0001` 形式の主キー |
| `key` | クリップ名（`海老ドーン贅沢ぷりぷり海老マヨピザ_20260803_honma_a0920`） |
| `win_id` / `t0` / `t1` / `dur` | 窓の番号と素材内の秒 |
| `shot_size` | `extreme_close` / `close` / `medium` / `wide` |
| `composition` | `hero` / `good` / `cramped` / `cut_off` / `no_subject` |
| `action` | ★**何をしているか**（選定の主キーはここ） |
| `semantic_tags` / `inventory` | 写っているもの。★`inventory` は照合に使わない（偽陽性を量産する） |
| `person_count` | ★**実画と食い違うことがある**。必ず目視で裏を取る |
| `bright_med` / `white_max` / `dark_max` | 輝度・白飛び・黒つぶれ |
| `sharp_med` / `sharp_min` | 精細度（高いほど良い） |
| `shift_med/p95/max` | 平行移動量（カメラの動き） |
| `dcam_med/p95/max` | カメラ動作量 |
| `mov_area_med/max` / `flow_std_med` | 動きの面積・オプティカルフロー |
| `verdict` / `verdict_reason` / `flags` | 判定 |
| `crop_potential` / `subject_cut_off` / `blur_or_shake` / `freeze` | 品質フラグ |

## 3. 引き方の例

```bash
DB="data/asset_db/feriest_0801-0805_windows.sqlite"   # キット同梱（テーブルは asset_windows_v2）

# 商材の全窓を一覧化（★選定前に必ず全部読む）
sqlite3 -separator '|' "$DB" "
SELECT replace(win,'海老ドーン贅沢ぷりぷり海老マヨピザ_','')||'',
       printf('%5.2f-%5.2f',t0,t1), printf('%4.2f',dur), shot_size, composition,
       printf('%3.0f',bright_med), printf('%5.3f',white_max), printf('%4.0f',sharp_med),
       person_count, substr(action,1,70)
FROM asset_windows_v2 WHERE key LIKE '海老ドーン%' AND dur>=0.5
ORDER BY key, win_id;"

# 白飛びが少なく精細な候補
sqlite3 -header -column "$DB" "
SELECT win, dur, bright_med, white_max, sharp_med, shot_size, substr(action,1,40)
FROM asset_windows_v2
WHERE key LIKE '海老ドーン%' AND white_max<0.05 AND dur>=1.85
ORDER BY sharp_med DESC LIMIT 15;"

# カメラの動きが大きい窓
sqlite3 -header -column "$DB" "
SELECT win, dur, shift_p95, dcam_p95, shot_size, substr(action,1,40)
FROM asset_windows_v2 WHERE key LIKE '海老ドーン%' AND dur>=1.85
ORDER BY shift_p95 DESC LIMIT 10;"
```

★**DBの数値は目安。最終判断は実素材を測る。**
カメラの動きは本番と同じクロップでフレーム間差を実測した方が正確:

```bash
ffmpeg -hide_banner -v error -ss <tin> -t <dur> -i <src> \
  -vf "scale=-2:1920,crop=1080:1920,scale=160:284,format=gray" -f rawvideo - \
  | python3 -c "import sys,numpy as np; W,H=160,284; d=sys.stdin.buffer.read(); \
    n=len(d)//(W*H); f=np.frombuffer(d[:n*W*H],dtype=np.uint8).reshape(n,H,W).astype(float); \
    dd=np.abs(np.diff(f,axis=0)).mean(axis=(1,2)); print(f'平均{dd.mean():.2f} 最大{dd.max():.2f}')"
```

**実測の目安（海老ドーンの素材）**: 静止 0.56 ／ なめるような移動 8.18 ／ 最大 12.73

## 4. 素材の内訳

| 商材 | 本数 | 尺 | 窓 |
|---|---|---|---|
| Mii + フレグランスオイル | 47 | 24.4分 | 1,307 |
| Reebok ファン付きベスト | 46 | 18.2分 | 803 |
| ド情熱 消臭＆防水スプレー | 36 | 10.3分 | 430 |
| おうちでライブマイク | 35 | 19.1分 | 793 |
| **海老ドーン** | **24** | **9.9分** | **429** |
| トロリスタ | 22 | 7.9分 | 372 |
| アプリクーポン（★放置） | 15 | 7.5分 | 427 |
| ホイールグローブ | 8 | 1.9分 | 85 |
| **計** | **234** | **99.4分** | **4,658** |

**海老ドーンの範囲**: `20260803_honma_a0920`〜`a0933` ＋ `IMG_2848`〜`IMG_2858`

## 5. 素材の原本

`$FERIEST_ROOT/00_source_drive/20260807_新素材_8月掲載分/<商材フォルダ>/`

★手元の原本が引けるかは `python3 scripts/check_links.py` で検査する。

★**読み取り専用。絶対に編集しない。**
★プロキシ（`01_assets/db_202608/proxy/`）で**書き出さない**。実測も原本で行う。

## 6. その他の成果物（全てSSD内）

| | 場所 |
|---|---|
| 構成設計（5商材30スロットの割付） | `01_assets/db_202608/s34_FINAL3.json`（★現在の採用） |
| スロット採点の履歴 | `01_assets/db_202608/s1_slot_score_v1〜v6.json` / `s34_select_v1〜v10.json` |
| 参考の様式プロファイル | `01_assets/db_202608/ref_style_profile_v1.json` / `ref_machine_v1/` |
| 参考分析の所見 | `02_work/ref_analysis/KIMO.md` |
| コンタクトシート | `01_assets/db_202608/sheets/` |
| 抽出フレーム | `01_assets/db_202608/frames/` |
| 動き解析 | `01_assets/db_202608/motion_v3_202608/` |
| 字コンテとの突合 | `01_assets/db_202608/conte_match_v3/` |
| 素材不足の対処案 | `01_assets/db_202608/no_material_plan_v1.md` |
| 7月納品分（参考様式DB） | `01_assets/db_202608/feriest_ref50_v1.sqlite` |
| DB化計画（罠の記録つき） | `05_docs/20260807_新素材_DB化計画.md` |
| カーテン工程の学び | `02_work/LEARNINGS_feriest_20260803.md` |
| テロップ工程の学び | `02_work/LEARNINGS_feriest_telop_20260803.md` |

## 7. ★SSDに無いもの（マシン側に必要）

| | 手当て |
|---|---|
| MOGRT `telop_3slot_v22.mogrt` | ★このスキルの `assets/` に**同梱済み**。本来は video-ops-framework 側 |
| Twemoji `1f447.png` / `1f364.png` | ★このスキルの `assets/` に**同梱済み** |
| **CEP Bridge 拡張** | `~/Library/Application Support/Adobe/CEP/extensions/MCPBridgeCEP` を導入する |
| **フォント** | Adobe Fonts で `mplus-1p-heavy` / `HeiseiMinStd-W9` / `Makinas-4-Square` を有効化 |
| **video-ops-framework** | `git clone` → `core/ops/scripts/install.sh` |
| **Codex CLI** | `npm i -g @openai/codex@latest` → `codex login`（敵対レビューに使う） |

**これ以外は全てSSD内にある。**
