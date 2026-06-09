from audio_paths import WAV_DIR
from Sherpa_onnx_stt import SpeechToText
from streaming_tts import LocalVitsTTS


SUFFIX = "_VITS"


def main() -> None:
    WAV_DIR.mkdir(parents=True, exist_ok=True)
    sources = [
        path
        for path in sorted(WAV_DIR.glob("*.wav"))
        if not path.stem.endswith(SUFFIX)
    ]

    if not sources:
        print("No WAV files found.")
        return

    print("Loading STT model...")
    stt = SpeechToText()
    print("Loading VITS model...")
    tts = LocalVitsTTS()

    for source in sources:
        target = source.with_name(f"{source.stem}{SUFFIX}.wav")
        if target.exists():
            print(f"SKIP {target.name}")
            continue

        print(f"Converting {source.name} -> {target.name}")
        text = stt.transcribe_file(str(source)).strip()
        if not text:
            print(f"SKIP empty text: {source.name}")
            continue

        print(f"TEXT: {text}")
        tts.synthesize(text, str(target))

    print("Done.")


if __name__ == "__main__":
    main()
