#!/usr/bin/env python3

import argparse
import hashlib
import html
import json
import re
from pathlib import Path


ALLOWED_SLIDE_TYPES = {"slide", "subslide", "fragment", "notes", "skip"}
CALLOUT_LABELS = {
    "concept": "Concept",
    "example": "Example",
    "predict": "Predict before running",
    "try-it": "Try it",
    "checkpoint": "Checkpoint",
    "common-mistake": "Common mistake",
    "instructor-note": "Instructor note",
    "prairielearn-exercise": "PrairieLearn exercise",
    "takeaway": "Takeaway",
}



def normalize_cell_id(value):
    raw = str(value or "cell")
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "-", raw).strip("-_") or "cell"
    if len(normalized) <= 64:
        return normalized
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]
    return f"{normalized[:53].rstrip('-_')}-{digest}"


def automatic_cell_id(lecture_id, purpose, payload):
    serialized = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:10]
    return normalize_cell_id(f"{lecture_id}-{purpose}-{digest}")


def normalized_tags(tags):
    result = []
    for tag in tags or []:
        value = str(tag).strip()
        if value and value not in result:
            result.append(value)
    return result


def cell_metadata(slide_type, tags=None):
    if slide_type not in ALLOWED_SLIDE_TYPES:
        allowed = ", ".join(sorted(ALLOWED_SLIDE_TYPES))
        raise ValueError(f"Unsupported slide_type {slide_type!r}; expected one of: {allowed}")
    metadata = {"slideshow": {"slide_type": slide_type}}
    clean_tags = normalized_tags(tags)
    if clean_tags:
        metadata["tags"] = clean_tags
    return metadata


def make_markdown_cell(source, slide_type="slide", cell_id=None, tags=None):
    return {
        "cell_type": "markdown",
        "id": normalize_cell_id(cell_id),
        "metadata": cell_metadata(slide_type, tags),
        "source": source.splitlines(keepends=True),
    }


def make_code_cell(source, slide_type="subslide", cell_id=None, tags=None):
    metadata = cell_metadata(slide_type, tags)
    metadata["presentation"] = {"classes": ["nyu-lecture-slide", "nyu-code-slide"]}
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": normalize_cell_id(cell_id),
        "metadata": metadata,
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


def render_inline(value):
    escaped = html.escape(str(value or ""), quote=False)
    return re.sub(r"`([^`\n]+)`", r"<code>\1</code>", escaped)


def render_paragraphs(value):
    paragraphs = []
    for paragraph in str(value or "").split("\n\n"):
        paragraph = paragraph.strip()
        if paragraph:
            paragraphs.append(f"<p>{render_inline(paragraph).replace(chr(10), '<br>')}</p>")
    return "\n".join(paragraphs)


def render_list(items, ordered=False):
    if not items:
        return ""
    tag = "ol" if ordered else "ul"
    lines = [f"<{tag}>"]
    for item in items:
        if isinstance(item, dict):
            content = item.get("html") or render_inline(item.get("text", ""))
            children = render_list(item.get("items", []), item.get("ordered", False))
            lines.append(f"  <li>{content}")
            if children:
                lines.append(children)
            lines.append("  </li>")
        else:
            lines.append(f"  <li>{render_inline(item)}</li>")
    lines.append(f"</{tag}>")
    return "\n".join(lines)


