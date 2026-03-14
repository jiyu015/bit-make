import os
import soundfile as sf
from flask import Flask, request, send_file
import converter

app = Flask(__name__)

# ファイルアップロードの制限（最大16MB）
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return "ファイルがありません", 400
        
        file = request.files['file']
        if file.filename == '':
            return "ファイルが選択されていません", 400
        
        # 一時ファイルとして保存して変換
        input_path = os.path.join('/tmp', file.filename)
        file.save(input_path)
        
        try:
            # 変換実行
            wave, sr = converter.convert_to_chiptune(input_path)
            
            # 出力用ファイル作成
            output_path = '/tmp/chiptune.wav'
            sf.write(output_path, wave, sr)
            
            return send_file(output_path, as_attachment=True)
        except Exception as e:
            return f"変換中にエラーが発生しました: {str(e)}", 500

    # フォームを表示
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
