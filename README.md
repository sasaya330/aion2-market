# AION2 相場（バイゼル・天族）ギルド用ページ

ギルドのメンバーが URL を開くだけで、取引所の相場を見られるページです。
GitHub が1時間ごとに自動で相場を取り込んで更新するので、誰のPCも動かしておく必要はありません。

- タブ: 急変動・全相場・ほしい物・製作（品目をタップすると、期間を選べる値動きのグラフ）
- ほしい物: 目標の値段まで下がると「買い時」と表示。登録は各自のブラウザにだけ保存され、ほかの人には見えない
- 相場のデータ: Aion2Market（https://aion2.exchange）。日本語名: AION 2 データベース（https://aion2.th.gl/ja）。非公式のファンツール

## 公開のしかた（最初の1回だけ）

1. GitHub のアカウントを作る（https://github.com/signup 、無料）
2. 右上の「＋」→「New repository」で、名前を `aion2-market` にして **Public** で作る（他の項目はそのまま）
3. このフォルダで次を実行して送る（初回はブラウザで GitHub へのサインインを求められる）

   ```powershell
   git remote add origin https://github.com/<あなたのユーザー名>/aion2-market.git
   git push -u origin main
   ```

4. GitHub のリポジトリ画面で「Settings」→「Pages」→「Build and deployment」の **Source** を「**GitHub Actions**」にする
5. 「Actions」タブ →「update」→「Run workflow」を押す（2分ほどで終わる）
   - 手順3で送った直後に自動で1回動いて失敗していても問題ありません（手順4の前だったため）
6. `https://<あなたのユーザー名>.github.io/aion2-market/` を開いて表示を確かめ、ギルドに URL を共有する

## 動き

- `.github/workflows/update.yml` が毎時13分（日本時間も同じ）に `update.py` を動かし、`site/` を公開する
- 値動きの記録は、公開中のページの `history.json` を受け取って足していく（8日分）。初回だけ `seed/` を使う
- GitHub の都合で、数分〜十数分遅れて動くことがある
- **公開したリポジトリに60日間なにも変更がないと、GitHub が自動実行を止める**。その場合は「Actions」タブに出る案内から再開する

## 止め方

「Actions」タブ →「update」→ 右上の「…」→「Disable workflow」。ページごと消すときはリポジトリを削除する。
