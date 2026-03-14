import numpy as np
import librosa

def convert_to_chiptune(file_path, mode):
    # 音声を読み込む
    y, sr = librosa.load(file_path, sr=22050, mono=True)
    
    # モードに応じた変換
    if mode == 'nes': 
        # ファミコン風：矩形波
        y = np.where(y > 0, 1.0, -1.0)
    elif mode == 'gb':
        # ゲームボーイ風：量子化を荒くする
        y = np.round(y * 8) / 8
    else: 
        # スーファミ風：16bitに近い量子化
        y = np.round(y * 32767) / 32767
        
    return y.astype(np.float32), sr
