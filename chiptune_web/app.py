import os
import uuid
import threading
import shutil # 追加
from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024 
# 公開用フォルダを作成（永続化）
STORAGE_DIR = "downloads"
if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac'}
jobs = {}

def run_conversion(job_id, input_path, mode, output_path):
    try:
        jobs[job_id] = {'status': 'processing', 'progress': 0}
        from converter import convert
        convert(input_path, mode, output_path,
                progress_callback=lambda p: jobs[job_id].update({'progress': p}))
        jobs[job_id] = {'status': 'done', 'output': output_path}
    except Exception as e:
        jobs[job_id] = {'status': 'error', 'message': str(e)}
    finally:
        # inputだけ消す（outputはダウンロードまで残す）
        if os.path.exists(input_path):
            os.remove(input_path)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_audio():
    if 'file' not in request.files:
        return jsonify({'error': 'ファイルがありません'}), 400
    file = request.files['file']
    mode = request.form.get('mode', 'nes')
    
    job_id = str(uuid.uuid4())
    # 修正：tempfileではなくSTORAGE_DIRを使用
    input_path = os.path.join(STORAGE_DIR, f"{job_id}_in_{secure_filename(file.filename)}")
    output_path = os.path.join(STORAGE_DIR, f"{job_id}_out.wav")
    file.save(input_path)

    thread = threading.Thread(
        target=run_conversion,
        args=(job_id, input_path, mode, output_path)
    )
    thread.daemon = True
    thread.start()

    return jsonify({'job_id': job_id})

@app.route('/download/<job_id>')
def download(job_id):
    # ファイル名からpathを復元
    output_path = os.path.join(STORAGE_DIR, f"{job_id}_out.wav")
    if not os.path.exists(output_path):
        return jsonify({'error': 'ファイルがまだ作成されていないか、期限切れです'}), 404
    return send_file(output_path, as_attachment=True, download_name='chiptune_output.wav')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
