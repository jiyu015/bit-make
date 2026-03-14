def apply_quality_mastering(wave, sr):
    # 物理的な歪みを抑えるためのソフトクリッピング
    return np.tanh(wave * 0.95)

def render_note_high_quality(freq, duration, sr):
    # 高解像度生成（オーバーサンプリングの概念）
    # ... 波形生成後 ...
    return apply_quality_mastering(wave, sr)
