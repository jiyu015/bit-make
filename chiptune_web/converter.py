"""
チップチューン変換エンジン
app.py から呼び出される変換処理本体
"""

import os
import warnings
warnings.filterwarnings("ignore")

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter

SAMPLE_RATE = 44100

PSG_VOL_TABLE = np.array([
    0, 0.01, 0.0138, 0.0190, 0.0262, 0.0362, 0.0500, 0.0690,
    0.0952, 0.131, 0.181, 0.250, 0.345, 0.476, 0.657, 1.0
])

def midi_to_freq(note):
    return 440.0 * (2.0 ** ((note - 69) / 12.0))

def generate_square(freq, duration, sr, duty=0.5, amplitude=1.0):
    n = int(duration * sr)
    if n == 0 or freq <= 0:
        return np.zeros(n)
    t = np.arange(n) / sr
    phase = (t * freq) % 1.0
    return np.where(phase < duty, amplitude, -amplitude).astype(np.float32)

def generate_triangle(freq, duration, sr, amplitude=1.0):
    n = int(duration * sr)
    if n == 0 or freq <= 0:
        return np.zeros(n)
    t = np.arange(n) / sr
    phase = (t * freq) % 1.0
    wave = 2.0 * np.abs(2.0 * phase - 1.0) - 1.0
    wave = np.round(wave * 15) / 15
    return (wave * amplitude).astype(np.float32)

def generate_nes_noise(duration, sr, amplitude=1.0):
    n = int(duration * sr)
    if n == 0:
        return np.zeros(n)
    lfsr = 1
    out = np.zeros(n)
    period = max(1, int(sr / 220))
    for i in range(n):
        if i % period == 0:
            bit = ((lfsr >> 0) ^ (lfsr >> 1)) & 1
            lfsr = (lfsr >> 1) | (bit << 14)
        out[i] = amplitude if (lfsr & 1) == 0 else -amplitude
    return out.astype(np.float32)

def generate_gb_wave(freq, duration, sr, amplitude=1.0):
    n = int(duration * sr)
    if n == 0 or freq <= 0:
        return np.zeros(n)
    wave_table = np.round(np.linspace(1, -1, 32) * 7) / 7
    t = np.arange(n) / sr
    phase = (t * freq * 32) % 32
    indices = phase.astype(int) % 32
    return (wave_table[indices] * amplitude).astype(np.float32)

def generate_gb_noise(duration, sr, amplitude=1.0):
    n = int(duration * sr)
    if n == 0:
        return np.zeros(n)
    lfsr = 0x7F
    out = np.zeros(n)
    period = max(1, int(sr / 440))
    for i in range(n):
        if i % period == 0:
            bit = ((lfsr >> 0) ^ (lfsr >> 1)) & 1
            lfsr = (lfsr >> 1) | (bit << 6)
        out[i] = amplitude if (lfsr & 1) == 0 else -amplitude
    return out.astype(np.float32)

def generate_snes_brr(freq, duration, sr, amplitude=1.0):
    n = int(duration * sr)
    if n == 0 or freq <= 0:
        return np.zeros(n)
    wave = generate_square(freq, duration, sr, duty=0.5, amplitude=amplitude)
    wave = np.round(wave * 8) / 8
    cutoff = min(freq * 3 / (sr / 2), 0.45)
    b, a = butter(2, cutoff, btype='low')
    wave = lfilter(b, a, wave).astype(np.float32)
    # ADSR
    attack_s, decay_s, sustain_l, release_s = 0.06, 0.10, 0.85, 0.09
    ai, di, ri = int(attack_s*sr), int(decay_s*sr), int(release_s*sr)
    env = np.ones(n)
    env[:min(ai,n)] = np.linspace(0, 1, min(ai,n))
    if ai < n:
        env[ai:min(ai+di,n)] = np.linspace(1, sustain_l, min(di, n-ai))
    if ai+di < n:
        env[ai+di:max(0,n-ri)] = sustain_l
    if n-ri > 0:
        env[max(0,n-ri):] = np.linspace(sustain_l, 0, n-max(0,n-ri))
    return (wave * env).astype(np.float32)

