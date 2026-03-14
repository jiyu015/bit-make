import numpy as np
import librosa

def convert_to_chiptune(file_path, mode):
    y, sr = librosa.load(file_path, sr=22050, mono=True)
    
    # モードに応じたビット深度/解像度調整
    if mode == 'nes': # ファミコン風 (鋭い矩形波)
        y = np.where(y > 0, 1.0, -1.0)
    elif mode == 'gb': # ゲームボーイ風 (少し丸みを帯びた波)
        y = np.sign(y) * np.abs(y)**0.5
    else: # スーファミ風 (16bit風の粗い量子化)
        y = np.round(y * 16) / 16
        
    return y, sr
