import argparse
import json
import numpy as np
import librosa

def analyze(path):
    y, sr = librosa.load(path, sr=22050, mono=True)
    if not len(y):
        raise ValueError("Empty audio")
    hop = 256
    f0, voiced, probability = librosa.pyin(y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C6"), sr=sr, hop_length=hop)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    times = librosa.frames_to_time(np.arange(len(f0)), sr=sr, hop_length=hop)
    frames = [{"time": float(t), "hz": float(f), "confidence": float(p)} for t,f,p in zip(times,f0,probability) if np.isfinite(f) and np.isfinite(p)]
    return {"duration": len(y)/sr, "bpm": float(np.asarray(tempo).reshape(-1)[0]), "beats": librosa.frames_to_time(beats,sr=sr).tolist(), "pitch": frames, "peak": float(np.max(np.abs(y))), "rms": float(np.sqrt(np.mean(y*y)))}

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("audio")
    a = p.parse_args()
    print(json.dumps(analyze(a.audio), allow_nan=False))
