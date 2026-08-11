// guard.jsx — 全スクリプトの冒頭に置く定型（コピーして WANT_* を埋める）。
//
// なぜ必要か: app.project は「手前のプロジェクト」を返す。複数プロジェクトが開いているのは常態
// （実測で同時7本）。ユーザーが別プロジェクトを開いて確認した直後に気づかず作業を続け、
// 参考プロジェクトのSEを削除して書き出す事故が実際に起きた。
// 要点は「警告して続行」ではなく **中断して返す** こと。
//
// 日本語名は Premiere から NFD で返る（ブ=12501,12441 / ザ=12469,12441）。
// 素の === では一致しないので、文字コード配列で比較する。
// 配列は次で作れる:
//   python3 -c 'import sys,unicodedata as u; print(",".join(str(ord(c)) for c in u.normalize("NFD", sys.argv[1])))' 'ファイル名.mp4'

function s(a) { var r = ""; for (var i = 0; i < a.length; i++) r += String.fromCharCode(a[i]); return r; }
function eq(str, arr) {
    if (str.length !== arr.length) return false;
    for (var i = 0; i < arr.length; i++) if (str.charCodeAt(i) !== arr[i]) return false;
    return true;
}

// ==== ここを対象プロジェクトごとに埋める ====
var WANT_PROJ = [/* NFD charcodes of "xxx.prproj" */];
var WANT_SEQ  = [/* NFD charcodes of sequence name */];
var WANT_V0   = -1;  // V0 のクリップ枚数。実測して入れる（不変量。ズレたら別シーケンス）
// ================================

if (WANT_V0 < 0 || !WANT_PROJ.length || !WANT_SEQ.length)
    return "★中断: WANT_PROJ / WANT_SEQ / WANT_V0 が未設定";

var P = app.project;
if (!eq(P.name, WANT_PROJ)) return "★中断: 手前のプロジェクトが違う (" + P.name + ")";

var S = null;
for (var i = 0; i < P.sequences.numSequences; i++) {
    if (eq(P.sequences[i].name, WANT_SEQ)) { S = P.sequences[i]; break; }
}
if (!S) return "★中断: シーケンスが無い";
P.openSequence(S.sequenceID);
S = P.activeSequence;

if (S.videoTracks[0].clips.numItems !== WANT_V0)
    return "★中断: V0枚数違い (" + S.videoTracks[0].clips.numItems + ")";

// トラック数は必ず先に読む。シーケンスによって本数が違い（V0-V3 の4本だけのこともある）、
// videoTracks[4] を触ると "ExtendScript execution failed via CEP evalScript()" になる。
var NV = S.videoTracks.numTracks;

// ---- ここから本処理 ----

var out = [];
out.push("guard_ok nVtracks=" + NV);

// 結果は必ずファイルへ。evalScript の戻り値は長いと切れる。
// ★ファイル名は毎回変える（同名は前回の残骸を読む）。
var fo = new File("/tmp/premiere-mcp-bridge/RENAME_ME.txt");
fo.encoding = "UTF-8";
fo.open("w"); fo.write(out.join("\n")); fo.close();
return out.join(" | ");
