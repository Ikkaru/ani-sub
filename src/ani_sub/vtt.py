import webvtt
from dataclasses import dataclass


@dataclass
class Cue:
    index: int
    start: str
    end: str
    text: str


def parse(path: str) -> list[Cue]:
    return [
        Cue(index=i, start=c.start, end=c.end, text=c.text)
        for i, c in enumerate(webvtt.read(path))
    ]


def write(path: str, cues: list[Cue]) -> None:
    vtt = webvtt.WebVTT(
        captions=[webvtt.Caption(c.start, c.end, c.text) for c in cues]
    )
    vtt.save(path)