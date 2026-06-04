import argparse

from streaming_tts import LocalVitsTTS


def main() -> None:
    parser = argparse.ArgumentParser(description="Test local sherpa-onnx VITS TTS")
    parser.add_argument("text", nargs="?", default="我已做好陪伴您入睡的准备了，祝您做个好梦！")
    parser.add_argument("--output", default="tts_test.wav")
    parser.add_argument("--play", action="store_true")
    args = parser.parse_args()

    tts = LocalVitsTTS()
    tts.synthesize(args.text, args.output)
    print(f"Saved local TTS audio to: {args.output}")
    if args.play:
        tts.play(args.output)


if __name__ == "__main__":
    main()
