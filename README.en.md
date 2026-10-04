# fractal-speech

🇺🇸 English | [🇧🇷 Português](README.md)

Generates English voiceover from a plain-text script using [Kokoro TTS](https://huggingface.co/hexgrad/Kokoro-82M). Runs on CPU and works offline after the first model download (~330 MB). Kokoro is licensed under Apache 2.0.

## Installation

Requires Python 3.10 to 3.12 and `ffmpeg`. On Linux/macOS, also install `espeak-ng`.

```bash
# Ubuntu/Debian
sudo apt install ffmpeg espeak-ng
# macOS
brew install ffmpeg espeak-ng
# Windows
winget install Gyan.FFmpeg
```

Create a virtual environment and install PyTorch **before** the other dependencies (the CPU build avoids DLL problems on Windows):

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

On the first run, Kokoro downloads the model (~330 MB).

## Usage

```bash
python narrate.py example_script.txt                 # creates example_script.mp3 + .srt
python narrate.py script.txt -o narration.mp3 --voice am_adam --speed 0.95
python narrate.py script.txt --compare-voices        # voice samples in samples/
python narrate.py script.txt --profile other_profile.json   # use another voice profile
python narrate.py --list-voices
```

Output: audio normalized to -16 LUFS (the YouTube standard) and an `.srt` file with the timing of each sentence, useful for captions and for placing the narration in your editor.

## Options

| Option | Description | Default |
|---|---|---|
| `-o`, `--output` | output file (`.mp3` or `.wav`) | `<script>.mp3` |
| `--profile` | voice profile (JSON) | `voice_profile.json` |
| `--voice` | Kokoro voice (see `--list-voices`) | from profile (`am_adam`) |
| `--speed` | speech speed (0.8 = slower, 1.2 = faster) | from profile (`0.95`) |
| `--sentence-pause` | seconds of pause between sentences | from profile (`0.35`) |
| `--paragraph-pause` | seconds of pause between paragraphs | from profile (`0.9`) |
| `--dictionary` | pronunciation JSON file | `pronunciations.json` |
| `--no-normalize` | skip loudness normalization (-16 LUFS) | |
| `--no-srt` | do not write the `.srt` subtitle file | |
| `--compare-voices` | render a sample with several voices | |
| `--list-voices` | list the available voices | |

Voice and pause options, when given, override the profile.

## Script format

- Blank line between paragraphs: longer pause (`--paragraph-pause`)
- `[beat]`: short pause before a key concept (length set by `beat_pause` in `voice_profile.json`)
- `[pause 2]`: 2 seconds of silence
- Lines starting with `#`: comments, not read aloud (use them for scene notes)
- List items (`- text`) become separate sentences

## Voice profile

The HyperMechane voice standard lives in `voice_profile.json`: voice, speed, pauses (`sentence_pause`, `paragraph_pause`, `beat_pause`) and the target words-per-minute range (`target_wpm`). `narrate.py` loads it by default; command-line flags override the profile and `--profile` points to another file. For published videos, keep the profile untouched so the voice stays the same every time.

After each render the script prints the pace, for example `Pace: 150 words/min (target 145-155) - OK`. If it is outside the range, adjust `speed` in the profile. The full standard is in [VOICE_BIBLE.md](VOICE_BIBLE.md).

## Pronouncing technical terms

Edit `pronunciations.json` (key = how it appears in the script, value = how it should be read). Add your brand name and any term that comes out wrong. Numbers, years, versions (`2.4.1`), `%` and `$` are converted to words automatically.

For exact control, a value can use Kokoro's phoneme syntax, e.g. `"[HyperMechane](/ˌhaɪpɚmɛkəˈni/)"`.

## Quality tips

- Short sentences and clear punctuation improve intonation.
- If a sentence sounds off, rewrite it or split it with commas.
- A speed between 0.9 and 1.0 usually sounds more natural for explainer videos.

## License

MIT. Kokoro and its voices are distributed under their own license (Apache 2.0).