def apply_envelope(wave, attack_s, decay_s, sustain_level, release_s, sr):
    n = len(wave)
    env = np.zeros(n)
    ai = int(attack_s * sr)
    di = int(decay_s * sr)
    ri = int(release_s * sr)
    sustain_end = max(0, n - ri)
    if ai > 0:
        env[:min(ai,n)] = np.linspace(0, 1, min(ai,n))
    if di > 0 and ai < n:
        env[ai:min(ai+di,n)] = np.linspace(1, sustain_level, min(di,n-ai))
    if ai+di < n:
        env[min(ai+di,n):sustain_end] = sustain_level
    if ri > 0 and sustain_end < n:
        env[sustain_end:] = np.linspace(sustain_level, 0, n-sustain_end)
    return (wave * env).astype(np.float32)

def lowpass(signal, cutoff_hz, sr):
    cutoff = min(cutoff_hz / (sr / 2), 0.99)
    b, a = butter(2, cutoff, btype='low')
    return lfilter(b, a, signal).astype(np.float32)

def midi_to_notes(midi_path):
    try:
        import pretty_midi
    except ImportError:
        os.system("pip install pretty_midi -q")
        import pretty_midi
    pm = pretty_midi.PrettyMIDI(midi_path)
    notes = []
    for instrument in pm.instruments:
        for note in instrument.notes:
            notes.append({
                'note': note.pitch,
                'freq': midi_to_freq(note.pitch),
                'start': note.start,
                'end': note.end,
                'velocity': note.velocity,
                'is_drum': instrument.is_drum,
            })
    notes.sort(key=lambda x: x['start'])
    return notes, pm.get_end_time()

def assign_to_slots(notes, num_slots):
    slots = [[] for _ in range(num_slots)]
    busy_until = [0.0] * num_slots
    for note in sorted(notes, key=lambda x: x['start']):
        free = [i for i in range(num_slots) if note['start'] >= busy_until[i] - 0.005]
        idx = min(free, key=lambda i: busy_until[i]) if free else min(range(num_slots), key=lambda i: busy_until[i])
        slots[idx].append(note)
        busy_until[idx] = note['end']
    return slots

def assign_channels(notes, mode):
    drums   = [n for n in notes if n['is_drum']]
    pitched = [n for n in notes if not n['is_drum']]
    bass    = [n for n in pitched if n['note'] < 48]
    mid_hi  = sorted([n for n in pitched if n['note'] >= 48], key=lambda x: -x['velocity'])
    bass    = sorted(bass, key=lambda x: -x['velocity'])

    if mode == 'nes':
        sq = assign_to_slots(mid_hi, 2)
        tr = assign_to_slots(bass, 1)
        return {'SQ1': sq[0], 'SQ2': sq[1], 'TRI': tr[0], 'NOISE': drums}
    elif mode == 'gb':
        sq = assign_to_slots(mid_hi, 2)
        tr = assign_to_slots(bass, 1)
        return {'CH1': sq[0], 'CH2': sq[1], 'CH3': tr[0], 'CH4': drums}
    elif mode == 'snes':
        mel  = assign_to_slots(mid_hi, 6)
        bass_slots = assign_to_slots(bass + drums, 2)
        ch = {f'CH{i+1}': mel[i] for i in range(6)}
        ch['CH7'] = bass_slots[0]
        ch['CH8'] = bass_slots[1]
        return ch

def render_note(ch_name, note, mode, sr):
    dur = note['end'] - note['start']
    amp = (note['velocity'] / 127.0) * 0.8

    if mode == 'nes':
        if ch_name == 'SQ1':
            w = generate_square(note['freq'], dur, sr, duty=0.50, amplitude=amp)
            return apply_envelope(w, 0.005, 0.02, 0.7, 0.03, sr)
        elif ch_name == 'SQ2':
            w = generate_square(note['freq'], dur, sr, duty=0.25, amplitude=amp)
            return apply_envelope(w, 0.005, 0.02, 0.7, 0.03, sr)
        elif ch_name == 'TRI':
            return generate_triangle(note['freq'], dur, sr, amplitude=amp * 0.9)
        elif ch_name == 'NOISE':
            w = generate_nes_noise(dur, sr, amplitude=amp * 0.5)
            return apply_envelope(w, 0.001, 0.05, 0.0, 0.05, sr)

    elif mode == 'gb':
        if ch_name in ('CH1', 'CH2'):
            duty = 0.25 if ch_name == 'CH1' else 0.50
            w = generate_square(note['freq'], dur, sr, duty=duty, amplitude=amp)
            return apply_envelope(w, 0.003, 0.01, 0.75, 0.02, sr)
        elif ch_name == 'CH3':
            return generate_gb_wave(note['freq'], dur, sr, amplitude=amp * 0.85)
        elif ch_name == 'CH4':
            w = generate_gb_noise(dur, sr, amplitude=amp * 0.45)
            return apply_envelope(w, 0.001, 0.04, 0.0, 0.04, sr)

    elif mode == 'snes':
        if note.get('is_drum'):
            w = np.random.uniform(-amp, amp, int(dur * sr)).astype(np.float32)
            w = lowpass(w, 800, sr)
            return apply_envelope(w, 0.001, 0.06, 0.0, 0.05, sr)
        else:
            return generate_snes_brr(note['freq'], dur, sr, amplitude=amp)

    return np.zeros(int(dur * sr), dtype=np.float32)