def render_callout(block, cell_id):
    callout_type = block.get("callout_type", "concept")
    if callout_type not in CALLOUT_LABELS:
        supported = ", ".join(CALLOUT_LABELS)
        raise ValueError(f"Unsupported callout_type {callout_type!r}; expected one of: {supported}")

    label = block.get("label") or CALLOUT_LABELS[callout_type]
    title = block.get("title") or label
    heading_id = f"{cell_id}-heading"
    slide_class = "nyu-activity-slide" if callout_type == "prairielearn-exercise" else "nyu-content-slide"
    lines = [
        f'<aside class="nyu-lecture-slide {slide_class} lecture-shell lecture-callout '
        f'lecture-callout--{html.escape(callout_type)}" '
        f'aria-labelledby="{html.escape(heading_id)}">',
        f'  <p class="lecture-label">{render_inline(label)}</p>',
        f'  <h2 id="{html.escape(heading_id)}">{render_inline(title)}</h2>',
    ]

    body = render_paragraphs(block.get("body") or block.get("content", ""))
    if body:
        lines.append(body)
    items = render_list(block.get("items", []))
    if items:
        lines.append(items)

    fields = [
        ("objective", "Objective"),
        ("prompt", "Prompt"),
        ("instruction", "What to do"),
        ("why", "Why now"),
        ("activity", "Activity"),
        ("return_cue", "When you return"),
    ]
    for key, field_label in fields:
        value = block.get(key)
        if value:
            lines.append(
                f'  <p class="lecture-callout__field"><strong>{field_label}:</strong> '
                f"{render_inline(value)}</p>"
            )

    link = block.get("link") or {}
    if link.get("href") and link.get("text"):
        lines.append(
            f'  <p class="lecture-callout__action"><a class="lecture-link" href="{html.escape(str(link["href"]), quote=True)}">'
            f'{render_inline(link["text"])}</a></p>'
        )

    resource_paths = list(block.get("resource_paths", []))
    for key in ("assessment_path", "question_path"):
        if block.get(key):
            resource_paths.append(block[key])
    if resource_paths:
        lines.append('  <details class="lecture-resource-paths">')
        lines.append("    <summary>Author references</summary>")
        lines.append("    <ul>")
        for path in resource_paths:
            lines.append(f"      <li><code>{html.escape(str(path))}</code></li>")
        lines.append("    </ul>")
        lines.append("  </details>")

    lines.append("</aside>")
    return "\n".join(lines)


def render_title(manifest, cell_id):
    presentation = manifest.get("presentation", {})
    heading_id = f"{cell_id}-heading"
    lines = [
        f'<header class="nyu-lecture-slide nyu-hero-slide lecture-shell lecture-title" aria-labelledby="{html.escape(heading_id)}">',
        f'  <p class="lecture-eyebrow">{render_inline(manifest.get("course", ""))} · Lecture</p>',
        f'  <h1 id="{html.escape(heading_id)}">{render_inline(manifest.get("title", "Untitled Lecture"))}</h1>',
    ]
    subtitle = presentation.get("subtitle")
    if subtitle:
        lines.append(f'  <p class="lecture-title__subtitle">{render_inline(subtitle)}</p>')
    details = presentation.get("title_details", [])
    if details:
        lines.append('  <ul class="lecture-title__details">')
        for detail in details:
            lines.append(
                f"    <li><strong>{render_inline(detail.get('label', ''))}:</strong> "
                f"{render_inline(detail.get('value', ''))}</li>"
            )
        lines.append("  </ul>")
    lines.append("</header>")
    return "\n".join(lines)


def render_agenda(manifest, block, cell_id):
    heading_id = f"{cell_id}-heading"
    sections = block.get("items") or manifest.get("sections", [])
    lines = [
        f'<nav class="nyu-lecture-slide nyu-agenda-slide lecture-shell lecture-agenda" aria-labelledby="{html.escape(heading_id)}">',
        '  <p class="lecture-label">Lecture map</p>',
        f'  <h2 id="{html.escape(heading_id)}">{render_inline(block.get("title", "Today’s path"))}</h2>',
        '  <div class="lecture-agenda__grid">',
    ]
    for index, section in enumerate(sections, start=1):
        if isinstance(section, str):
            lines.append(
                f'    <article class="lecture-agenda__card"><span>{index:02d}</span>'
                f"<h3>{render_inline(section)}</h3></article>"
            )
        else:
            objective_text = section.get("objectives") or []
            lines.append(
                f'    <article class="lecture-agenda__card"><span>{index:02d}</span>'
                f"<h3>{render_inline(section.get('title', 'Section'))}</h3>"
                f"<p>{render_inline(', '.join(objective_text))}</p></article>"
            )
    lines.extend(["  </div>", "</nav>"])
    return "\n".join(lines)


