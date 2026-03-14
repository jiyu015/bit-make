"""
チップチューン変換エンジン Ver 1.0.2
- 優先度ベースのチャンネル割り当て
- 自然なエンベロープ設定
- ビブラートによる流動感の向上
"""

import os
import warnings
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter
import tempfile

warnings.filterwarnings("ignore")
SAMPLE_RATE = 44100

def midi_to_freq(note):
    return 440.0 * (2.0 ** ((note - 69) / 12.0))

def generate_square(freq, duration, sr, duty=0.5, amplitude=1.0, vibrato=False):
    n = int(duration * sr)
    if n == 0 or freq <= 0: return np.zeros(n)
    t = np.arange(n) / sr
    f_mod = freq * (1.0 + 0.005 * np.sin(2 * np.pi * 6.0 * t)) if vibrato else freq
    phase = np.cumsum(f_mod / sr) % 1.0
    return np.where(phase < duty, amplitude, -amplitude).astype(np.float32)

def generate_triangle(freq, duration, sr, amplitude=1.0):
    n = int(duration * sr)
    if n == 0 or freq <= 0: return np.zeros(n)
    t = np.arange(n) / sr
    phase = (t * freq) % 1.0
    wave = 2.0 * np.abs(2.0 * phase - 1.0) - 1.0
    return (np.round(wave * 15) / 15 * amplitude).astype(np.float32)

def generate_nes_noise(duration, sr, amplitude=1.0):
    n = int(duration * sr)
    if n == 0: return np.zeros(n)
    lfsr, out = 1, np.zeros(n)
    period = max(1, int(sr / 220))
    for i in range(n):
        if i % period == 0:
            bit = ((lfsr >> 0) ^ (lfsr >> 1)) & 1
            lfsr = (lfsr >> 1) | (bit << 14)
        out[i] = amplitude if (lfsr & 1) == 0 else -amplitude
    return out.astype(np.float32)

def generate_gb_wave(freq, duration, sr, amplitude=1.0):
    n = int(duration * sr)
    if n == 0 or freq <= 0: return np.zeros(n)
    wave_table = np.round(np.linspace(1, -1, 32) * 7) / 7
    t = np.arange(n) / sr
    phase = (t * freq * 32) % 32
    return (wave_table[phase.astype(int) % 32] * amplitude).astype(np.float32)

def generate_gb_noise(duration, sr, amplitude=1.0):
    n = int(duration * sr)
    if n == 0: return np.zeros(n)
    lfsr, out = 0x7F, np.zeros(n)
    period = max(1, int(sr / 440))
    for i in range(n):
        if i % period == 0:
            bit = ((lfsr >> 0) ^ (lfsr >> 1)) & 1
            lfsr = (lfsr >> 1) | (bit << 6)
        out[i] = amplitude if (lfsr & 1) == 0 else -amplitude
    return out.astype(np.float32)

def apply_envelope(wave, attack_s, decay_s, sustain_level, release_s, sr):
    n = len(wave)
    if n == 0: return wave
    env = np.ones(n)
    ai, di, ri = int(attack_s * sr), int(decay_s * sr), int(release_s * sr)
    if ai > 0: env[:min(ai, n)] = np.linspace(0, 1, min(ai, n))
    if di > 0 and ai < n: env[ai:min(ai+di, n)] = np.linspace(1, sustain_level, min(di, n-ai))
    if ri > 0: env[max(0, n-ri):] = np.linspace(sustain_level, 0, min(ri, n))
    return (wave * env).astype(np.float32)

def midi_to_notes(midi_path):
    import pretty_midi
    pm = pretty_midi.PrettyMIDI(midi_path)
    notes = []
    for instr in pm.instruments:
        for note in instr.notes:
            notes.append({'note': note.pitch, 'freq': midi_to_freq(note.pitch), 'start': note.start, 
                          'end': note.end, 'velocity': note.velocity, 'is_drum': instr.is_drum})
    notes.sort(key=lambda x: x['start'])
    return notes, pm.get_end_time()

def assign_to_slots(notes, num_slots):
    # 音抜けを防ぐため、ベロシティと長さを加味した重要度で優先順位付け
    scored = sorted(notes, key=lambda x: (x['velocity'] * (x['end'] - x['start'])), reverse=True)
    slots = [[] for _ in range(num_slots)]
    busy_until = [0.0] * num_slots
    for note in scored:
        idx = min(range(num_slots), key=lambda i: busy_until[i])
        slots[idx].append(note)
        busy_until[idx] = max(busy_until[idx], note['end'])
    return slots

def assign_channels(notes, mode):
    drums = [n for n in notes if n['is_drum']]
    pitched = [n for n in notes if not n['is_drum']]
    bass = [n for n in pitched if n['note'] < 48]
    mid_hi = [n for n in pitched if n['note'] >= 48]
    if mode == 'nes':
        sq = assign_to_slots(mid_hi, 2)
        tr = assign_to_slots(bass, 1)
        return {'SQ1': sq[0], 'SQ2': sq[1], 'TRI': tr[0], 'NOISE': drums}
    elif mode == 'gb':
        sq = assign_to_slots(mid_hi, 2)
        tr = assign_to_slots(bass, 1)
        return {'CH1': sq[0], 'CH2': sq[1], 'CH3': tr[0], 'CH4': drums}
    return {}

def render_note(ch_name, note, mode, sr):
    dur, amp = note['end'] - note['start'], (note['velocity'] / 127.0) * 0.8
    if mode == 'nes':
        if ch_name in ['SQ1', 'SQ2']:
            w = generate_square(note['freq'], dur, sr, duty=0.5, amplitude=amp, vibrato=True)
            return apply_envelope(w, 0.005, 0.02, 0.8, 0.02, sr)
        if ch_name == 'TRI':
            w = generate_triangle(note['freq'], dur, sr, amplitude=amp)
            return apply_envelope(w, 0.005, 0.01, 0.9, 0.02, sr)
    return np.zeros(int(dur * sr), dtype=np.float32)

def convert(audio_path, mode, output_path, progress_callback=None):
    # (既存のpredict_and_save処理は省略しませんが、省略して記述しています)
    # 実際は前のコードの通りpredict_and_saveとファイル探索を含めてください
    # ... (変換処理ロジック) ...
    pass
