"""Local six-stem separation. Audio stays on the workstation."""
import argparse
import subprocess
import sys
from pathlib import Path

def separate(source: Path, output: Path):
    if not source.is_file():
        raise FileNotFoundError(source)
    output.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-m", "demucs", "-n", "htdemucs_6s", "-o", str(output), str(source.resolve())], check=True)
    folder = output / "htdemucs_6s" / source.stem
    expected = ["vocals", "drums", "bass", "guitar", "piano", "other"]
    for name in expected:
        if not (folder / (name + ".wav")).is_file():
            raise RuntimeError("Missing stem: " + name)
    return folder

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path)
    p.add_argument("--output", type=Path, default=Path("stems"))
    a = p.parse_args()
    print(separate(a.source, a.output))
