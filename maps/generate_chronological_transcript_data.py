#!/usr/bin/env python3
"""Convert the edited chronological Markdown transcript into browser data.

The generated file contains references into the original recordings. It never
reads, rewrites, clips, or re-encodes either MP3.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "transcripts" / "chronological_edited_transcript.md"
OUTPUT = ROOT / "maps" / "vendor" / "chronological_transcript_data.js"

TIMED_LINE = re.compile(
    r"^\*\*\[(jaques-([ab])\.transcript\.md) "
    r"(\d{2}:\d{2}:\d{2})[–-](\d{2}:\d{2}:\d{2})\] ([^:]+):\*\*\s*(.*)$"
)


def seconds(timestamp: str) -> int:
    hours, minutes, secs = (int(part) for part in timestamp.split(":"))
    return hours * 3600 + minutes * 60 + secs


def stable_id(source: str, start: str, end: str, text: str) -> str:
    digest = hashlib.sha1(f"{source}|{start}|{end}|{text}".encode()).hexdigest()[:10]
    return f"line-{source}-{start.replace(':', '')}-{digest}"


def main() -> None:
    entries: list[dict[str, object]] = []
    unparsed_timed: list[tuple[int, str]] = []

    for line_number, raw in enumerate(SOURCE.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue

        struck = line.startswith("~~**[") and line.endswith("~~")
        parse_line = line[2:-2].strip() if struck else line
        match = TIMED_LINE.match(parse_line)
        if match:
            source_name, recording, start, end, speaker, text = match.groups()
            start_seconds = seconds(start)
            end_seconds = seconds(end)
            # Some single-word utterances were timestamped to the same whole
            # second at both ends. Keep their displayed source timestamps but
            # provide a short, non-destructive playback window for the player.
            playback_end = end_seconds if end_seconds > start_seconds else start_seconds + 1
            entries.append({
                "type": "cue",
                "id": stable_id(recording, start, end, text),
                "recording": recording,
                "source": source_name,
                "start": start_seconds,
                "end": playback_end,
                "sourceEnd": end_seconds,
                "startLabel": start,
                "endLabel": end,
                "speaker": speaker,
                "text": text,
                "struck": struck,
                "markdownLine": line_number,
            })
            continue

        if line.startswith("**["):
            unparsed_timed.append((line_number, line))
            continue

        heading = re.match(r"^(#{1,4})\s+(.+)$", line)
        if heading:
            entries.append({
                "type": "heading",
                "level": len(heading.group(1)),
                "text": heading.group(2),
                "markdownLine": line_number,
            })
        elif line.startswith(">"):
            entries.append({
                "type": "context",
                "style": "blockquote",
                "text": line.lstrip("> "),
                "markdownLine": line_number,
            })
        elif line.lower().startswith("editors note") or line.lower().startswith("**editors note"):
            entries.append({
                "type": "context",
                "style": "editor-note",
                "text": line.strip("*"),
                "markdownLine": line_number,
            })
        else:
            entries.append({
                "type": "context",
                "style": "paragraph",
                "text": line,
                "markdownLine": line_number,
            })

    if unparsed_timed:
        details = "\n".join(f"line {number}: {line}" for number, line in unparsed_timed)
        raise SystemExit(f"Unparsed timestamped transcript lines:\n{details}")

    cue_count = sum(entry["type"] == "cue" for entry in entries)
    payload = {
        "title": "Chronological Combined Edited Transcript",
        "source": "../transcripts/chronological_edited_transcript.md",
        "audio": {"a": "../jaques-a.mp3", "b": "../jaques-b.mp3"},
        "cueCount": cue_count,
        "entries": entries,
    }
    OUTPUT.write_text(
        "window.CHRONOLOGICAL_TRANSCRIPT = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    print(f"Generated {OUTPUT.relative_to(ROOT)} with {cue_count} timed cues.")


if __name__ == "__main__":
    main()
