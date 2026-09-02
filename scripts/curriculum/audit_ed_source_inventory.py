#!/usr/bin/env python3
"""Audit CS0001 Ed source records, manifests, notebooks, assets, and PL mappings."""

import argparse
import json
from pathlib import Path


FORBIDDEN_URL_PARTS = (
    "/assessment_instance/", "/instance_question/", "/instructor/", "/preview/"
)


def load(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    inventory = load(root / "curriculum-source/cs1/ed/course_migration_inventory.json")
    activities = load(root / "curriculum-source/cs1/ed/course_activity_inventory.json")["activities"]
    activity_by_lecture = {}
    for activity in activities:
        activity_by_lecture.setdefault(activity["lecture"], []).append(activity)

    errors = []
    table = []
    for row in inventory["remaining_lectures"]:
        lecture = row["target_lecture"]
        source = load(root / row["source_record"])
        manifest = load(root / row["manifest"])
        notebook = load(root / row["notebook"])
        expected = row["slide_ids"]
        source_ids = [slide["slide_id"] for slide in source["slides"]]
        manifest_ids = [block["ed_slide_id"] for block in manifest["lecture_blocks"]]
        if source_ids != expected:
            errors.append(f"Lecture {lecture}: source slide order differs from course inventory")
        if manifest_ids != expected:
            errors.append(f"Lecture {lecture}: manifest slide order differs from Ed inventory")
        if len(set(expected)) != len(expected):
            errors.append(f"Lecture {lecture}: duplicate Ed slide ID")

        ids = [cell.get("id") for cell in notebook["cells"]]
        if len(ids) != len(set(ids)):
            errors.append(f"Lecture {lecture}: duplicate notebook cell ID")
        code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
        for cell in code_cells:
            if cell.get("outputs") != [] or cell.get("execution_count") is not None:
                errors.append(f"Lecture {lecture}: code cell {cell.get('id')} contains execution state")
        rise = notebook.get("metadata", {}).get("rise", {})
        if not all(key in rise for key in ("theme", "transition", "start_slideshow_at")):
            errors.append(f"Lecture {lecture}: incomplete RISE metadata")

        image_count = 0
        for source_slide in source["slides"]:
            for asset_info in source_slide.get("assets", []):
                image_count += 1
                local_path = asset_info.get("local_path")
                if not local_path or not (root / local_path).is_file():
                    errors.append(f"Lecture {lecture}: unresolved source asset {local_path}")
        for block in manifest["lecture_blocks"]:
            for segment in block.get("segments", []):
                if segment.get("type") == "image":
                    asset = root / "notebooks/cs1" / segment["src"]
                    if not asset.is_file():
                        errors.append(f"Lecture {lecture}: unresolved image {segment['src']}")
        pending = sum(
            block.get("prairielearn_signpost", {}).get("status") == "deployment_pending"
            for block in manifest["lecture_blocks"]
        )
        activity_count = len(activity_by_lecture.get(lecture, []))
        if pending != activity_count:
            errors.append(f"Lecture {lecture}: {pending} pending signposts for {activity_count} activities")
        notebook_text = json.dumps(notebook)
        for forbidden in FORBIDDEN_URL_PARTS:
            if forbidden in notebook_text:
                errors.append(f"Lecture {lecture}: forbidden URL fragment {forbidden}")
        table.append({
            "lecture": lecture,
            "ed_lesson_id": row["ed_lesson_id"],
            "ed_slide_count": len(expected),
            "generated_slide_count": len(manifest_ids),
            "runnable_code_count": len(code_cells),
            "image_count": image_count,
            "pl_activity_count": activity_count,
            "pl_question_count": activity_count,
            "single_question_assessment_count": activity_count,
            "pending_direct_link_count": pending,
            "warnings": [],
        })
    result = {"ok": not errors, "errors": errors, "table": table}
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(errors))


if __name__ == "__main__":
    main()
