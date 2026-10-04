# fractal-speech

[🇺🇸 English](README.en.md) | 🇧🇷 Português

Gera narração em inglês a partir de um roteiro em texto. Roda em CPU, offline depois do primeiro download do modelo (~330 MB). Licença do Kokoro: Apache 2.0.

## Instalação

Requer Python 3.10 a 3.12 e `ffmpeg`. No Linux/macOS, instale também o `espeak-ng`.

```bash
# Ubuntu/Debian
sudo apt install ffmpeg espeak-ng
# macOS
brew install ffmpeg espeak-ng
# Windows
winget install Gyan.FFmpeg
```

Crie o ambiente virtual e instale o PyTorch **antes** das demais dependências (a versão CPU evita problemas de DLL no Windows):

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

Na primeira execução o Kokoro baixa o modelo (~330 MB).

## Uso

```bash
python narrate.py example_script.txt                 # gera example_script.mp3 + .srt
python narrate.py script.txt -o narration.mp3 --voice am_adam --speed 0.95
python narrate.py script.txt --compare-voices        # amostras em samples/
python narrate.py script.txt --profile outro_perfil.json   # usa outro perfil de voz
python narrate.py --list-voices
```

Saída: áudio normalizado em -16 LUFS (padrão do YouTube) e um `.srt` com o tempo de cada frase, útil para legendas e para posicionar a narração na edição.

## Opções

| Opção | Descrição | Padrão |
|---|---|---|
| `-o`, `--output` | arquivo de saída (`.mp3` ou `.wav`) | `<roteiro>.mp3` |
| `--profile` | perfil de voz (JSON) | `voice_profile.json` |
| `--voice` | voz do Kokoro (veja `--list-voices`) | do perfil (`am_adam`) |
| `--speed` | velocidade da fala (0.8 = mais lenta, 1.2 = mais rápida) | do perfil (`0.95`) |
| `--sentence-pause` | segundos de pausa entre frases | do perfil (`0.35`) |
| `--paragraph-pause` | segundos de pausa entre parágrafos | do perfil (`0.9`) |
| `--dictionary` | arquivo JSON de pronúncias | `pronunciations.json` |
| `--no-normalize` | não normalizar o volume (-16 LUFS) | |
| `--no-srt` | não gerar o arquivo de legendas `.srt` | |
| `--compare-voices` | gera amostras de várias vozes | |
| `--list-voices` | lista as vozes disponíveis | |

Os parâmetros de voz e pausas, quando informados, sobrescrevem o perfil.

## Formato do roteiro

- Parágrafo em branco: pausa maior (`--paragraph-pause`)
- `[beat]`: pausa curta antes de um conceito-chave (duração em `beat_pause`, no `voice_profile.json`)
- `[pause 2]` (ou `[pausa 2]`): silêncio de 2 segundos
- Linha começando com `#`: comentário, não é lida (use para notas de cena)
- Itens de lista (`- texto`) viram frases separadas

## Perfil de voz

O padrão de voz da HyperMechane fica em `voice_profile.json`: voz, velocidade, pausas (`sentence_pause`, `paragraph_pause`, `beat_pause`) e a faixa-alvo de palavras por minuto (`target_wpm`). O `narrate.py` lê esse arquivo por padrão; os parâmetros da linha de comando sobrescrevem o perfil e `--profile` aponta para outro arquivo. Para vídeos publicados, mantenha o perfil sem sobrescrever, para a voz ser sempre a mesma.

Ao final de cada narração o script mostra o ritmo, por exemplo `Pace: 150 words/min (target 145-155) - OK`. Se estiver fora da faixa, ajuste `speed` no perfil. O padrão completo está em [VOICE_BIBLE.md](VOICE_BIBLE.md).

## Pronúncia de termos técnicos

Edite `pronunciations.json` (chave = como está no roteiro, valor = como deve ser lido). Adicione o nome da sua marca e qualquer termo que saia errado. Números, anos, versões (`2.4.1`), `%` e `$` são convertidos para palavras automaticamente.

## Dicas de qualidade

- Frases curtas e pontuação clara melhoram a entonação.
- Se uma frase sair estranha, reescreva-a ou separe com vírgulas.
- Velocidade entre 0.9 e 1.0 costuma soar mais natural em vídeo explicativo.

## Licença

MIT. O Kokoro e suas vozes são distribuídos sob a licença própria (Apache 2.0).
