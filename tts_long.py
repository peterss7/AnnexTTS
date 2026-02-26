import argparse
import re
import shutil
from pathlib import Path

from gtts import gTTS
from pydub import AudioSegment


def chunk_text(text: str, max_chars: int = 3500):
    # gTTS has practical limits; keep chunks conservative.
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return

    sentences = re.split(r"(?<=[.!?])\s+", text)

    chunk = []
    chunk_len = 0

    for s in sentences:
        if not s:
            continue

        if len(s) > max_chars:
            if chunk:
                yield " ".join(chunk)
                chunk, chunk_len = [], 0
            for i in range(0, len(s), max_chars):
                yield s[i : i + max_chars]
            continue

        if chunk_len + len(s) + 1 <= max_chars:
            chunk.append(s)
            chunk_len += len(s) + 1
        else:
            yield " ".join(chunk)
            chunk = [s]
            chunk_len = len(s) + 1

    if chunk:
        yield " ".join(chunk)


def main():
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg not found on PATH. Install/add C:\\ffmpeg\\bin to PATH.")

    parser = argparse.ArgumentParser(description="Long text file to MP3 using gTTS (internet).")
    parser.add_argument("input", help="Path to input .txt file")
    parser.add_argument("--out", default="output.mp3", help="Output MP3 path")
    parser.add_argument("--lang", default="en", help="Language code (default: en)")
    parser.add_argument("--chunk-chars", type=int, default=3500, help="Max chars per chunk")
    parser.add_argument("--tmpdir", default="tts_chunks", help="Temp directory for chunk mp3s")
    args = parser.parse_args()

    in_path = Path(args.input)
    text = in_path.read_text(encoding="utf-8", errors="replace")

    tmpdir = Path(args.tmpdir)
    tmpdir.mkdir(parents=True, exist_ok=True)

    chunk_files = []
    for i, chunk in enumerate(chunk_text(text, max_chars=args.chunk_chars), start=1):
        print(f"Generating chunk {i} ({len(chunk)} chars)")
        tts = gTTS(chunk, lang=args.lang)
        chunk_path = tmpdir / f"chunk_{i:05d}.mp3"
        tts.save(str(chunk_path))
        chunk_files.append(chunk_path)

    print("Concatenating chunks...")
    combined = AudioSegment.empty()
    for p in chunk_files:
        combined += AudioSegment.from_mp3(p)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    combined.export(out_path, format="mp3")
    print(f"Done: {out_path}")


if __name__ == "__main__":
    main()