def render_objectives(manifest, block, cell_id):
    heading_id = f"{cell_id}-heading"
    objectives = block.get("items") or manifest.get("learning_objectives", [])
    lines = [
        f'<section class="nyu-lecture-slide nyu-content-slide lecture-shell lecture-objectives" aria-labelledby="{html.escape(heading_id)}">',
        '  <p class="lecture-label">Learning objectives</p>',
        f'  <h2 id="{html.escape(heading_id)}">{render_inline(block.get("title", "By the end of this lecture"))}</h2>',
        "  <ol>",
    ]
    for objective in objectives:
        if isinstance(objective, str):
            lines.append(f"    <li>{render_inline(objective)}</li>")
        else:
            lines.append(
                f"    <li><strong>{render_inline(objective.get('id', ''))}</strong> "
                f"{render_inline(objective.get('text', ''))}</li>"
            )
    lines.extend(["  </ol>", "</section>"])
    return "\n".join(lines)


def render_section(manifest, block, cell_id):
    section = dict(block)
    section_id = block.get("section_id")
    if section_id:
        match = next((item for item in manifest.get("sections", []) if item.get("id") == section_id), None)
        if not match:
            raise ValueError(f"Unknown section_id {section_id!r}")
        section = {**match, **block}
    heading_id = f"{cell_id}-heading"
    number = section.get("number", "")
    total = section.get("total") or len(manifest.get("sections", []))
    number_text = f"Section {number}" + (f" of {total}" if total else "")
    lines = [
        f'<section class="nyu-lecture-slide nyu-section-slide lecture-shell lecture-section" aria-labelledby="{html.escape(heading_id)}">',
        f'  <p class="lecture-label">{render_inline(number_text)}</p>',
        f'  <h2 id="{html.escape(heading_id)}">{render_inline(section.get("title", "Section"))}</h2>',
    ]
    if section.get("body"):
        lines.append(
            f'  <div class="lecture-section__purpose">{render_paragraphs(section["body"])}</div>'
        )
    if section.get("objectives"):
        lines.append(
            f'  <p class="lecture-section__objectives"><strong>Objectives:</strong> '
            f"{render_inline(', '.join(section['objectives']))}</p>"
        )
    lines.append("</section>")
    return "\n".join(lines)


def render_review_map(block, cell_id):
    heading_id = f"{cell_id}-heading"
    lines = [
        f'<section class="nyu-lecture-slide nyu-review-slide lecture-shell lecture-review-map" aria-labelledby="{html.escape(heading_id)}">',
        '  <p class="lecture-label">Review map</p>',
        f'  <h2 id="{html.escape(heading_id)}">{render_inline(block.get("title", "Objectives to practice"))}</h2>',
        '  <div class="lecture-review-map__grid">',
    ]
    for row in block.get("rows", []):
        practice = render_inline(row.get("practice", ""))
        if row.get("href"):
            practice = (
                f'<a href="{html.escape(str(row["href"]), quote=True)}">{practice}</a>'
            )
        lines.append(
            '    <article class="lecture-review-map__card">'
            f"<h3>{render_inline(row.get('objective', ''))}</h3>"
            f'<p><strong>Lecture evidence</strong><br>{render_inline(row.get("evidence", ""))}</p>'
            f'<p><strong>Next practice</strong><br>{practice}</p>'
            "</article>"
        )
    lines.extend(["  </div>", "</section>"])
    return "\n".join(lines)


