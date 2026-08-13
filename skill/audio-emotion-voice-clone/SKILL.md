# 音声の抑揚・感情解析 → Fish Audioでのボイスクローン再現 スキル

<!-- ここから: feriest-donki-kit 同梱時の追記 -->
## ★このキットで使うときの前提（2026-08-13 同梱時に追記）

**このスキルだけは追加インストールが要ります。** キット本体の SETUP.md は
「pip install は不要・numpy も Pillow も使いません」と書いていますが、それは
**このスキルを除く**前提です。使う前に揃えてください。

| 要るもの | 用途 | 入れ方 |
|---|---|---|
| `parselmouth`（Praat） | 抑揚・感情の定量分析 | `pip install praat-parselmouth` |
| `numpy` | 同上 | `pip install numpy` |
| `matplotlib` | 抑揚の可視化（`plot_prosody.py`） | `pip install matplotlib` |
| `requests` | Fish Audio API | `pip install requests` |
| `whisper` | 文字起こし（`transcribe.py`） | 別途導入 |
| `ffmpeg` | 音声の切り出し・変換 | キット本体でも使うので導入済みのはず |

**Fish Audio のキーはリポジトリに置かないでください。** 環境変数 `FISH_KEY`
（または `.fishkey` ファイル）から読む作りになっています。**キーをコミットしない**こと。

★本文中に Notion（`修正指示DB` / `レンダーpy管理DB` / `QAログDB`）を前提にした記述が
残っていますが、**このキットは台帳（VOPS Ledger）運用**です。記録先はキット側の運用に
読み替えてください（`skills/video-revision-db-workflow` を参照）。

★横断原則の参照先は、このキットでは **`core/PRINCIPLES.md`** です（同梱時に置換済み）。
<!-- ここまで -->


> ★動画/音声制作の横断原則（実測主義・検証の鉄則・閉ループ選別・承認ゲート）は `core/PRINCIPLES.md` を適用する。
> ★動画修正案件の音声再生成では `video-revision-db-workflow` も適用し、生成音声のパス、モデルID、差し替え対象秒数、採用レンダー、QA結果をNotionの `レンダーpy管理DB` と `QAログDB` に残す。

## Notion連携ルール

修正依頼がNotionの `修正指示DB` にある場合は、音声生成前に対象動画、対象秒数、過去修正、採用pyを確認する。生成後は音声ファイルを消さず、`音声ソース` としてレンダー記録に残す。冒頭欠け、語尾切れ、吐息、無音、食い込みが続いた場合は、トリムやフェードで粘らず再生成を優先する。

参考動画/音声から**話者の声質・抑揚・感情の起伏構造をPraatで精密に定量分析**し、その構造を維持したまま**別テキストをFish Audioでボイスクローン生成**するスキル。2026-07-01に実プロジェクト(健康サプリ系UGC広告ナレーションの分析・再現)で確立したワークフローをそのまま資産化したもの。

**このスキルを使う場面**:
- 「この動画の抑揚/感情を分析して、別の台本で同じ喋り方を再現したい」
- 「参考ナレーションの声をクローンして、違う文章を読ませたい」
- 「音声のBGMを除去してクリーンな声だけにしたい」
- 「音声の感情の山谷(フック/説明/安心訴求/CTAの緩急)を数値で可視化したい」

## 推奨: 汎用再現パイプライン(scripts/replicate_pipeline.py)

「元音声の喋り方を保ったまま台本を差し替える」用途は、個別スクリプトを組む前に**この2ステップパイプラインを使う**(v9方式の一般化。性別・声域・テンション・方言を問わず動く):

```bash
# 1. PLAN: 元音声から行ごとの目標(F0/語尾スロープ/尺/間)と話者統計を自動抽出
python3 scripts/replicate_pipeline.py plan original.wav transcript.json mapping.json

# 2. mapping.json の "text" を書き換える(表記プロソディ ! !? っ。 。 を維持)。
#    "tags" は自動提案(統計的外れ値の行のみ)を尊重し、原則触らない。"targets" は触らない。

# 3. RUN: 行ごとにK候補生成→z正規化スコアで機械選別→音量統一→元の間構造で結合
python3 scripts/replicate_pipeline.py run mapping.json --key-file .fishkey \
  --reference-id <クローンモデルID> --workdir v1_work --output final_v1.mp3
```

- ピッチ解析範囲は話者から自動推定(男性の低い声でも正しく計測される)
- スコアは話者の標準偏差で正規化したz単位(声域が違っても同じ重みで機能する)
- 低音レジスター行(`[low quiet voice]`)や叫び行(`[shouting]`)はplanが統計的に自動検出して提案
- 出力に `WEAK` と出た行だけ、K増加 or 表記/タグ微調整で個別リトライ
- workdirとoutputは**必ず版数付きで毎回変える**(過去の生成物は上書きしない)

以下の6フェーズは、このパイプラインの前段(音声抽出〜クローン作成)と、個別に深掘りが必要なときの手順。

## 全体ワークフロー(6フェーズ)

