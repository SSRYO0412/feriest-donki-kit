# Fish Audio API — 実測済みの注意点 (2026-07-01)

## エンドポイント
- TTS生成: `POST https://api.fish.audio/v1/tts`
  - ヘッダ: `Authorization: Bearer <key>`, `Content-Type: application/json`, `model: s2.1-pro-free` (無料枠モデル)
  - ボディ: `{"text": "...", "reference_id": "<voice or model id>", "format": "mp3"}`
- 音声モデル一覧/検索: `GET https://api.fish.audio/model?tag=<tag>&title=<url-encoded>&sort_by=task_count&page_size=<n>`
  - 日本語ナレーション系ボイスは `tag=narration` や `title=ナレーション`(URLエンコード)で検索すると見つかる。`tag=japanese`単体だとアニメキャラのファンクローンばかり出やすい
- クローンモデル作成: `POST https://api.fish.audio/model` (multipart/form-data)
  - フィールド: `type=tts`, `title`, `train_mode=fast`, `voices=@<audio file>`, `texts=<参照音声の書き起こし>`, `visibility=private`, `enhance_audio_quality=true`
  - `train_mode=fast` は即座に `state: trained` で返る(学習待ちなし)

## 感情タグの書式(S2/S2.1系)
- `[tag]` を**変化させたい箇所の直前**にインラインで置く。プリセットに限定されない自由記述(`[excited]`, `[calm][reassuring]`, `[slow]` 等を複数レイヤー可)
- 旧世代のS1モデルは丸括弧 `(happy)` + 固定タグセットなので混同しないこと

## 動かなかったこと(実測、2026-07-01)
インラインのゼロショットクローン(`references: [{"audio": "<base64>", "text": "..."}]` をTTSリクエストに直接含める方式)は**一貫して失敗した**:
- WAV/MP3どちらでも失敗
- data URIプレフィックス有無どちらでも失敗
- 10秒・20秒クリップどちらでも失敗
- **Fish Audio自身が生成した音声を参照として渡しても失敗**(＝リクエストの中身の問題ではなく、この経路自体が機能していない可能性が高い)
- 常に `{"message":"Reference Audio is not valid, please check your reference audio","status":400}`

→ **確実に動くのは `POST /model` でモデルを先に作り、その `_id` を `reference_id` として使う方式**。この方式は一発で成功した。

## APIキーの扱い
- チャットに生キーを貼らせない/貼らない。ユーザーに `!` プレフィックスでローカルシェルから直接ファイルに保存してもらう:
  ```bash
  read -rsp "Fish Audio API Key: " FK && printf '%s' "$FK" > .fishkey && chmod 600 .fishkey && unset FK
  ```
- `security find-generic-password` 等のKeychainコマンドはBash権限でブロックされる環境があるため、それが拒否されたら上記のローカルファイル方式にフォールバックする
- チャットに誤って生キーが貼られた場合は、処理は続行してよいが、テスト後のローテーション(再発行)をユーザーに勧める

## 音声フォーマット
- 参照音声・出力ともに `mp3`(44.1kHz, mono)で問題なく通る。ffmpegで `-codec:a libmp3lame -qscale:a 2` 程度で十分