def render_ed_segments(segments):
    lines = []
    for segment in segments or []:
        segment_type = segment.get("type", "paragraph")
        if segment_type == "heading":
            lines.append(f'<h3>{render_inline(segment.get("text", ""))}</h3>')
        elif segment_type == "paragraph":
            if segment.get("html"):
                lines.append(f'<p>{segment["html"]}</p>')
            else:
                lines.append(f'<p>{render_inline(segment.get("text", ""))}</p>')
        elif segment_type == "list":
            lines.append(render_list(segment.get("items", []), segment.get("ordered", False)))
        elif segment_type == "math":
            lines.append(f'<div class="lecture-ed-math">\\[{html.escape(str(segment.get("tex", "")), quote=False)}\\]</div>')
        elif segment_type == "source_code":
            language = html.escape(str(segment.get("language", "text")), quote=True)
            lines.append(f'<pre class="lecture-ed-source"><code data-language="{language}">{html.escape(str(segment.get("text", "")))}</code></pre>')
        elif segment_type == "prompt":
            lines.append(
                f'<p class="lecture-ed-prompt"><strong>{render_inline(segment.get("label", "Prompt"))}:</strong> '
                f'{render_inline(segment.get("text", ""))}</p>'
            )
        elif segment_type == "choices":
            lines.append('<ol class="lecture-ed-choices">')
            for choice in segment.get("items", []):
                lines.append(f'  <li><span aria-hidden="true"></span><code>{html.escape(str(choice))}</code></li>')
            lines.append("</ol>")
        elif segment_type == "link":
            lines.append(
                f'<p class="lecture-ed-action"><a class="lecture-link" href="{html.escape(str(segment.get("href", "")), quote=True)}">'
                f'{render_inline(segment.get("text", "Open practice"))}</a></p>'
            )
        elif segment_type == "image":
            src = str(segment.get("src", "")).strip()
            if not src:
                raise ValueError("Ed image segments require a non-empty src")
            alt = str(segment.get("alt", ""))
            lines.append(
                '<figure class="lecture-ed-figure" style="margin:1rem auto 0;text-align:center;">'
                f'<img src="{html.escape(src, quote=True)}" alt="{html.escape(alt, quote=True)}" '
                'style="display:block;height:auto;margin:0 auto;max-height:42vh;max-width:100%;object-fit:contain;width:auto;">'
                "</figure>"
            )
        else:
            raise ValueError(f"Unsupported Ed segment type: {segment_type!r}")
    return "\n".join(line for line in lines if line)


def render_prairielearn_signpost(block):
    signpost = block.get("prairielearn_signpost") or {}
    href = str(signpost.get("href", "")).strip()
    status = str(signpost.get("status", "")).strip()
    pending = status == "deployment_pending"
    if not href and not pending:
        raise ValueError("PrairieLearn signposts require a non-empty href")

    location = str(signpost.get("location", "")).strip()
    lines = [
        '<div style="',
        '    border:2px solid #b26a00;border-left:10px solid #b26a00;',
        '    background:#fff6e6;border-radius:12px;padding:1.3em 1.5em;">',
        '  <div style="font-size:0.6em;font-weight:800;letter-spacing:0.16em;',
        '              text-transform:uppercase;color:#b26a00;">',
        '    &#129514; In-Class Exercise',
        '  </div>',
        '  <div style="font-size:1.15em;font-weight:800;color:#241c2c;margin:0.45em 0 0.9em 0;">',
        f'    {render_inline(block.get("title", "Untitled"))}',
        '  </div>',
        '  <div style="background:#fff;border:2px dashed #b26a00;border-radius:8px;',
        '              padding:0.8em 1em;">',
    ]
    if pending:
        lines.extend([
            '    <span style="font-size:1.05em;font-weight:800;color:#b26a00;">',
            '      PrairieLearn activity deployment pending',
            '    </span>',
        ])
    else:
        lines.extend([
            f'    <a href="{html.escape(href, quote=True)}" target="_blank" rel="noopener"',
            '       style="font-size:1.05em;font-weight:800;color:#b26a00;',
            '              text-decoration:underline;">Exercise Link</a>',
        ])
    if location:
        lines.extend(
            [
                '    <div style="font-size:0.7em;color:#241c2c;margin-top:0.45em;">',
                f'      {render_inline(location)}',
                '    </div>',
            ]
        )
    if not pending:
        lines.extend([
            '    <div style="font-size:0.6em;color:#6b6478;margin-top:0.5em;',
            '                overflow-wrap:anywhere;">',
            "      If the hyperlink doesn't work, paste this link into your browser:",
            '      <span style="font-family:ui-monospace,SFMono-Regular,Menlo,monospace;">'
            f'{html.escape(href)}</span>',
            '    </div>',
        ])
    lines.extend(['  </div>', '</div>'])
    return "\n".join(lines)


