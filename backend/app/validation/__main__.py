"""Run the AS-022 validation against live IRSA and SkyBoT.

Usage (from backend/):
    python -m app.validation --fields validation/fields.json \
        --out-json validation/results/as022_validation.json \
        --out-md validation/results/as022_validation.md
"""

import argparse
import json
from pathlib import Path

from app.validation.models import ValidationField
from app.validation.runner import render_markdown, run_validation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fields", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args()

    fields = [
        ValidationField.model_validate(item)
        for item in json.loads(args.fields.read_text())
    ]
    report = run_validation(
        fields, progress=lambda message: print(message, flush=True)
    )

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(report.model_dump_json() + "\n")
    args.out_md.write_text(render_markdown(report))
    print(f"wrote {args.out_json} and {args.out_md}")


if __name__ == "__main__":
    main()
