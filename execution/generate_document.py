from __future__ import annotations

import argparse
from pathlib import Path

from execution.converter import SUPPORTED_OUTPUTS, convert_images_to_document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert one or more images into a document.")
    parser.add_argument("images", nargs="+", help="Input image paths")
    parser.add_argument("--format", required=True, choices=sorted(SUPPORTED_OUTPUTS), help="Output format")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--title", help="Optional document title")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    image_paths = [Path(image) for image in args.images]
    output_path = Path(args.output)
    convert_images_to_document(image_paths, args.format, output_path, title=args.title)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
