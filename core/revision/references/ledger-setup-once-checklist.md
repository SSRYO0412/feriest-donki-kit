# 台帳セットアップ 一回作業チェックリスト（案件を作った直後に1回だけ）

> 対象: VOPS Ledger の新しい `project_id`。**13DBは `notion_bootstrap.py vops:<project_id>` が用意する**ので、
> ここでやるのは「その案件に合わせる」ぶんだけ。全操作は MCP（`schema_edit` / `schema_list` / `ledger_query`）で通る。
> 上位規範は `ledger-db-contract.md`（§0 触り方・§10 ビュー）。
>
> ★Notion 時代の「UI で1回やる作業」（unique_id 追加・relation の双方向化・rollup）は**台帳では不要**。
> 版番号は台帳が自動で持ち（`ledger_history`）、relation は片側に張れば逆参照でき、
> 採用vの鏡は `notion_autolink.py --apply` が生成する。この節は**廃止**した。

- [ ] **`whoami` で会社と `writable` を確認した**（HTTP MCP の場合。`vops-<会社>` を取り違えていない）
- [ ] **`schema_list` で13 db_key が揃っていることを確認した**
      （`project_ledger` / `video_ledger` / `asset_db` / `cut_ledger` / `asset_use_db` /
      `revision_request_db` / `render_db` / `qa_log_db` / `schedule_db` / `telop_check_db` /
      `script_db` / `revision_ledger` / `project_rules_db`）
- [ ] **`project_ledger` に案件行を1行作った**（プロジェクト名・クライアント・案件フォルダ・納品フォルダ・共通ルール）
- [ ] **`vops ledger link <project_id> <案件ルート>` を実行した**（`path_rel` の基準。未登録でも壊れないが、
      パスの突合が効かなくなる）
- [ ] **案件固有の列・選択肢を `schema_edit` で足した。`project_id` を付けた**
      （付け忘れると会社共通＝他案件の初期値を変えてしまう）
- [ ] **時間軸のあるDBの既定ビューを `set_view` + `first: true` で確認・設定した**（契約§10-1 の表）
      → `revision_ledger` / `script_db` / `cut_ledger` / `telop_check_db` / `schedule_db`
- [ ] **`ledger_query` で実際に引いて、先頭が0秒・グループが `video_id` になっていることを確認した**
      （設定した申告だけで「時系列にした」と言わない）
- [ ] （修正案件）**`revision_ledger` の記入用ビューに `修正指示` と `採否` が
      横スクロールなしで見える位置にある**ことを UI で確認した（`REVISION-LEDGER.md` §3.3）
- [ ] （任意）**未完了ビュー**を足した: `revision_request_db`（ステータス≠納品済み/却下/保留）、
      `render_db`（`採用状態=却下` 一覧＝却下履歴の一覧性）
- [ ] **ユーザーに UI の URL と「どこに何を書くか」の1文を渡した**

完了したら日付を記録: ____年__月__日 実施 / project_id: ____________
