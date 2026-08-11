import json, os, sys

# ★パスをマシンに依存させない。雛形はこのキットに同梱してある（skills/short-video-qc/）。
#   framework 側の新しい雛形を使いたいときだけ GATES_TEMPLATE で明示する。
KIT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.environ.get(
    "GATES_TEMPLATE",
    os.path.join(KIT_ROOT, "skills/short-video-qc/references/gates.template.json"))
DST = os.path.join(KIT_ROOT, ".fork/gates.json")
if not os.path.exists(SRC):
    sys.exit("雛形が見つかりません: %s\n  → GATES_TEMPLATE=/path/to/gates.template.json で指定してください" % SRC)
t=json.load(open(SRC,encoding="utf-8"))

# --- 12レンズ（既存アナリスト7本を土台に、今回追加分を足す） ---
LENSES=[
 # 対象=設計案（5）
 ("G50-1","設計:意味の回収","editorial-analyst",
  "コンテの各語（例『ぷりぷり』『トロトロ』）に対応する画が割り当たっているか。語が映像で回収されていない箇所を挙げよ"),
 ("G50-2","設計:画と動作の重複","cut-analyst",
  "同じ動作・同じ絵が連続していないか。別クリップでも『同じ絵』なら重複とみなせ。同一クリップの別区間使用も指摘せよ"),
 ("G50-3","設計:訴求の強さ","framing-analyst",
  "各スロットの画は、そのスロットの訴求として弱くないか。『単なる全景』『説明になっていない』を指摘せよ"),
 ("G50-4","設計:テンポ整合","pace-analyst",
  "REFERENCE-TARGETS.json の shots_per_telop / 尺中央値 / 最短14F と照らして逸脱を指摘せよ。cuts/分だけを合わせる設計は却下せよ"),
 ("G50-5","設計:権利・NG","claude-isolated",
  "第三者の顔・他社ロゴ・ロケ地特定・値札/QR等の写り込み、コンテ文言の改変を指摘せよ。★今回は顔出しOK（顔を理由に却下しない）"),
 # 対象=テロップ（3）
 ("G51-1","テロップ:参考様式との一致","telop-analyst",
  "REFERENCE-TARGETS.json の telop_grammar と照合。書体/サイズ/色/フチ/縦位置/行間/群中心の逸脱を指摘せよ。★3階層(通常/感嘆/商品名2行組)の割当が妥当か"),
 ("G51-2","テロップ:可読性","claude-isolated",
  "背景平均色との ΔRGB を根拠に、埋もれている行を指摘せよ。参考帯93〜142・下限60。はみ出し・改行位置・隣接画像との衝突も見よ"),
 ("G51-3","テロップ:文言の改変","claude-isolated",
  "コンテ確定文言と1文字ずつ突合せよ。★一字でも違えば却下。レイアウト用の全角スペース追加は許容だが必ず報告せよ"),
 # 対象=完成品（4）
 ("G52-1","完成:全ショット目視","claude-isolated",
  "全ショットの代表フレーム（頭・中・尻）を見て、破綻・紛れ込み・意図しない写り込みを指摘せよ。見た枚数は分母/分子で申告せよ"),
 ("G52-2","完成:繋ぎの不自然さ","cut-analyst",
  "カット間の繋がりが不自然な箇所（同ポジ・ジャンプ・意味の飛躍）を指摘せよ"),
 ("G52-3","完成:参考との数値突合","claude-isolated",
  "qc/reference_match.json を読み、許容帯を外れた項目について『なぜ外れてよいのか』の説明が成立しているかを判定せよ。説明が無ければ却下"),
 ("G52-4","完成:機械検査の見落とし","claude-isolated",
  "機械検査が0件でも残る欠陥（測定器の盲点）を探せ。TRAPS.md の『測定器の盲点』7件を全部当てはめて確認せよ"),
]

new=[]
for g in t["gates"]:
    ex=str(g.get("executor","")).lower()
    gid=g["id"]
    if gid in ("G20","G21","G22"):
        g=dict(g); g["executor"]="claude-isolated-subagent"
        g["tool"]="隔離サブエージェント（作業ログ非開示）×並列"
        g["evidence"]=g["evidence"].replace("codex_view","independent_view")
        g["pass_condition"]="coverage_verify.py が PASS（全ファイル名の列挙を機械照合・欠番0）"
        g["_fork_note"]="Codex→隔離Claude。coverage_verify は返答の出所を問わないのでそのまま使える"
    elif gid in ("G40",):
        g=dict(g); g["executor"]="claude+independent"
        g["pass_condition"]="全超過区間に5択スコア、(e)は independent_approval 付き（2/3多数決）"
        g["_fork_note"]="codex_approval → independent_approval に一般化"
    elif gid in ("G41","G60"):
        g=dict(g); g["executor"]="script+independent"
        g["_fork_note"]="Codex→隔離Claude"
    elif gid in ("G50","G51","G52"):
        continue  # レンズへ展開するので親は落とす
    elif gid=="G71":
        g=dict(g); g["id"]="G71"; g["name"]="独立採点B（隔離サブエージェント2体目）"
        g["executor"]="claude-isolated-subagent"; g["tool"]="採点基準のみ渡す"
        g["evidence"]="qc/scoring/independent_b.json"
        g["_fork_note"]="Codex独立採点→2体目の隔離Claude。1体目(G70)とは別プロンプト・別レンズ"
    elif gid=="G72":
        g=dict(g); g["executor"]="subagent×2 + synthesizer"
        g["tool"]="相互指摘の往復 → core/common/agents/synthesizer.md が整合を裁定"
        g["pass_condition"]="合意スコアと合意経緯が記録済み。食い違い項目は往復の記録あり"
        g["_fork_note"]="Codexの代わりに synthesizer が次元間整合を点検して裁定"
    new.append(g)

