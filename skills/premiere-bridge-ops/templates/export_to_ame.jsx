// export_to_ame.jsx — シーケンスを Adobe Media Encoder のキューへ投げる（非ブロッキング）
//
// なぜ exportAsMediaDirect ではなくこれか:
//   sequence.exportAsMediaDirect(...) は **その場でレンダーする**。
//   ExtendScript は同期なので、レンダーが終わるまでブリッジ全体が塞がる。
//   1時間の書き出しの間、他の動画の編集ジョブが1件も流れなくなる。
//   app.encoder.encodeSequence(...) は **AMEのキューに積んで即座に返る**（jobID を返す）。
//   Premiere は空くので、書き出し中も別プロジェクトの編集を進められる。
//   AME は別ソース同士を同時にエンコードしないので、キューは自動的に直列になる。
//
// prq.py 経由で投入すると prqResolveProject() / prqFindSequence() が使える。
// --doc-id を渡していれば、そのプロジェクトが **フロントに無くても** 対象にできる。

// ==== 埋める ====
var SEQ_ID     = "";     // 対象シーケンスの sequenceID（dump_state 等で実測して入れる）
var OUT_PATH   = "";     // 出力先の絶対パス（拡張子はプリセットに合わせる）
var PRESET_EPR = "";     // .epr の絶対パス。縦型は "Match Source - High bitrate"
var WORK_AREA  = 0;      // 0=シーケンス全体 / 1=イン点〜アウト点 / 2=ワークエリア
var REMOVE_ON_DONE = 0;  // 1 でAMEのキューから完了後に消す。0 なら残して履歴にする
var START_NOW  = true;   // AMEのバッチを即開始するか
// ================

var out = [];

if (!SEQ_ID || !OUT_PATH || !PRESET_EPR)
    return "★中断: SEQ_ID / OUT_PATH / PRESET_EPR が未設定";

var proj = prqResolveProject();
if (!proj) return "★中断: 対象プロジェクトが開いていない（documentID 不一致）";
out.push("proj=" + proj.name);

var seq = prqFindSequence(proj, SEQ_ID);
if (!seq) return "★中断: sequenceID が見つからない " + SEQ_ID + " in " + proj.name;
out.push("seq=" + seq.name);

// プリセットが無いまま投げると AME 側で静かに落ちる
if (!(new File(PRESET_EPR)).exists)
    return "★中断: .epr が無い " + PRESET_EPR;

// 出力先ディレクトリが無いと失敗する
var outFolder = (new File(OUT_PATH)).parent;
if (!outFolder.exists)
    return "★中断: 出力先ディレクトリが無い " + outFolder.fsName;

// 既存ファイルがあると AME は別名で書くことがある。上書きせず気づけるように報告する
if ((new File(OUT_PATH)).exists)
    out.push("★警告: 出力先に既存ファイルがある（別名で書かれる可能性）");

app.encoder.launchEncoder();          // 起動していなければ起動（既に起動中なら無害）
app.encoder.setEmbeddedXMPEnabled(0); // XMP を混ぜない
app.encoder.setSidecarXMPEnabled(0);

var jobID = app.encoder.encodeSequence(
    seq, OUT_PATH, PRESET_EPR, WORK_AREA, REMOVE_ON_DONE
);

// 0 が返ったら投入自体に失敗している。jobID 文字列なら投入成功
if (!jobID || jobID === 0) return "★中断: encodeSequence が 0 を返した（投入失敗）";
out.push("jobID=" + jobID);

if (START_NOW) {
    app.encoder.startBatch();
    out.push("startBatch=called");
}

// ★ここで返るのは「キューに積めた」までであって「書き出せた」ではない。
// 完了は ame_watch.py で AME のログを見て確かめること。
out.push("NOTE=queued only, not rendered");
return out.join(" | ");
