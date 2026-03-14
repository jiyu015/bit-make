import os
import numpy as np
import librosa
import soundfile as sf
from flask import Flask, request, send_file
import converter

app = Flask(__name__)
UPLOAD_FOLDER = '/tmp'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        mode = request.form.get('mode', 'nes')
        fmt = request.form.get('format', 'wav')
        
        input_path = os.path.join(UPLOAD_FOLDER, file.filename)
        output_path = os.path.join(UPLOAD_FOLDER, f'output.{fmt}')
        
        file.save(input_path)
        
        try:
            wave, sr = converter.convert_to_chiptune(input_path, mode)
            sf.write(output_path, wave, sr)
            return send_file(output_path, as_attachment=True)
        except Exception as e:
            return f"変換エンジンエラー: {str(e)}", 500

    return """
    <style>
        body { background: #000; color: #0f0; font-family: monospace; text-align: center; padding-top: 50px; }
        .box { border: 2px solid #0f0; display: inline-block; padding: 20px; }
    </style>
    <div class="box">
        <h1>CHIPTUNE PRO</h1>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept="audio/*" required><br>
            <select name="mode">
                <option value="nes">NES (8-bit)</option>
                <option value="gb">GameBoy (Low-bit)</option>
                <option value="snes">SNES (16-bit)</option>
            </select><br>
            <select name="format">
                <option value="wav">WAV</option>
                <option value="flac">FLAC</option>
            </select><br>
            <input type="submit" value="CONVERT">
        </form>
    </div>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