# レンズ12本（各3回独立・2/3多数決）
for gid,name,agent,ask in LENSES:
    new.append({
        "id": gid, "name": name,
        "executor": "claude-isolated-subagent",
        "agent": agent,
        "rounds": 3,
        "decision": "2/3多数決。可否が割れたら却下側に倒す",
        "isolation": "作業ログ・制作側の理由を渡さない。成果物＋参考＋ルールのみ",
        "bias": "否定せよ。迷ったら却下（refuted=true をデフォルト）",
        "ask": ask,
        "tool": "Agent（隔離サブエージェント）",
        "evidence": f"qc/independent_review/{gid}.json",
        "pass_condition": "3ラウンド全て記録・多数決の結論あり・全指摘に採用/却下+理由",
        "status": "pending"
    })

# 新設ゲート
new += [
 {"id":"G90","name":"★参考突合（瓜二つ判定）","executor":"script",
  "tool":"scripts/reference_match.py","evidence":"qc/reference_match.json",
  "pass_condition":"REFERENCE-TARGETS.json の全項目が許容帯内。外れた項目は理由の記載があること",
  "_fork_note":"『瓜二つか』を感想でなく数値で判定する。判断ではなく測定なのでモデル多様性の問題を受けない",
  "status":"pending"},
 {"id":"G91","name":"★盲検ランキング","executor":"claude-isolated-subagent",
  "tool":"候補を伏せて順位付け","evidence":"qc/blind_ranking.json",
  "pass_condition":"全スロットで実施。レビューの1位と制作の1位が不一致の箇所は指摘として起票され採否記録あり",
  "_fork_note":"どれが採用案かを伏せて順位付けさせる。アンカリングを外す。Codexでもやっていなかった検査",
  "status":"pending"},
 {"id":"G92","name":"★較正ハーネス（既知欠陥の再検出）","executor":"script+claude-isolated-subagent",
  "tool":"scripts/calibration_harness.py",".fork":"known_defects.json",
  "evidence":"qc/calibration.json",
  "pass_condition":"測れる系5件=100%検出。判断系4件=3件以上(75%)検出。未検出は必ず名指しで報告",
  "_fork_note":"レビュー機構そのものの検出率を実測する。『Claudeでレビューしている』ではなく『既知欠陥N件中M件を検出した』と言えるようにする",
  "status":"pending"},
]

t["gates"]=new
t["project"]="feriest-donki (0801-0805)"
t["qc_profile"]={"_note":"★Codex不在環境。合格条件3・4を independent_review に一般化してフォーク側で上書き宣言している（PROJECT-RULES.md §合格条件）。master は一切変更していない",
  "profile":"FULL","approved_by":"","approved_at":"","sample_every_n":5,"series_first_video_id":"0801"}
t["_fork"]={
  "base":"video-ops-framework skills/short-video-qc/references/gates.template.json",
  "generated_at":"2026-08-11",
  "changes":"Codex実施12ゲート → 隔離Claude。G50/51/52 を12レンズ×3ラウンド=36レビューへ展開。G90/G91/G92 を新設",
  "review_count": len(LENSES)*3,
}
# ★Codex不在フォークとしての言い換え。
#   これを生成器に持たせないと、コミット済み gates.json を再現できない
#   （2026-08-11 に発覚: gates.json 側だけ手で直されていて、生成器を回すと差し戻っていた）。
#   雛形は framework 由来の編集禁止レイヤなので、書き換えはこの .fork 層で行う。
RENAME=[("Codex観察","独立観察"), ("Codex指摘箇所","独立レビューの指摘箇所")]
for g in t["gates"]:
    for k,v in list(g.items()):
        if isinstance(v,str):
            for a,b in RENAME: v=v.replace(a,b)
            g[k]=v

json.dump(t, open(DST,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"ゲート {len(t['gates'])} 本 / 独立レビュー {len(LENSES)*3} 回")
codex_left=[g["id"] for g in new if "codex" in json.dumps(g,ensure_ascii=False).lower()]
print("codex 残存:", codex_left if codex_left else "0件")
