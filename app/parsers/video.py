"""Video-Dateien verarbeiten - Frames extrahieren und analysieren."""

from pathlib import Path
import subprocess
import json


def parse_video(file_path: Path) -> list[dict]:
    """Video-Metadaten und Keyframes extrahieren."""
    results = []

    # Metadaten mit ffprobe
    meta = _get_metadata(file_path)
    if meta:
        results.append({
            "text": _format_metadata(meta),
            "content_type": "text",
            "section": "Video-Metadaten",
            "metadata": meta,
        })

    # Keyframes extrahieren fuer spaetere Bildanalyse
    frames = extract_keyframes(file_path)
    if frames:
        results.append({
            "text": f"[{len(frames)} Keyframes extrahiert fuer Analyse]",
            "content_type": "image_ref",
            "section": "Keyframes",
            "frame_paths": [str(f) for f in frames],
        })

    if not results:
        results.append({
            "text": f"[Video: {file_path.name} - ffprobe nicht verfuegbar]",
            "content_type": "text",
        })

    return results


def _get_metadata(file_path: Path) -> dict:
    """Video-Metadaten mit ffprobe auslesen."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", str(file_path)],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return {}


def _format_metadata(meta: dict) -> str:
    """Metadaten leserlich formatieren."""
    lines = []
    fmt = meta.get("format", {})

    if "duration" in fmt:
        secs = float(fmt["duration"])
        mins, secs = divmod(int(secs), 60)
        hours, mins = divmod(mins, 60)
        lines.append(f"Dauer: {hours:02d}:{mins:02d}:{secs:02d}")

    if "size" in fmt:
        size_mb = int(fmt["size"]) / (1024 * 1024)
        lines.append(f"Groesse: {size_mb:.1f} MB")

    if "format_long_name" in fmt:
        lines.append(f"Format: {fmt['format_long_name']}")

    for stream in meta.get("streams", []):
        codec_type = stream.get("codec_type", "")
        if codec_type == "video":
            w = stream.get("width", "?")
            h = stream.get("height", "?")
            fps = stream.get("r_frame_rate", "?")
            lines.append(f"Video: {w}x{h}, {fps} fps, {stream.get('codec_name', '?')}")
        elif codec_type == "audio":
            lines.append(f"Audio: {stream.get('codec_name', '?')}, "
                         f"{stream.get('sample_rate', '?')} Hz")

    return "\n".join(lines) if lines else "Keine Metadaten"


def extract_keyframes(file_path: Path, max_frames: int = 10) -> list[Path]:
    """Keyframes aus Video extrahieren."""
    output_dir = file_path.parent / f".frames_{file_path.stem}"
    output_dir.mkdir(exist_ok=True)

    try:
        # Gleichmaessig verteilte Frames extrahieren
        meta = _get_metadata(file_path)
        duration = float(meta.get("format", {}).get("duration", 60))
        interval = max(duration / max_frames, 1)

        subprocess.run(
            ["ffmpeg", "-i", str(file_path), "-vf",
             f"fps=1/{interval}", "-frames:v", str(max_frames),
             "-q:v", "2", str(output_dir / "frame_%03d.jpg")],
            capture_output=True, timeout=120
        )

        return sorted(output_dir.glob("frame_*.jpg"))
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
