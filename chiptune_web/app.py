import os
import uuid
import threading
import io
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)
# 変換ジョブを保持する辞書
jobs = {}

# 変換ロジックを非同期で実行するためのブリッジ関数
def run_conversion_task(job_id, file_data, mode):
    try:
        jobs[job_id] = {'status': 'processing', 'progress': 0}
        
        # converter.pyの変換処理をインポート
        from converter import convert
        
        # 実際には convert 関数を「メモリ上のデータを直接受け取り、メモリ上のデータを返す」ように
        # 修正する必要がありますが、まずは基盤を安定させます。
        # ここでメモリベースの変換を実行します。
        output_buffer = io.BytesIO()
        
        # 変換実行 (ダミー実装: 実際はここを converter.convert に繋ぎます)
        # 成功時にデータを bytes として格納
        jobs[job_id] = {'status': 'done', 'data': b"dummy_wave_data"} 
        
    except Exception as e:
        jobs[job_id] = {'status': 'error', 'message': str(e)}

@app.route('/')
def index():
    # ポーリング機能を内蔵したフロントエンド
    return """
    <!DOCTYPE html>
    <head><title>Chiptune Converter</title></head>
    <body>
        <h2>Chiptune Converter (ver 2.0.0)</h2>
        <input type="file" id="f">
        <button id="b" onclick="u()">変換開始</button>
        <p id="s">待機中...</p>
        <script>
            async function u() {
                let d = new FormData(); d.append('file', document.getElementById('f').files[0]);
                document.getElementById('s').innerText = '変換中...';
                let r = await fetch('/convert', {method:'POST', body:d});
                let j = await r.json();
                poll(j.job_id);
            }
            async function poll(id) {
                let r = await fetch('/status/'+id);
                let d = await r.json();
                if (d.status === 'done') { window.location.href = '/download/'+id; }
                else if (d.status === 'error') { alert('エラー'); }
                else { setTimeout(()=>poll(id), 2000); }
            }
        </script>
    </body>
    </html>
    """

@app.route('/convert', methods=['POST'])
def convert_audio():
    file = request.files.get('file')
    mode = request.form.get('mode', 'nes')
    if not file: return jsonify({'error': 'No file'}), 400
    
    job_id = str(uuid.uuid4())
    threading.Thread(target=run_conversion_task, args=(job_id, file.read(), mode)).start()
    return jsonify({'job_id': job_id})

@app.route('/status/<job_id>')
def job_status(job_id):
    return jsonify(jobs.get(job_id, {'status': 'not_found'}))

@app.route('/download/<job_id>')
def download(job_id):
    job = jobs.get(job_id)
    if job and job['status'] == 'done':
        return send_file(io.BytesIO(job['data']), mimetype='audio/wav', as_attachment=True, download_name='out.wav')
    return "Not ready", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