def convert(audio_path, mode, output_path, progress_callback=None):
    import tempfile

    def cb(p):
        if progress_callback:
            progress_callback(p)

    cb(5)

    # Step1: basic-pitch でMIDI変換
    with tempfile.TemporaryDirectory() as tmpdir:
        from basic_pitch.inference import predict_and_save
        from basic_pitch import ICASSP_2022_MODEL_PATH

        predict_and_save(
            audio_path_list=[audio_path],
            output_directory=tmpdir,
            save_midi=True,
            sonify_midi=False,
            save_model_outputs=False,
            save_notes=False,
            model_or_model_path=ICASSP_2022_MODEL_PATH,
            minimum_note_length=0.058,
            minimum_frequency=32.7,
            maximum_frequency=2000.0,
            multiple_pitch_bends=False,
            melodia_trick=True,
        )
        cb(30)

        # MIDIファイルを探す
        midi_path = None
        for f in os.listdir(tmpdir):
            if f.endswith('.mid'):
                midi_path = os.path.join(tmpdir, f)
                break
        if not midi_path:
            raise RuntimeError("MIDI変換に失敗しました")

        # Step2: チャンネル割り当て
        notes, total_sec = midi_to_notes(midi_path)
        channels = assign_channels(notes, mode)
        cb(40)

        # Step3: 波形合成
        if mode == 'nes':
            ch_names = ['SQ1', 'SQ2', 'TRI', 'NOISE']
            vol_map  = {'SQ1': 0.45, 'SQ2': 0.40, 'TRI': 0.35, 'NOISE': 0.30}
        elif mode == 'gb':
            ch_names = ['CH1', 'CH2', 'CH3', 'CH4']
            vol_map  = {'CH1': 0.45, 'CH2': 0.40, 'CH3': 0.35, 'CH4': 0.30}
        elif mode == 'snes':
            ch_names = [f'CH{i+1}' for i in range(8)]
            vol_map  = {f'CH{i+1}': max(0.15, 0.4 - i*0.03) for i in range(8)}

        total_samples = int(total_sec * SAMPLE_RATE) + SAMPLE_RATE
        mix = np.zeros(total_samples, dtype=np.float32)

        for ci, ch in enumerate(ch_names):
            for note in channels.get(ch, []):
                start_i = int(note['start'] * SAMPLE_RATE)
                wave = render_note(ch, note, mode, SAMPLE_RATE)
                end_i = min(start_i + len(wave), total_samples)
                wave = wave[:end_i - start_i]
                # 前の音と少しだけ重ねるクロスフェード処理
                target_wave = wave * vol_map.get(ch, 0.3)
                overlap = int(0.002 * SAMPLE_RATE) # 2ミリ秒だけ重ねる
                
                # 最初の方のサンプルを滑らかに足す
                if start_i > 0:
                    mix[start_i:start_i+overlap] += target_wave[:overlap] * np.linspace(0, 1, overlap)
                    mix[start_i+overlap:end_i] += target_wave[overlap:]
                else:
                    mix[start_i:end_i] += target_wave
            cb(40 + int(50 * (ci + 1) / len(ch_names)))

        if mode == 'snes':
            delay = int(0.06 * SAMPLE_RATE)
            if delay < len(mix):
                mix[delay:] += mix[:-delay] * 0.35
            mix = lowpass(mix, 16000, SAMPLE_RATE)
        elif mode == 'gb':
            mix = lowpass(mix, 8000, SAMPLE_RATE)

        # マスタリング
        peak = np.max(np.abs(mix))
        if peak > 1e-6:
            mix = mix * (0.9 / peak)
        mix = np.tanh(mix * 1.1) * 0.9

        out_int = (mix * 32767).astype(np.int16)
        wavfile.write(output_path, SAMPLE_RATE, out_int)
        cb(100)
