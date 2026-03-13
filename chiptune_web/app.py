import os
import uuid
import tempfile
import threading
from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB制限

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 変換ジョブの状態管理
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
    if mode not in ('nes', 'gb', 'snes'):
        return jsonify({'error': '不正なモードです'}), 400
    if file.filename == '':
        return jsonify({'error': 'ファイルを選択してください'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': '対応していないファイル形式です'}), 400

    job_id = str(uuid.uuid4())
    tmpdir = tempfile.mkdtemp()
    filename = secure_filename(file.filename)
    input_path = os.path.join(tmpdir, filename)
    output_path = os.path.join(tmpdir, f'output_{mode}.wav')
    file.save(input_path)

    thread = threading.Thread(
        target=run_conversion,
        args=(job_id, input_path, mode, output_path)
    )
    thread.daemon = True
    thread.start()

    return jsonify({'job_id': job_id})

@app.route('/status/<job_id>')
def job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'status': 'not_found'}), 404
    return jsonify(job)

@app.route('/download/<job_id>')
def download(job_id):
    job = jobs.get(job_id)
    if not job or job['status'] != 'done':
        return jsonify({'error': 'ファイルが見つかりません'}), 404
    output_path = job['output']
    if not os.path.exists(output_path):
        return jsonify({'error': 'ファイルが削除されました'}), 404
    return send_file(output_path, as_attachment=True,
                     download_name='chiptune_output.wav',
                     mimetype='audio/wav')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