```
1. 音声抽出 (ffmpeg)
2. 文字起こし (faster-whisper, セグメント分割+タイムスタンプ)
3. Praat音響解析 (parselmouth: F0/強度/ジッター/シマー → z-score → 覚醒度(arousal)/緊張度(tension)スコア)
4. 可視化 (matplotlib: ピッチ曲線+強度曲線+感情スコアのタイムライン) → 必ず自分の目で見て検証
5. BGM除去 (Demucs: vocals/no_vocalsに分離) → クリーンな参照音声を作る
6. Fish Audio: クローンモデル作成(POST /model) → 感情タグ付き台本を新規に書く → TTS生成(POST /v1/tts)
```

各フェーズは独立して使える。「感情分析だけしたい」「クローンだけしたい」等、部分的な利用も可。

## フェーズ1: 音声抽出

```bash
ffmpeg -y -i "input.mov" -vn -ac 1 -ar 44100 -acodec pcm_s16le audio.wav
```

動画の音声はモノラル・44.1kHzのWAVに統一する(Praat解析・Whisper・Demucsいずれも問題なく扱える形式)。

## フェーズ2: 文字起こし

`scripts/transcribe.py` を使う。

```bash
python3 scripts/transcribe.py audio.wav transcript.json --language ja
```

**精度が悪い場合の対処(実証済み)**:
- `medium` モデル + `int8` 量子化は、専門語彙(業界用語・スラング等)が多い音声で精度が大きく落ちる。`large-v3` + `float32` に上げる
- `initial_prompt` にドメイン語彙(想定される専門用語・固有名詞)を渡すとデコードが安定する
- `condition_on_previous_text=False` にして誤り伝播(前セグメントの誤りが後続に連鎖するハルシネーション)を防ぐ
- それでも精度が完璧にならないことは多い。**転写テキストの一言一句が要件でないなら(=声の抑揚パターン抽出が目的なら)無理に精度を追求せず先に進んでよい**

## フェーズ3: Praat音響解析(精密・z-score・覚醒度スコア)

`scripts/deep_analyze.py` を使う。`transcript.json` のセグメント区切りごとに以下を計測:

- **F0 (基本周波数)**: 平均・レンジ・標準偏差・区間内の傾き(上昇/下降トレンド)
- **強度 (Intensity, dB)**: 平均・レンジ
- **ジッター/シマー**: 声帯の緊張度の物理指標(怒り・緊迫感の代理指標として使う)
- **話速**: 文字数/秒
- **ポーズ**: 前後の無音区間長

**重要: 閾値の決め打ちではなく、コーパス全体(その音声全体)平均・標準偏差に対する z-score で相対評価する。** 初期実装で「範囲の何割か」という粗い閾値分けをしたところ、山谷の呼吸パターン(例: フックの直前でわずかに沈む「タメ」)が埋もれて見えなくなった。z-score化して可視化して初めて、それが見えるようになった。

Arousal(覚醒度)・Tension(緊張度)スコアの算出式は `references/emotion_tag_mapping.md` 参照。

## フェーズ4: 可視化(必須)

`scripts/plot_prosody.py` でF0曲線・強度曲線・区間別arousalスコアの3段グラフをPNG出力し、**Readツールで自分の目で見て確認する**。数値の表だけでは山谷の呼吸パターンを見落とす。

## フェーズ5: BGM除去(Demucs)

広告ナレーション等は大抵BGM/効果音が乗っており、そのままだとボイスクローンの精度が落ちる。

```bash
python3 -m pip install --user demucs soundfile   # 初回のみ。torch/torchaudioも自動インストールされる
python3 -m demucs.separate -n htdemucs --two-stems=vocals -o separated audio.wav
# → separated/htdemucs/audio/vocals.wav (ボーカルのみ)
# → separated/htdemucs/audio/no_vocals.wav (BGM/効果音のみ)
```

**ハマりどころ**: torchaudioの保存時に `Couldn't find appropriate backend` エラーが出ることがある → `soundfile` パッケージ未インストールが原因。`pip install soundfile` で解消する。

クローン用の参照音声は、この `vocals.wav` から切り出す(BGM混入なしのクリーンな10〜30秒区間)。

## フェーズ6: Fish Audio クローン生成

### APIキーの扱い(重要・セキュリティ)
チャットに生キーを貼らない。Keychain経由の読み取りがBash権限でブロックされる環境もあるため、ユーザーに以下を`!`プレフィックスで実行してもらい、ローカルの保護ファイルに保存する方式が確実:

```bash
! read -rsp "Fish Audio API Key: " FK && printf '%s' "$FK" > .fishkey && chmod 600 .fishkey && unset FK
```

以降 `FISH_KEY=$(cat .fishkey)` で読み込む。

### クローンモデル作成(推奨方式)
`references` フィールドをインラインでTTSリクエストに渡すゼロショットクローンは**動作しないことがある**(2026-07-01実測: 有効なmp3/wavをbase64で渡しても `"Reference Audio is not valid"` で一貫して400が返った。data URIプレフィックスの有無、10秒/20秒どちらの長さでも失敗、Fish Audio自身が生成した音声を参照に使っても失敗=リクエスト形式そのものが機能していない可能性が高い)。

