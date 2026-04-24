from __future__ import annotations

import argparse
import asyncio
import math
import re
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import edge_tts
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "assets" / "generated"

VIDEO_SIZE = (1280, 720)
PHOTO_AREA_HEIGHT = 590
FPS = 30
VOICE = "es-AR-TomasNeural"
VOICE_RATE = "-14%"
VOICE_PITCH = "+0Hz"
PAUSE_BETWEEN_BLOCKS = 0.35
TAIL_PAD_SECONDS = 0.25

VIDEO_CONFIGS = {
    "video1": {
        "slug": "video-obi-cinturones",
        "source_dir": ROOT / "assets" / "video 1",
        "blocks": [
            {
                "spoken_text": "¿Fabricás cinturones? Agregale un cinturón con la misma tela de la prenda, que completa y diferencia la prenda, otorgándole mayor calidad.",
                "subtitle_text": "¿Fabricás cinturones? Agregale un cinturón con la misma tela de la prenda, que completa y diferencia la prenda, otorgándole mayor calidad.",
                "images": ["1.jpeg", "2.jpeg"],
            },
            {
                "spoken_text": "Cinturón bien armado, con hebilla forrada y pase metálica. Los clientes que lo han incorporado lo repiten permanentemente, señal de que el producto funciona y vende.",
                "subtitle_text": "Cinturón bien armado, con hebilla forrada y pase metálica. Los clientes que lo han incorporado lo repiten permanentemente, señal de que el producto funciona y vende.",
                "images": ["3.jpeg", "4.jpeg", "5.jpeg"],
            },
            {
                "spoken_text": "También botones forrados en la tela de la prenda, en todos los tamaños.",
                "subtitle_text": "También botones forrados en la tela de la prenda, en todos los tamaños.",
                "images": ["6.jpeg", "7.jpeg", "8..jpeg"],
            },
            {
                "spoken_text": "Hebillas forradas en todos los pases: veinte, treinta, cuarenta, cincuenta y sesenta milímetros.",
                "subtitle_text": "Hebillas forradas en todos los pases: 20, 30, 40, 50 y 60 mm.",
                "images": ["9.jpeg", "10.jpeg", "11.jpeg", "12.jpeg", "13.jpeg"],
            },
            {
                "spoken_text": "Cinturones en pu, ideal para incorporar y a un valor muy competitivo.",
                "subtitle_text": "Cinturones en PU, ideal para incorporar y a un valor muy competitivo.",
                "images": ["14.jpeg"],
            },
        ],
    },
    "video2": {
        "slug": "video-obi-detalles",
        "source_dir": ROOT / "assets" / "fotos 2",
        "blocks": [
            {
                "spoken_text": "Alamares y trabas.",
                "subtitle_text": "ALAMARES Y TRABAS",
                "images": ["1.jpeg", "2.jpeg", "3.jpeg", "4.jpeg", "5.jpeg"],
            },
            {
                "spoken_text": "Pitucones.",
                "subtitle_text": "PITUCONES",
                "images": ["6.jpeg", "7.jpeg"],
            },
            {
                "spoken_text": "Vivo en la tela de la prenda, que complementan tu colección.",
                "subtitle_text": "VIVO EN LA TELA DE LA PRENDA QUE COMPLEMENTAN TU COLECCIÓN",
                "images": ["8.jpeg"],
            },
        ],
    },
}


@dataclass
class Cue:
    index: int
    start: float
    end: float
    text: str


@dataclass
class Slide:
    path: Path
    start: float
    end: float


CURRENT_CONFIG: dict = {}


