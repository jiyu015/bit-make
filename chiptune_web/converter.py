import numpy as np
import librosa

def convert_to_chiptune(file_path):
    # 1. 音声を読み込み、モノラルに変換
    y, sr = librosa.load(file_path, sr=22050, mono=True)
    
    # 2. 矩形波（チップチューン）への変換
    # 振幅が0より大きければ1.0、小さければ-1.0にする
    chiptune_wave = np.where(y > 0, 1.0, -1.0)
    
    # 3. ソフトクリッピング（過度なデジタル歪みを抑える）
    chiptune_wave = np.tanh(chiptune_wave * 0.95)
    
    return chiptune_wave, sr