def render_ed_slide(block, cell_id):
    if block.get("prairielearn_signpost") and not block.get("include_source_with_signpost"):
        return render_prairielearn_signpost(block)

    heading_id = f"{cell_id}-heading"
    layout_value = block.get("layout", "nyu-explanation-code-slide")
    layout_variant_value = block.get("layout_variant", "")
    layout = html.escape(layout_value)
    layout_variant = html.escape(layout_variant_value)
    code_cells = block.get("code_cells", [])
    code_density = ""
    if code_cells:
        code_density = (
            "nyu-code-density-long"
            if any("nyu-long-code" in code.get("tags", []) for code in code_cells)
            else "nyu-code-density-short"
        )
    lines = [
        f'<article class="nyu-lecture-slide nyu-ed-slide lecture-shell {layout} {layout_variant} {code_density}" aria-labelledby="{html.escape(heading_id)}">',
        f'  <h2 id="{html.escape(heading_id)}">{render_inline(block.get("title", "Untitled"))}</h2>',
    ]
    columns = block.get("columns", [])
    if columns:
        lines.append('  <div class="lecture-ed-columns">')
        for column in columns:
            lines.append('    <section class="lecture-ed-column">')
            lines.append(render_ed_segments(column))
            lines.append("    </section>")
        lines.append("  </div>")
    else:
        lines.append(render_ed_segments(block.get("segments", [])))
    if block.get("prairielearn_signpost"):
        lines.append(render_prairielearn_signpost(block))
    lines.append("</article>")
    return "\n".join(line for line in lines if line)


def ed_slide_to_cells(block, manifest, block_index):
    lecture_id = manifest.get("id", "lecture")
    payload = {key: value for key, value in block.items() if key != "id"}
    cell_id = normalize_cell_id(
        block.get("id") or automatic_cell_id(lecture_id, f"ed-slide-{block_index}", payload)
    )
    layout = block.get("layout", "nyu-explanation-code-slide")
    layout_variant = block.get("layout_variant")
    provenance = block.get("provenance", "ed-original")
    provenance_tag = "ed-derived" if provenance == "ed-derived" else "ed-original"
    tags = list(block.get("tags", []))
    tags.extend([provenance_tag, layout])
    if layout_variant:
        tags.append(layout_variant)
    cells = [
        make_markdown_cell(
            render_ed_slide(block, cell_id),
            block.get("slide_type", "slide"),
            cell_id,
            tags,
        )
    ]
    for code_index, code in enumerate(block.get("code_cells", []), start=1):
        code_id = normalize_cell_id(f"{cell_id}-code-{code_index}")
        code_tags = list(code.get("tags", []))
        code_tags.extend(
            [
                "executable-code",
                "ed-original-code",
                layout,
                "nyu-lecture-slide",
                "nyu-code-slide",
            ]
        )
        if layout_variant:
            code_tags.append(layout_variant)
        cells.append(
            make_code_cell(
                code.get("content", ""),
                code.get("slide_type", "fragment"),
                code_id,
                code_tags,
            )
        )
    return cells


def block_to_cell(block, manifest, block_index):
    block_type = block.get("block_type", "explanation")
    callout_type = block.get("callout_type")
    default_slide_type = "subslide" if block_type == "code" else "slide"
    slide_type = block.get("slide_type", default_slide_type)
    if callout_type == "instructor-note":
        if slide_type != "notes":
            raise ValueError("instructor-note callouts must use slide_type 'notes'")

    lecture_id = manifest.get("id", "lecture")
    payload = {key: value for key, value in block.items() if key != "id"}
    cell_id = normalize_cell_id(
        block.get("id") or automatic_cell_id(lecture_id, f"block-{block_index}", payload)
    )
    tags = list(block.get("tags", []))

    layout = block.get("layout")
    if callout_type:
        source = render_callout(block, cell_id)
        tags.extend(["semantic-callout", f"callout-{callout_type}"])
    elif layout == "agenda":
        source = render_agenda(manifest, block, cell_id)
        tags.append("lecture-agenda")
    elif layout == "objectives":
        source = render_objectives(manifest, block, cell_id)
        tags.append("learning-objectives")
    elif layout == "section":
        source = render_section(manifest, block, cell_id)
        tags.append("section-divider")
    elif layout == "review-map":
        source = render_review_map(block, cell_id)
        tags.append("review-map")
    else:
        source = block.get("content", "")

    if block_type == "code":
        tags.extend(["executable-code", "nyu-lecture-slide", "nyu-code-slide"])
        return make_code_cell(source, slide_type, cell_id, tags)
    return make_markdown_cell(source, slide_type, cell_id, tags)


