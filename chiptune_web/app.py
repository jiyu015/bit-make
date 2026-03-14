import os
import soundfile as sf
from flask import Flask, request, send_file, render_template_string
import converter

app = Flask(__name__)
UPLOAD_FOLDER = '/tmp'

# デザイン用のCSS
CSS = """
<style>
    body { background: #222; color: #0f0; font-family: 'Courier New', monospace; padding: 50px; text-align: center; }
    .container { background: #333; border: 2px solid #0f0; padding: 20px; border-radius: 10px; display: inline-block; }
    select, input { background: #000; color: #0f0; border: 1px solid #0f0; padding: 10px; margin: 10px; }
</style>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        mode = request.form['mode']
        fmt = request.form['format']
        
        input_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(input_path)
        
        wave, sr = converter.convert_to_chiptune(input_path, mode)
        output_path = os.path.join(UPLOAD_FOLDER, f'output.{fmt}')
        sf.write(output_path, wave, sr)
        
        return send_file(output_path, as_attachment=True)

    return f"""
    {CSS}
    <div class="container">
        <h1>Chiptune Converter PRO</h1>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept="audio/*" required><br>
            <select name="mode">
                <option value="nes">ファミコン風 (8-bit)</option>
                <option value="gb">ゲームボーイ風 (Low-bit)</option>
                <option value="snes">スーファミ風 (16-bit)</option>
            </select><br>
            <select name="format">
                <option value="wav">WAV形式</option>
                <option value="flac">FLAC形式</option>
            </select><br>
            <input type="submit" value="変換開始">
        </form>
    </div>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
