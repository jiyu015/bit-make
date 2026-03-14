import os
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    # テンプレートファイルを使わず、文字列としてHTMLを返す（ファイル読み込みエラー回避）
    return "<h1>Chiptune Service is Running.</h1><p>System Initialized.</p>"

if __name__ == '__main__':
    # RenderはPORT環境変数を必ず参照する必要がある
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