def block_to_cells(block, manifest, block_index):
    if block.get("block_type") == "ed_slide":
        return ed_slide_to_cells(block, manifest, block_index)
    return [block_to_cell(block, manifest, block_index)]


def legacy_exercise_index(exercises):
    exercise_lines = ["## Linked PrairieLearn Exercises\n\n"]
    for exercise in exercises:
        exercise_id = exercise.get("exercise_id", "unknown_exercise")
        placement = exercise.get("placement", "")
        site_url = exercise.get("prairielearn_site_url") or "TODO: add PrairieLearn site URL"
        question_path = exercise.get("prairielearn_question_path") or "TODO: add PrairieLearn question path"
        exercise_lines.append(f"- **{exercise_id}**\n")
        exercise_lines.append(f"  - Placement: {placement}\n")
        exercise_lines.append(f"  - PrairieLearn URL: {site_url}\n")
        exercise_lines.append(f"  - Question path: `{question_path}`\n")
    return "".join(exercise_lines)


def append_unique_cell(cells, cell, seen_ids):
    cell_id = cell["id"]
    if cell_id in seen_ids:
        raise ValueError(f"Duplicate generated cell id: {cell_id}")
    seen_ids.add(cell_id)
    cells.append(cell)


def build_notebook(manifest):
    cells = []
    seen_ids = set()
    lecture_id = manifest.get("id", "lecture")
    presentation = manifest.get("presentation", {})
    semantic_ui = presentation.get("ui") == "semantic-callouts-v1"

    if presentation.get("include_title", True):
        title_id = normalize_cell_id(f"{lecture_id}-title")
        if semantic_ui:
            title_source = render_title(manifest, title_id)
        else:
            title = manifest.get("title", "Untitled Lecture")
            course = manifest.get("course", "")
            title_source = f"# {course}: {title}\n\nLecture ID: `{lecture_id}`"
        append_unique_cell(
            cells,
            make_markdown_cell(
                title_source,
                "slide",
                title_id,
                ["lecture-title", "nyu-hero-slide"] if semantic_ui else ["lecture-title"],
            ),
            seen_ids,
        )

    for index, block in enumerate(manifest.get("lecture_blocks", [])):
        for cell in block_to_cells(block, manifest, index):
            append_unique_cell(cells, cell, seen_ids)

    exercises = manifest.get("in_class_exercises", [])
    include_exercise_index = presentation.get("include_exercise_index", True)
    if exercises and include_exercise_index:
        index_id = automatic_cell_id(lecture_id, "exercise-index", exercises)
        source = legacy_exercise_index(exercises)
        append_unique_cell(
            cells,
            make_markdown_cell(source, "slide", index_id, ["prairielearn-index"]),
            seen_ids,
        )

    rise_metadata = {
        "theme": "simple",
        "transition": "slide",
        "start_slideshow_at": "selected",
    }
    rise_metadata.update(presentation.get("rise", {}))
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "pygments_lexer": "ipython3",
            },
            "rise": rise_metadata,
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Convert a curriculum manifest into a Jupyter notebook with RISE metadata."
    )
    parser.add_argument("manifest", help="Path to curriculum manifest JSON")
    parser.add_argument("output", help="Output .ipynb path")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    output_path = Path(args.output)
    manifest = json.loads(manifest_path.read_text())
    notebook = build_notebook(manifest)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {output_path}")
    print(f"Cells: {len(notebook['cells'])}")


if __name__ == "__main__":
    main()
