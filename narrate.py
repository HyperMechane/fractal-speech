#!/usr/bin/env python3
"""
narrate.py - English voiceover from a plain-text script (Kokoro TTS).

Examples:
    python narrate.py script.txt
    python narrate.py script.txt -o narration.mp3 --voice am_adam --speed 0.95
    python narrate.py script.txt --compare-voices
    python narrate.py --list-voices

Script conventions:
    - Blank line            -> longer pause between paragraphs
    - [pause 2]             -> 2 seconds of silence
    - Line starting with #  -> comment (not read aloud; use for scene notes)
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
import soundfile as sf

SAMPLE_RATE = 24000  # Kokoro's native sample rate
HERE = Path(__file__).resolve().parent

VOICES = {
    "af_heart": "American, female (default, most natural)",
    "af_bella": "American, female",
    "af_nicole": "American, female, soft",
    "af_sarah": "American, female",
    "am_adam": "American, male",
    "am_michael": "American, male",
    "am_fenrir": "American, male, deep",
    "bf_emma": "British, female",
    "bm_george": "British, male",
    "bm_lewis": "British, male",
}

# "[pause 2]" (the Portuguese "[pausa 2]" is also accepted)
PAUSE_RE = re.compile(r"^\[\s*(?:pause|pausa)\s+(\d+(?:\.\d+)?)\s*s?\s*\]$", re.I)


# --------------------------------------------------------------------------
# Text preprocessing
# --------------------------------------------------------------------------
def load_dictionary(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def apply_dictionary(text: str, dictionary: dict[str, str]) -> str:
    # longest keys first ("APIs" before "API")
    for key in sorted(dictionary, key=len, reverse=True):
        pattern = r"(?<!\w)" + re.escape(key) + r"(?!\w)"
        value = dictionary[key]
        text = re.sub(pattern, lambda _m, v=value: v, text)
    return text


def numbers_to_words(text: str) -> str:
    try:
        from num2words import num2words
    except ImportError:
        return text

    def dollars(m: re.Match) -> str:
        whole = m.group(1).replace(",", "")
        cents = m.group(2)
        out = f"{num2words(int(whole))} dollar" + ("" if whole == "1" else "s")
        if cents and int(cents[:2].ljust(2, "0")) > 0:
            c = int(cents[:2].ljust(2, "0"))
            out += f" and {num2words(c)} cent" + ("" if c == 1 else "s")
        return out

    def version(m: re.Match) -> str:
        return " dot ".join(num2words(int(part)) for part in m.group(0).split("."))

    def number(m: re.Match) -> str:
        raw = m.group(0).replace(",", "")
        if "." in raw:
            return num2words(float(raw))
        n = int(raw)
        if "," not in m.group(0) and len(raw) == 4 and 1900 <= n <= 2099:
            return num2words(n, to="year")
        return num2words(n)

    text = re.sub(r"\$(\d[\d,]*)(?:\.(\d+))?", dollars, text)
    text = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"\1 percent", text)
    text = re.sub(r"(?<![\w.])\d+(?:\.\d+){2,}(?![\w.])", version, text)
    text = re.sub(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w])", number, text)
    return text


def strip_markdown(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # [link](url) -> link
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)   # **bold**
    text = text.replace("`", "")
    text = re.sub(r"^\s*[-•]\s+", "", text)                # list bullets
    return text


def prepare_text(text: str, dictionary: dict[str, str]) -> str:
    text = strip_markdown(text)
    text = apply_dictionary(text, dictionary)
    text = numbers_to_words(text)
    text = text.replace("&", " and ").replace("→", " to ")
    text = re.sub(r"\s*[—–]\s*", ", ", text)
    text = re.sub(r"(?<=\w)/(?=\w)", " slash ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if text and not re.search(r"[.!?…:;][\"”')]?$", text):
        text += "."
    return text


def split_sentences(paragraph: str) -> list[str]:
    parts = re.split(r"(?<=[.!?…])\s+(?=[\"'“(\[]?[A-Z0-9])", paragraph)
    return [p.strip() for p in parts if re.search(r"\w", p)]


def parse_script(text: str, dictionary: dict[str, str]) -> list[tuple]:
    """Returns items: ("sentence", text, last_in_paragraph) or ("pause", seconds)."""
    items: list[tuple] = []
    paragraph: list[str] = []

    def flush() -> None:
        if not paragraph:
            return
        raw = " ".join(paragraph)
        paragraph.clear()
        sentences = split_sentences(prepare_text(raw, dictionary))
        for i, sentence in enumerate(sentences):
            items.append(("sentence", sentence, i == len(sentences) - 1))

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#"):
            continue
        if not line:
            flush()
            continue
        m = PAUSE_RE.match(line)
        if m:
            flush()
            items.append(("pause", float(m.group(1))))
            continue
        if re.match(r"^[-•]\s+", line):  # list item = its own sentence
            flush()
            paragraph.append(re.sub(r"^[-•]\s+", "", line))
            flush()
            continue
        paragraph.append(line)
    flush()
    return items


# --------------------------------------------------------------------------
# Synthesis
# --------------------------------------------------------------------------
_pipelines: dict = {}


def get_pipeline(lang: str):
    """Creates (and caches) the Kokoro pipeline. 'a' = American, 'b' = British."""
    if lang not in _pipelines:
        try:
            from kokoro import KPipeline
        except ImportError:
            sys.exit("Kokoro is not installed. Run: pip install -r requirements.txt")
        _pipelines[lang] = KPipeline(lang_code=lang, repo_id="hexgrad/Kokoro-82M")
    return _pipelines[lang]


def synthesize(pipeline, text: str, voice: str, speed: float) -> np.ndarray:
    chunks = []
    for _, _, audio in pipeline(text, voice=voice, speed=speed):
        if audio is None:
            continue
        a = audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio)
        chunks.append(a.astype(np.float32).reshape(-1))
    return np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)


def silence(seconds: float) -> np.ndarray:
    return np.zeros(int(seconds * SAMPLE_RATE), dtype=np.float32)


def build_audio(items, voice, speed, sentence_pause, paragraph_pause):
    pipeline = get_pipeline(voice[0])
    total = sum(1 for i in items if i[0] == "sentence")
    parts: list[np.ndarray] = []
    captions: list[tuple[float, float, str]] = []
    cursor = 0
    n = 0

    def add(a: np.ndarray) -> None:
        nonlocal cursor
        parts.append(a)
        cursor += len(a)

    for item in items:
        if item[0] == "pause":
            add(silence(item[1]))
            continue
        _, text, last = item
        n += 1
        print(f"  [{n}/{total}] {text[:70]}")
        audio = synthesize(pipeline, text, voice, speed)
        start = cursor / SAMPLE_RATE
        add(audio)
        captions.append((start, cursor / SAMPLE_RATE, text))
        add(silence(paragraph_pause if last else sentence_pause))

    if not parts:
        sys.exit("The script is empty.")
    return np.concatenate(parts), captions


# --------------------------------------------------------------------------
# Output (audio, normalization, SRT)
# --------------------------------------------------------------------------
def _srt_time(s: float) -> str:
    ms = int(round(s * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    sec, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def write_srt(captions, path: Path) -> None:
    blocks = []
    for i, (start, end, text) in enumerate(captions, 1):
        lines = "\n".join(textwrap.wrap(text, 42)[:4])
        blocks.append(f"{i}\n{_srt_time(start)} --> {_srt_time(end)}\n{lines}\n")
    path.write_text("\n".join(blocks), encoding="utf-8")


def save_audio(audio: np.ndarray, output: Path, normalize: bool) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_name(output.stem + ".tmp.wav")
    sf.write(tmp, audio, SAMPLE_RATE)

    ext = output.suffix.lower()
    if not shutil.which("ffmpeg"):
        if ext != ".wav":
            tmp.unlink(missing_ok=True)
            sys.exit("ffmpeg not found: install it or use a .wav output file")
        tmp.replace(output)
        print("Warning: ffmpeg not found, so the audio was not loudness-normalized.")
        return

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp)]
    if normalize:
        cmd += ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"]  # YouTube loudness target
    cmd += ["-ar", "48000"]
    if ext == ".mp3":
        cmd += ["-codec:a", "libmp3lame", "-q:a", "2"]
    cmd.append(str(output))
    try:
        subprocess.run(cmd, check=True)
    finally:
        tmp.unlink(missing_ok=True)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def compare_voices(items, args) -> None:
    sample = [i for i in items if i[0] == "sentence"][:2]
    if not sample:
        sample = [("sentence", "Welcome to the channel. Today we are building something new.", True)]
    folder = Path("samples")
    folder.mkdir(exist_ok=True)
    for voice in ["af_heart", "af_bella", "am_adam", "am_michael", "bf_emma", "bm_george"]:
        print(f"Voice: {voice}")
        audio, _ = build_audio(sample, voice, args.speed, args.sentence_pause, args.paragraph_pause)
        save_audio(audio, folder / f"{voice}.mp3", normalize=True)
    print(f"\nSamples saved in {folder}/ - listen and pick one with --voice.")


def main() -> None:
    p = argparse.ArgumentParser(description="English voiceover from a text script (Kokoro TTS).")
    p.add_argument("script", nargs="?", help="text file with the script")
    p.add_argument("-o", "--output", default=None, help="output file (.mp3 or .wav); default: <script>.mp3")
    p.add_argument("--voice", default="af_heart", help="Kokoro voice (see --list-voices)")
    p.add_argument("--speed", type=float, default=1.0, help="0.8 = slower, 1.2 = faster")
    p.add_argument("--sentence-pause", type=float, default=0.30, help="seconds between sentences")
    p.add_argument("--paragraph-pause", type=float, default=0.80, help="seconds between paragraphs")
    p.add_argument("--dictionary", default=str(HERE / "pronunciations.json"), help="pronunciation JSON file")
    p.add_argument("--no-normalize", action="store_true", help="skip loudness normalization (-16 LUFS)")
    p.add_argument("--no-srt", action="store_true", help="do not write the .srt subtitle file")
    p.add_argument("--compare-voices", action="store_true", help="render a sample with several voices")
    p.add_argument("--list-voices", action="store_true", help="list the available voices")
    args = p.parse_args()

    if args.list_voices:
        for name, description in VOICES.items():
            print(f"{name:12} {description}")
        return
    if not args.script:
        p.error("please provide the script file")
    script_path = Path(args.script)
    if not script_path.exists():
        sys.exit(f"File not found: {script_path}")
    if args.voice[0] not in ("a", "b"):
        sys.exit("Invalid voice. See --list-voices (English Kokoro voices start with a or b).")

    dictionary = load_dictionary(Path(args.dictionary))
    items = parse_script(script_path.read_text(encoding="utf-8"), dictionary)

    if args.compare_voices:
        compare_voices(items, args)
        return

    output = Path(args.output) if args.output else script_path.with_suffix(".mp3")
    print(f"Generating narration with voice {args.voice}...")
    audio, captions = build_audio(items, args.voice, args.speed, args.sentence_pause, args.paragraph_pause)
    save_audio(audio, output, normalize=not args.no_normalize)
    if not args.no_srt:
        write_srt(captions, output.with_suffix(".srt"))
    print(f"\nDone: {output} ({len(audio) / SAMPLE_RATE:.1f}s)")


if __name__ == "__main__":
    main()
