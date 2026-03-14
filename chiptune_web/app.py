import os
import uuid
import threading
import io
from flask import Flask, request, jsonify, send_file, render_template

app = Flask(__name__)
# メモリ制限を考慮しつつ効率的に処理
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024 

# ジョブ状態の保持
jobs = {}

def process_audio_in_memory(job_id, file_data, mode):
    """
    メモリ空間内でのみ変換を行うパイプライン
    """
    try:
        jobs[job_id] = {'status': 'processing', 'progress': 0}
        
        # converterの変換関数をインポート
        from converter import convert
        
        # 一時的なメモリバッファとしてBytesIOを使用
        output_buffer = io.BytesIO()
        
        # 変換ロジックへのパス（実際の実装に合わせ適宜調整）
        # ※converter.pyがメモリを直接扱えるよう設計されているのが理想的
        # ここでは簡易化のため、最終出力をメモリへ格納
        # 実際には convert 関数に BytesIO を渡せるよう設計変更を推奨
        
        # 変換実行後、output_buffer にデータを書き込む処理
        # ... (変換ロジック) ...
        
        jobs[job_id] = {'status': 'done', 'data': output_buffer.getvalue()}
    except Exception as e:
        jobs[job_id] = {'status': 'error', 'message': str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_audio():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    mode = request.form.get('mode', 'nes')
    job_id = str(uuid.uuid4())
    
    # データをメモリに読み込む
    file_data = file.read()
    
    # スレッドで非同期処理
    threading.Thread(target=process_audio_in_memory, args=(job_id, file_data, mode)).start()
    
    return jsonify({'job_id': job_id})

@app.route('/download/<job_id>')
def download(job_id):
    job = jobs.get(job_id)
    if not job or job['status'] != 'done':
        return jsonify({'error': 'Processing or not found'}), 404
        
    return send_file(
        io.BytesIO(job['data']),
        mimetype='audio/wav',
        as_attachment=True,
        download_name='chiptune_output.wav'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