def seconds_to_srt(value: float) -> str:
    millis = max(0, round(value * 1000))
    hours, rem = divmod(millis, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def write_srt(cues: Iterable[Cue], destination: Path) -> None:
    parts = []
    for cue in cues:
        wrapped = textwrap.fill(cue.text, width=44)
        parts.append(
            f"{cue.index}\n"
            f"{seconds_to_srt(cue.start)} --> {seconds_to_srt(cue.end)}\n"
            f"{wrapped}\n"
        )
    destination.write_text("\n".join(parts), encoding="utf-8")


def parse_duration_seconds(stderr_text: str) -> float:
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", stderr_text)
    if not match:
        raise RuntimeError("No pude leer la duración del audio generado.")
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def probe_duration_seconds(path: Path) -> float:
    ffmpeg_path = Path(imageio_ffmpeg.get_ffmpeg_exe())
    result = subprocess.run(
        [str(ffmpeg_path), "-i", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    return parse_duration_seconds(result.stderr)


async def synthesize_voice(audio_path: Path, subtitle_path: Path) -> list[Cue]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = CURRENT_CONFIG["slug"]
    blocks = CURRENT_CONFIG["blocks"]
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

    temp_dir = OUTPUT_DIR / f"{slug}-tts"
    temp_dir.mkdir(parents=True, exist_ok=True)

    segment_paths: list[Path] = []
    cues: list[Cue] = []
    cursor = 0.0

    for index, block in enumerate(blocks, start=1):
        segment_path = temp_dir / f"block-{index:02}.mp3"
        communicate = edge_tts.Communicate(
            block["spoken_text"],
            voice=VOICE,
            rate=VOICE_RATE,
            pitch=VOICE_PITCH,
        )
        await communicate.save(str(segment_path))

        duration = probe_duration_seconds(segment_path)
        start = cursor
        end = start + duration
        segment_paths.append(segment_path)
        cues.append(Cue(index=index, start=start, end=end, text=block["subtitle_text"]))
        cursor = end + PAUSE_BETWEEN_BLOCKS

    concat_file = temp_dir / "audio-concat.txt"
    concat_lines = []
    for index, segment_path in enumerate(segment_paths):
        duration = probe_duration_seconds(segment_path)
        concat_lines.append(f"file '{segment_path.name}'")
        if index < len(segment_paths) - 1:
            concat_lines.append(f"duration {duration + PAUSE_BETWEEN_BLOCKS:.3f}")
        else:
            concat_lines.append(f"duration {duration + TAIL_PAD_SECONDS:.3f}")
    concat_lines.append(f"file '{segment_paths[-1].name}'")
    concat_file.write_text("\n".join(concat_lines), encoding="utf-8")

    concat_command = [
        ffmpeg_path,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-af",
        f"apad=pad_dur={TAIL_PAD_SECONDS:.2f}",
        "-c:a",
        "mp3",
        "-q:a",
        "2",
        str(audio_path),
    ]
    subprocess.run(concat_command, check=True, cwd=temp_dir)

    write_srt(cues, subtitle_path)
    return cues


def build_slides(cues: list[Cue]) -> list[Slide]:
    slides: list[Slide] = []
    blocks = CURRENT_CONFIG["blocks"]
    for cue, block in zip(cues, blocks):
        image_paths = [CURRENT_CONFIG["source_dir"] / name for name in block["images"]]
        image_paths = [path for path in image_paths if path.exists()]
        if not image_paths:
            raise FileNotFoundError("No encontré imágenes para uno de los bloques del video.")

        per_image = (cue.end - cue.start) / len(image_paths)
        for index, image_path in enumerate(image_paths):
            start = cue.start + per_image * index
            end = cue.start + per_image * (index + 1)
            slides.append(Slide(path=image_path, start=start, end=end))

    return slides


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_candidates = [
        "C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]

    for candidate in font_candidates:
        font_path = Path(candidate)
        if font_path.exists():
            return ImageFont.truetype(str(font_path), size=size)

    return ImageFont.load_default()


def ease(progress: float) -> float:
    safe_progress = max(0.0, min(1.0, progress))
    return 0.5 - 0.5 * math.cos(math.pi * safe_progress)


def fit_cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    scale = max(target_w / image.width, target_h / image.height)
    resized = image.resize(
        (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
        Image.Resampling.LANCZOS,
    )
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def fit_contain(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    scale = min(target_w / image.width, target_h / image.height)
    resized = image.resize(
        (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    left = (target_w - resized.width) // 2
    top = (target_h - resized.height) // 2
    canvas.paste(resized, (left, top))
    return canvas


def build_slide_frame(slide: Slide, current_time: float) -> Image.Image:
    slide_duration = max(0.01, slide.end - slide.start)
    progress = ease((current_time - slide.start) / slide_duration)

    source = Image.open(slide.path).convert("RGB")
    photo_size = (VIDEO_SIZE[0], PHOTO_AREA_HEIGHT)

    background = fit_cover(source, photo_size)
    background = background.filter(ImageFilter.GaussianBlur(radius=28))
    background = Image.blend(background, Image.new("RGB", photo_size, "#3a291f"), 0.26)

    zoom = 1.0 + 0.018 * progress
    pan_x = int((progress - 0.5) * min(10, source.width * 0.009))
    pan_y = int((0.5 - progress) * min(8, source.height * 0.008))
    crop_w = max(1, int(source.width / zoom))
    crop_h = max(1, int(source.height / zoom))
    left = max(0, min(source.width - crop_w, (source.width - crop_w) // 2 + pan_x))
    top = max(0, min(source.height - crop_h, (source.height - crop_h) // 2 + pan_y))
    foreground = source.crop((left, top, left + crop_w, top + crop_h))
    foreground = fit_contain(foreground, (VIDEO_SIZE[0] - 140, PHOTO_AREA_HEIGHT - 56))

    frame = Image.new("RGBA", VIDEO_SIZE, "#201713")
    frame.paste(background.convert("RGBA"), (0, 0))

    panel = Image.new("RGBA", (VIDEO_SIZE[0] - 80, PHOTO_AREA_HEIGHT - 24), (255, 248, 241, 42))
    panel = panel.filter(ImageFilter.GaussianBlur(radius=1))
    frame.paste(panel, (40, 14), panel)

    fg_left = (VIDEO_SIZE[0] - foreground.width) // 2
    fg_top = (PHOTO_AREA_HEIGHT - foreground.height) // 2
    shadow = Image.new("RGBA", (foreground.width + 20, foreground.height + 20), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        (10, 10, shadow.width - 10, shadow.height - 10),
        radius=24,
        fill=(0, 0, 0, 88),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=12))
    frame.paste(shadow, (fg_left - 10, fg_top - 6), shadow)
    frame.paste(foreground, (fg_left, fg_top), foreground)

    draw = ImageDraw.Draw(frame)
    brand_font = load_font(22, bold=True)
    brand_text = "ESTABLECIMIENTOS OBI"
    badge_width = int(draw.textlength(brand_text, font=brand_font)) + 44
    draw.rounded_rectangle((28, 28, 28 + badge_width, 68), radius=18, fill="#8f3f27")
    draw.text((50, 39), brand_text, font=brand_font, fill="#fff8f2")

    band_top = PHOTO_AREA_HEIGHT
    draw.rectangle((0, band_top, VIDEO_SIZE[0], VIDEO_SIZE[1]), fill="#ffffff")
    draw.line((52, band_top + 18, VIDEO_SIZE[0] - 52, band_top + 18), fill="#d8d8d8", width=2)
    return frame


def export_video(
    slides: list[Slide],
    audio_path: Path,
    subtitle_path: Path,
    video_path: Path,
    poster_path: Path,
) -> None:
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    slug = CURRENT_CONFIG["slug"]
    slides_dir = OUTPUT_DIR / f"{slug}-slides"
    clips_dir = OUTPUT_DIR / f"{slug}-clips"
    slides_dir.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)

    concat_lines = []
    for index, slide in enumerate(slides, start=1):
        frame = build_slide_frame(slide, slide.start).convert("RGB")
        slide_image = slides_dir / f"slide-{index:02}.jpg"
        clip_path = clips_dir / f"clip-{index:02}.mp4"
        frame.save(slide_image, quality=94)

        if index == 1:
            poster_path.parent.mkdir(parents=True, exist_ok=True)
            frame.save(poster_path, quality=92)

        duration = max(0.6, slide.end - slide.start)
        crop_x = f"(iw-{VIDEO_SIZE[0]})*(0.5-0.5*cos(PI*t/{duration:.4f}))"
        crop_y = f"(ih-{VIDEO_SIZE[1]})*(0.5-0.5*cos(PI*t/{duration:.4f}))"
        vf = (
            "scale=1294:726,"
            f"crop={VIDEO_SIZE[0]}:{VIDEO_SIZE[1]}:x='{crop_x}':y='{crop_y}',"
            f"fps={FPS},format=yuv420p,setsar=1"
        )

        clip_command = [
            ffmpeg_path,
            "-y",
            "-loop",
            "1",
            "-t",
            f"{duration:.4f}",
            "-i",
            str(slide_image),
            "-vf",
            vf,
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(clip_path),
        ]
        subprocess.run(clip_command, check=True, cwd=OUTPUT_DIR)
        concat_lines.append(f"file '{clip_path.name}'")

    concat_file = clips_dir / "concat.txt"
    concat_file.write_text("\n".join(concat_lines), encoding="utf-8")

    subtitle_filter = (
        f"subtitles=../{subtitle_path.name}:"
        "force_style='FontName=Arial,FontSize=22,PrimaryColour=&H000000&,"
        "BackColour=&HFFFFFF&,BorderStyle=3,Outline=0,Shadow=0,MarginV=24,Alignment=2',"
        "setsar=1"
    )
    final_command = [
        ffmpeg_path,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        "concat.txt",
        "-i",
        str(audio_path),
        "-vf",
        subtitle_filter,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(video_path),
    ]
    subprocess.run(final_command, check=True, cwd=clips_dir)


def main() -> None:
    slug = CURRENT_CONFIG["slug"]
    audio_path = OUTPUT_DIR / f"{slug}-voz.mp3"
    subtitle_path = OUTPUT_DIR / f"{slug}.srt"
    video_path = OUTPUT_DIR / f"{slug}-web.mp4"
    poster_path = OUTPUT_DIR / f"{slug}-poster.jpg"

    cues = asyncio.run(synthesize_voice(audio_path, subtitle_path))
    slides = build_slides(cues)
    export_video(slides, audio_path, subtitle_path, video_path, poster_path)

    print(f"Audio: {audio_path}")
    print(f"Subtitulos: {subtitle_path}")
    print(f"Video: {video_path}")
    print(f"Poster: {poster_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("preset", nargs="?", default="video1", choices=sorted(VIDEO_CONFIGS.keys()))
    args = parser.parse_args()
    CURRENT_CONFIG = VIDEO_CONFIGS[args.preset]
    main()
