---
name: short-telop-craft
description: ショート動画のテロップを参考動画から完全再現する（区間定義→実測→PNGレンダー→Premiereアニメ→画素検証）。部分強調・動き測定・書き出し検証の全手法
---

# short-telop-craft — テロップ完全再現・アニメ実装

**手順の正本は `references/TELOP-CRAFT.md`（＝ `_video-core/telop/` から配布）。必ず全文読んでから着手する。**

6工程: [1]区間定義（テロップは時間区間単位・1ショット=1テロップは破綻する）→
[2]様式実測（定常フレームで原寸実測・フチとグローは書き出した動画で合わせる）→
[3]動き実測（テンプレートマッチング。探索上限・-ssずれ・時系列ノイズの3罠）→
[4]PNGレンダー（約物詰め送り・base/emph分離で部分強調）→
[5]Premiere配置+アニメ（inPoint基準・敷き直し集約・エフェクト実測値表）→
[6]検証（書き出した実ファイルの画素で参考と数値突合）。

- 横断原則は `references/PRINCIPLES.md`（実測主義・書き出した実ファイルで確かめる §12）。
- 改善したら `_video-core/sync_core.sh pull short-telop-craft references/TELOP-CRAFT.md` → `push`。
- 出自と実測値付きの記録: Notion「テロップ工程の学び（Dec28_01 全精読・2026-08-03）」。