**確実に動くのは `POST /model` でのモデル作成方式**:

```bash
curl -sS -X POST "https://api.fish.audio/model" \
  -H "Authorization: Bearer $FISH_KEY" \
  -F "type=tts" \
  -F "title=my_clone_$(date +%s 2>/dev/null || echo test)" \
  -F "train_mode=fast" \
  -F "voices=@reference_clip.mp3;type=audio/mpeg" \
  -F "texts=<参照音声の書き起こしテキスト>" \
  -F "visibility=private" \
  -F "enhance_audio_quality=true"
```

レスポンスの `_id` が `reference_id`。`state: trained` ならすぐ使える(学習待ちなし)。

### 感情タグ付き台本を書く
Fish Audio S2モデルはテキスト中に `[タグ]` を**変化させたい箇所の直前**に埋め込む方式(自由記述可、プリセットに限定されない)。フェーズ3-4で得た覚醒度パターンをタグに変換する対応表は `references/emotion_tag_mapping.md`。

**タグ調整で微妙な結果が続く・語尾や細かい抑揚が合わないときは、必ず `references/prosody_control_playbook.md` を読む**(制御手段のはしご: 表記プロソディ→タグ規律→参照キュレーション→閉ループ候補選別→ポスト編集→ツール昇格)。要点: 音響仕様の長文タグや演技指示タグは効かない/事故る、日本語は表記(促音・記号)が最強レバー、生成候補はPraat計測で機械選別する。

### 生成
```bash
curl -sS -X POST "https://api.fish.audio/v1/tts" \
  -H "Authorization: Bearer $FISH_KEY" \
  -H "Content-Type: application/json" \
  -H "model: s2.1-pro-free" \
  -d '{"text": "<感情タグ付きテキスト>", "reference_id": "<モデルID>", "format": "mp3"}' \
  --output out.mp3
```

## 台本を新規に書く場合の鉄則(コンプライアンス、2026-07-01の実例から)

**元音声/参考動画が誇大な効能表現(医薬品的な治療効果・具体的な数値効果の保証等)を含む場合、それをそのまま模倣した新規台本を創作しない。** 特に健康食品・サプリメント・美容系商材で「治る」「○秒で」「○センチ」「絶対に」のような未承認の効能効果を保証する文言は、たとえ既存の参考音声のニュアンス再現が目的でも、薬機法等の誇大広告に抵触する新規コンテンツを生成することになるため断る。

**対処**: 抑揚・感情の起伏構造(フック→説明→安心訴求→再フック→CTAという構成、山谷のタイミング)だけを踏襲し、具体的な効能保証を含まない一般的な表現(「サポート」「実感する方も」「個人差があります」等)に置き換えた台本を書く。技術検証(抑揚パターンの再現)が目的であることをユーザーに明示した上で進める。

## 依存パッケージ一覧

```bash
python3 -m pip install --user praat-parselmouth faster-whisper numpy matplotlib scipy demucs soundfile requests
```

Demucsは初回実行時にモデル(~80MB)を自動ダウンロードする。ffmpegはHomebrew等で別途インストール済みであること。

## 作業ディレクトリの慣例
プロジェクトごとに `~/Documents/<project-name>/` を作り、`audio.wav` / `transcript.json` / `deep_acoustic_analysis.json` / `prosody_emotion_chart.png` / `separated/` / `.fishkey` を集約する。`.fishkey` は `.gitignore` 相当の扱い(バージョン管理・共有をしない)。

## 2026-07-02/06 追記: VERARUS VOバッチで判明した必須工程

- **行別ラウドネスのソフト正規化(必須)**: replicate_pipelineのnorm_XXは行間の統合ラウドネス差が最大16LU残ることがある(行によって声が沈む/飛び出す→ミックスLRA超過)。結合前に各行のLUFSを実測し**中央値±4LUへクランプ**する(ゲインのみ・タイミング不変)。基準実績: 承認済みバッチはスプレッド≒8LU。
- **数値・固有名詞の読み**: 「6.5cm」等はミスりやすい→「プラスろくてんごセンチ」等の明示ひらがな表記にし、生成後に逆転写QAで全行確認。ASRの同音限界(高見え/高みへ)は入力カナ化で担保し、行位置で対応付ける。
- **展開手順**: まず1本生成→ユーザー確認→全台本展開(いきなり量産しない)。
- **参考音声との一致検証**: 提出前に 尺/発話密度(文字/秒)/ラウドネス(I/TP/LRA)/F0帯/間の構造(silencedetect) を参考と実測比較し、Codex等の独立検査を通す。全体尺の一致だけでは不十分(間が多くて発話が同速でも体感が変わる)。
- **globの罠**: `<id>_work*` はリトライの `_work2` も拾い二重連結する。workdirは常に完全一致パスで指定。
