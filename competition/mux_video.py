"""Probe real narration lengths, then join captured browser footage with narration."""
import argparse
import json
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1] / "output/competition"
parser = argparse.ArgumentParser()
parser.add_argument("action", choices=["prepare", "mux"])
parser.add_argument("--recording", type=Path)
args = parser.parse_args()
if args.action == "prepare":
    chunks = [ROOT / "audio" / f"part-{i}.wav" for i in range(1, 9)]
    durations = []
    all_frames = []
    params = None
    for path in chunks:
        with wave.open(str(path), "rb") as stream:
            current = (stream.getnchannels(), stream.getsampwidth(), stream.getframerate())
            if params is not None and params != current:
                raise ValueError("voice format changed")
            params = current
            # A short silence after each segment matches the browser timing slots.
            frames = stream.readframes(stream.getnframes())
            silence_frames = round(stream.getframerate() * 0.5)
            all_frames.append(frames + bytes(silence_frames * stream.getnchannels() * stream.getsampwidth()))
            durations.append(stream.getnframes()/stream.getframerate()+0.5)
    assert params
    assert 180 <= sum(durations) <= 300, f"video duration outside submission range: {sum(durations)}"
    with wave.open(str(ROOT / "audio/narration.wav"), "wb") as stream:
        stream.setnchannels(params[0]); stream.setsampwidth(params[1]); stream.setframerate(params[2])
        stream.writeframes(b"".join(all_frames))
    (ROOT / "audio/durations.json").write_text(json.dumps(durations), encoding="utf-8")
    print(json.dumps({"seconds":sum(durations),"segments":durations}))
else:
    assert args.recording and args.recording.exists()
    target=ROOT / "机图索隐_真实系统演示.mp4"
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", str(args.recording), "-i", str(ROOT / "audio/narration.wav"), "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(target)], check=True, capture_output=True)
    assert target.stat().st_size <= 300*1024*1024
    print(json.dumps({"path":str(target),"bytes":target.stat().st_size},ensure_ascii=False))
