# data/ledger — Notion が見られないときの代替台帳

`.fork/project.base.json` の `notion.ledger_offline` が指す場所。

> ★**Notion が見られない環境では `HANDBOOK.md` と `data/ledger/` で代替する。
> 台帳の更新義務そのものは消えない。**

Notion に繋がるなら**そちらが正**です。ここは繋がらない期間の受け皿で、
繋がったあと **Notion へ転記してから**このディレクトリの行を消さずに残します
（恒久ルール10「却下版も消さない」と同じ考え方）。

## ファイル

| | 対応する Notion | 何を書くか |
|---|---|---|
| `revision_records.jsonl` | Feriest 修正記録DB（`41e8866a-de56-829f-850d-0726dd063cdc`）| **py/jsx を作る・直すたびに1行** |
| `adoption.json` | 動画台帳（11DB体制）| 現在の採用 MP4 / 採用 py / 採用 v。★**採用が変わった瞬間に書く** |

`.jsonl` は1行1レコード。追記だけで、既存行は書き換えません。

## 書き方

```bash
# 修正記録を1行足す
python3 - <<'PY'
import json, io, datetime
rec = {
  "記録名": "0802 c03 の白飛び対策",
  "対象ファイル": "work/jsx_20260809/…（フルパスで）",
  "バージョン": "v2",
  "変更内容": "c03 を a0788#w0004 に差し替え",
  "変更理由": "★ユーザー指摘は原文引用: 「ここ白飛びしてない？」",
  "採用状態": "採用",          # 採用 / 却下 / 旧採用 / 未判定
  "却下理由": "",
  "検証方法": "★実測値を数字で: 輝度≥250の画素比 6.34% → 0.02%",
  "関連ファイルパス": "design/build_0802.json",
  "実行日時": datetime.datetime.now().isoformat(timespec="seconds"),
}
with io.open("data/ledger/revision_records.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
PY
```

## ★守ること（`PROJECT-RULES.md` から）

- **py・prproj・jsx は上書き禁止**。必ず新版・**却下版も消さない**
- **変更理由のユーザー指摘は原文引用**。要約しない
- **検証方法は実測値を数字で**書く（「直した」だけでは足りない）
- **採用が変わったのに台帳が未更新のまま「完了」と報告しない**
