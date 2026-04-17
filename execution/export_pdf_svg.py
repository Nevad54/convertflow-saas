from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from execution.pdf_tools import pdf_page_to_svg


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a PDF page to SVG.")
    parser.add_argument("input_pdf", type=Path, help="Path to the source PDF")
    parser.add_argument("output_svg", type=Path, help="Path to the target SVG")
    parser.add_argument("--page", type=int, default=1, help="1-based page number to export")
    parser.add_argument(
        "--text-as-path",
        action="store_true",
        help="Convert text to paths for maximum appearance fidelity",
    )
    args = parser.parse_args()

    page_number = args.page - 1
    pdf_page_to_svg(
        args.input_pdf,
        args.output_svg,
        page_number=page_number,
        text_as_path=args.text_as_path,
    )
    print(args.output_svg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
