# 素材の引き方

> ★このキットには**窓単位の素材解析データ（DB）は同梱していません**。
> 配布物に入っているのは ①在庫表（検収用の最小情報）と ②スロット別の候補リスト（選抜済み）です。
> 追加の判断が要るときは**実素材を ffprobe/ffmpeg で都度測り、実画を目視**します——
> これはこの案件の原則（実測主義・ラベルを信用しない）と同じ考え方です。

---

## 1. 同梱物

| ファイル | 中身 | 用途 |
|---|---|---|
| `data/asset_db/media_manifest.json` | **在庫表**。5商材 188クリップの名前と実尺（秒）＋窓数の集計 | `check_links.py --verify-media` の検収・件数検算 |
| `data/design/s34_FINAL3.json` | ★**スロット別の候補リスト（選抜済み）**。5商材 × 6スロット・候補 **562件**。各候補に `t0/t1/dur/shot/comp/quality/blur/persons/matched` | 0802〜0805 の選定の出発点 |
| `data/conte/conte.json` | 字コンテ45スロット（`need` = must+want の被写体要求つき） | 何を探すかの正 |
| `data/revision_aids/alternatives.json` | ★**軸別の代替候補**（白飛び/動き/カメラワーク種類/寄り引き/人物なし/被写体中心・スロット別top5＋商材別極値） | 修正指示への即応（`REVISION-PLAYBOOK.md`） |
| `data/revision_aids/clip_profiles.json` | 188本×1秒粒度の数値プロファイル（カメラ分類つき） | 候補表の外を探す粗い地図 |

### 在庫の内訳（media_manifest.json の実測値）

| product | クリップ | 窓（集計） |
|---|---|---|
| Mii +フレグランスオイル、ロックミルク | 47 | 1,307 |
| Reebokファン付きベスト | 46 | 803 |
| おうちでライブマイク | 35 | 793 |
| ド情熱逆さで使える消臭スプレー&速乾防水スプレー | 36 | 430 |
| 海老ドーン贅沢ぷりぷり海老マヨピザ | 24 | 429 |

トロリスタ・アプリクーポン・ホイールグローブは**対象外**（字コンテ未着 or 恒久放置）。

## 2. 候補の引き方（s34_FINAL3.json）

```bash
python3 - <<'PY'
import json
d = json.load(open("data/design/s34_FINAL3.json"))
p = d["products"]["おうちでライブマイク"]
for s in p["slots"]:
    print(s["slot"], s["function"], "|", s["telop"], "|",
          "%.2f秒" % s["dur_est"], "候補", len(s["candidates"]))
    for c in s["candidates"][:3]:
        print("   ", c["id"], c.get("shot"), c.get("comp"), "|", (c.get("action") or "")[:40])
PY
```

- 候補IDの `#` 以降は不透明トークン。**実時刻は `t0/t1` が正**
- `__NO_INSERT__` は**「置かない」という選択肢**。★これも必ず候補に入れる（恒久ルール）
- s34 は自分でこう宣言している: **「候補列挙とスコアまで。採否は人の原寸目視で決める」**

## 3. 追加の探索・裏取り（★実測主義）

候補リストの外を探したいとき・候補の実態を確かめるときは、**実素材を直接測る**。

```bash
SRC="$FERIEST_ROOT/00_source_drive/20260807_新素材_8月掲載分/海老ドーン贅沢ぷりぷり海老マヨピザ"

# 尺・回転メタ・解像度
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height:stream_side_data=rotation:format=duration \
  -of json "$SRC/20260803_honma_a0920.MP4"

# 区間を実画で見る（0.5秒刻みのサムネ列を出して Read で1枚ずつ目視）
ffmpeg -v error -ss 2.0 -to 3.1 -i "$SRC/20260803_honma_a0920.MP4" \
  -vf fps=2,scale=480:-2 /tmp/probe_%02d.jpg

# 白飛び率（輝度≥250の画素比。★絶対値でなく他カットとの相対で見る）
# → scripts/reference_match.py の G90-9 と同じ測り方
```

★**候補に挙がった窓は、採用前に必ず実画を目視する。** ラベル（`persons` / `action` / 分類）と
実画は食い違うことがある——実際に `person_count=0` の窓に素手の指が写っていた（他は全て黒手袋）。

## 4. ★素材の既知の罠（すべて実際に踏んだ）

| 罠 | 中身 |
|---|---|
| **向き** | 原本は全て 3840×2160 で返るが、**大半に rotation メタがあり実体は縦**。probe の w/h だけで判定すると全数「横」になる。真に横なのは5本（a0947 / a0950 / a0951 / a0803 / **a0933**）|
| **連番が商品をまたぐ** | `20260803_honma_a08xx.MP4` はフォルダ分けが撮影順と一致していない。★**フォルダ名の商品帰属を信用しない**（在庫表の product が正）|
| **ラベルと実画の食い違い** | 上記 §3。候補の実画目視は省略不可 |
| **選定の主キーは「何をしているか」** | 写っている物の列挙（inventory 的な情報）で照合すると偽陽性を量産する。動作・機能で選ぶ |
| **NFD 問題** | 日本語ファイル名は NFC/NFD の差で `os.path.exists` が False になることがある。`unicodedata.normalize` か glob で拾う |
| **`._*` AppleDouble** | 解析・列挙時は `-not -name "._*"` で除外 |

## 5. 検収（原本を新しく用意したとき）

```bash
python3 scripts/check_links.py --verify-media
```

在庫表と ffprobe 実測を突合して **欠け／DBに無い余分／尺ズレ（取り違え）／破損** を検出する
（188本で約3秒・欠陥注入で実証済み）。★Google Drive からの取得は取りこぼしが起きやすい
（`rclone lsjson -R` が 268本と出るが実際は315本、を実際に踏んだ。HANDBOOK 1節）。
