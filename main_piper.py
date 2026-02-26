import argparse
import re
import shutil
import subprocess
from pathlib import Path

from pydub import AudioSegment

PIPER_EXE = r"C:\piper\piper.exe"
MODEL = r"C:\piper\voices\en_US-libritts-high.onnx"


def chunk_text(text: str, max_chars: int = 1200):
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return
    sentences = re.split(r"(?<=[.!?])\s+", text)

    buf, n = [], 0
    for s in sentences:
        if not s:
            continue
        if n + len(s) + 1 > max_chars and buf:
            yield " ".join(buf)
            buf, n = [], 0
        buf.append(s)
        n += len(s) + 1
    if buf:
        yield " ".join(buf)

def delete_chunks_folder(path="piper_chunks"):
    p = Path(path)
    if p.exists() and p.is_dir():
        shutil.rmtree(p)
        print(f"Deleted chunks folder: {p.resolve()}")
    else:
        print(f"No chunks folder found at: {p.resolve()}")


def main():
    parser = argparse.ArgumentParser(description="Long text to WAV using Piper (offline).")
    parser.add_argument("input", help="Input .txt")
    parser.add_argument("--out", default="output.wav", help="Output wav")
    parser.add_argument("--chunk-chars", type=int, default=1200)
    parser.add_argument("--tmpdir", default="piper_chunks")
    parser.add_argument("--delete-chunks", action="store_true")
    args = parser.parse_args()

    # optional: ensure ffmpeg exists for pydub merge (recommended)
    # if not shutil.which("ffmpeg"):
    #     raise SystemExit("ffmpeg not found on PATH (needed for pydub).")

    text = Path(args.input).read_text(encoding="utf-8", errors="replace")

    tmpdir = Path(args.tmpdir)
    tmpdir.mkdir(parents=True, exist_ok=True)

    chunk_files = []
    for i, chunk in enumerate(chunk_text(text, args.chunk_chars), start=1):
        chunk_path = tmpdir / f"chunk_{i:05d}.wav"

        # resume-safe: don't regenerate existing chunks
        if chunk_path.exists():
            chunk_files.append(chunk_path)
            continue

        subprocess.run(
            [PIPER_EXE, "--model", MODEL, "--output_file", str(chunk_path)],
            input=chunk,
            text=True,
            check=True,
        )
        chunk_files.append(chunk_path)
        print(f"Generated {chunk_path.name}")

    combined = AudioSegment.empty()
    for p in chunk_files:
        combined += AudioSegment.from_wav(p)

    out_path = Path(args.out)
    combined.export(out_path, format="wav")
    print(f"Done: {out_path}")

    if args.delete_chunks:
        delete_chunks_folder(args.tmpdir)


if __name__ == "__main__":
    main()