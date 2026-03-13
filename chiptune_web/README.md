# 🎮 Chiptune Converter Web

音楽ファイルをレトロゲーム風チップチューンに変換するWebアプリです。

## ファイル構成

```
chiptune_web/
├── app.py              # Flaskサーバー
├── converter.py        # 変換エンジン
├── requirements.txt    # 必要ライブラリ
├── render.yaml         # Render.com設定
├── templates/
│   └── index.html      # Webページ
└── README.md
```

---

## 公開手順（GitHubとRender.comを使う）

### Step 1: GitHubにアップロード

1. GitHub (https://github.com) にログイン
2. 右上の「+」→「New repository」をクリック
3. Repository name に `chiptune-converter` と入力
4. 「Create repository」をクリック
5. 「uploading an existing file」をクリック
6. このフォルダの中身を全部ドラッグ＆ドロップ
7. 「Commit changes」をクリック

### Step 2: Render.comにデプロイ

1. https://render.com にアクセスしてGitHubアカウントでサインアップ
2. 「New +」→「Web Service」をクリック
3. 「Connect a repository」でさっき作ったリポジトリを選択
4. 設定は自動で入るのでそのまま「Create Web Service」をクリック
5. デプロイが完了すると `https://chiptune-converter.onrender.com` のようなURLが発行される

### 完了！

発行されたURLにアクセスすればサイトが使えます。

---

## 注意事項

- Render.com の無料プランでは変換に時間がかかる場合があります（6分の曲で10〜20分）
- 無料プランはしばらく使わないとスリープします（最初のアクセスに30秒ほどかかります）
- ファイルサイズは50MBまで対応
