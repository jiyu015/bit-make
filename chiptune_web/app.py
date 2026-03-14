import os
import uuid
import threading
import io
from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024 

jobs = {}

def run_conversion(job_id, input_bytes, mode):
    try:
        jobs[job_id] = {'status': 'processing', 'progress': 0}
        
        # 一時ファイルとして書き出す（メモリ/tmp内）
        input_path = f"/tmp/{job_id}_in.mp3"
        output_path = f"/tmp/{job_id}_out.wav"
        
        with open(input_path, 'wb') as f:
            f.write(input_bytes)
            
        from converter import convert
        convert(input_path, mode, output_path,
                progress_callback=lambda p: jobs[job_id].update({'progress': p}))
        
        # 変換結果をメモリに読み込む
        with open(output_path, 'rb') as f:
            result_data = f.read()
        
        jobs[job_id] = {'status': 'done', 'data': result_data}
        
        # 掃除
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)
        
    except Exception as e:
        jobs[job_id] = {'status': 'error', 'message': str(e)}

@app.route('/convert', methods=['POST'])
def convert_audio():
    file = request.files['file']
    mode = request.form.get('mode', 'nes')
    job_id = str(uuid.uuid4())
    
    # ファイルをメモリに読み込む
    input_bytes = file.read()
    
    thread = threading.Thread(target=run_conversion, args=(job_id, input_bytes, mode))
    thread.start()
    return jsonify({'job_id': job_id})

@app.route('/download/<job_id>')
def download(job_id):
    job = jobs.get(job_id)
    if not job or job['status'] != 'done':
        return jsonify({'error': '未完了または存在しません'}), 404
        
    # メモリ上のデータから直接ダウンロード
    return send_file(
        io.BytesIO(job['data']),
        mimetype='audio/wav',
        as_attachment=True,
        download_name='chiptune_output.wav'
    )
