import os
import uuid
import threading
from flask import Flask, request, jsonify, send_from_directory, render_template
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024 

# 永続的な保存ディレクトリを確実に作成
STORAGE_DIR = os.path.join(os.getcwd(), 'downloads')
if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ジョブ管理
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
        # 入力ファイルは変換後速やかに削除して容量を節約
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
    
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': '不正なファイルです'}), 400

    job_id = str(uuid.uuid4())
    # job_id をファイル名に含めることで競合を回避
    input_filename = f"{job_id}_{secure_filename(file.filename)}"
    output_filename = f"{job_id}_out.wav"
    
    input_path = os.path.join(STORAGE_DIR, input_filename)
    output_path = os.path.join(STORAGE_DIR, output_filename)
    
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
    filename = f"{job_id}_out.wav"
    # ファイルが物理的に存在するか確認
    if not os.path.exists(os.path.join(STORAGE_DIR, filename)):
        return jsonify({'error': 'ファイルがまだ作成されていないか、存在しません'}), 404
        
    # send_from_directory で確実に配信
    return send_from_directory(STORAGE_DIR, filename, as_attachment=True, download_name='chiptune_output.wav')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
