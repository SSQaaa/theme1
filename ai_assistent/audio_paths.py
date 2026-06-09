from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
WAV_DIR = BASE_DIR / "WAV"


def wav_path(name: str, prefer_vits: bool = True) -> Path:
    """Return a path inside WAV/, preferring a generated *_VITS.wav variant."""
    WAV_DIR.mkdir(parents=True, exist_ok=True)

    path = Path(name)
    if path.is_absolute():
        return path

    if path.parent != Path("."):
        candidate = BASE_DIR / path
    else:
        candidate = WAV_DIR / path.name

    if prefer_vits and candidate.suffix.lower() == ".wav" and not candidate.stem.endswith("_VITS"):
        vits_candidate = candidate.with_name(f"{candidate.stem}_VITS.wav")
        if vits_candidate.is_file():
            return vits_candidate

    return candidate
