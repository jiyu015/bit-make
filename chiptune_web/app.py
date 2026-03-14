import os
from flask import Flask, request, send_file

app = Flask(__name__)

# アップロードされたファイルを一時的にメモリで処理するための設定
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16MBまで

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return "ファイルがありません", 400
        
        file = request.files['file']
        if file.filename == '':
            return "ファイルが選択されていません", 400
        
        # ここで converter.py の関数を呼び出します
        # 例: converted_data = converter.process(file.read())
        
        return "変換成功（※現在は受け取りのみ実装中）"

    # HTMLフォームを返す
    return """
    <!DOCTYPE html>
    <html>
    <body>
        <h1>Chiptune Converter</h1>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept="audio/*">
            <input type="submit" value="変換開始">
        </form>
    </body>
    </html>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
