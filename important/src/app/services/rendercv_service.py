"""RenderCV integration service for Compust Resume Studio.

Translates Compust's canonical JSON resume data model into RenderCV YAML,
compiling pixel-perfect, ATS-friendly documents via the Typst engine.
Produces both exported PDFs and high-resolution per-page PNG images for
the live preview, eliminating layout drift and pagination mismatch by construction.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any

from ruamel.yaml import YAML

from ..schemas_resume import resolve_section_title
from .resume_localization import (
    format_language_display,
    format_skill_display,
    get_localized_present_label,
)

logger = logging.getLogger("compust.rendercv")

# Map Compust templates to RenderCV built-in themes
THEME_MAPPING: dict[str, str] = {
    "classic": "classic",
    "modern": "classic",
    "minimal": "sb2nov",
    "technical": "engineeringresumes",
}

# Map Compust languages to RenderCV supported locales
LOCALE_MAPPING: dict[str, str] = {
    "en": "english",
    "fr": "french",
    "de": "german",
    "es": "spanish",
}


def hex_to_rgb_tuple(hex_str: str) -> tuple[int, int, int]:
    """Convert hex color string like #2563eb to (r, g, b) integers."""
    clean = hex_str.lstrip("#").strip()
    if len(clean) == 3:
        clean = "".join(c * 2 for c in clean)
    if len(clean) != 6:
        return (37, 99, 235)
    try:
        return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16))
    except ValueError:
        return (37, 99, 235)


def normalize_rendercv_date(date_str: str | None) -> str | None:
    """Normalize date string to standard RenderCV format (YYYY-MM or YYYY)."""
    if not date_str or not isinstance(date_str, str):
        return None
    s = date_str.strip()
    if not s or s.lower() in ("present", "présent", "heute", "current", "now"):
        return "present"

    # Match YYYY-MM
    match_ym = re.search(r"\b(19\d\d|20\d\d)[-/.](0[1-9]|1[0-2])\b", s)
    if match_ym:
        return f"{match_ym.group(1)}-{match_ym.group(2)}"

    # Match MM/YYYY or MM-YYYY
    match_my = re.search(r"\b(0[1-9]|1[0-2])[-/.](19\d\d|20\d\d)\b", s)
    if match_my:
        return f"{match_my.group(2)}-{match_my.group(1)}"

    # Match 4-digit Year
    match_y = re.search(r"\b(19\d\d|20\d\d)\b", s)
    if match_y:
        return match_y.group(1)

    return s


def build_rendercv_yaml_dict(
    structured_data: dict[str, Any],
    settings: dict[str, Any] | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Translate Compust canonical resume data to RenderCV YAML dictionary."""
    settings = settings or {}
    profile = structured_data.get("profile", {}) or {}
    lang = (settings.get("language") or "en").lower()
    locale_name = LOCALE_MAPPING.get(lang, "english")

    theme_setting = (settings.get("template") or "modern").lower()
    theme_name = THEME_MAPPING.get(theme_setting, "classic")

    doc_size = (settings.get("document_size") or "A4").upper()
    page_size = "a4" if doc_size == "A4" else "us-letter"

    theme_color = settings.get("theme_color") or "#2563eb"
    r, g, b = hex_to_rgb_tuple(theme_color)
    color_rgb_str = f"rgb({r}, {g}, {b})"

    section_titles = settings.get("section_titles") or {}
    visibility = settings.get("section_visibility") or {}
    order = settings.get("section_order") or [
        "summary",
        "experience",
        "education",
        "skills",
        "projects",
        "certifications",
        "languages",
        "custom_sections",
    ]

    # 1. Base CV header (B1: robust name extraction hierarchy)
    cand_name = (
        profile.get("full_name")
        or profile.get("name")
        or structured_data.get("full_name")
        or structured_data.get("name")
        or f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip()
        or "Candidate Name"
    ).strip()
    if not cand_name:
        cand_name = "Candidate Name"

    cv_dict: dict[str, Any] = {
        "name": cand_name,
    }

    if profile.get("headline"):
        cv_dict["headline"] = profile["headline"].strip()
    if profile.get("location"):
        cv_dict["location"] = profile["location"].strip()
    if profile.get("email"):
        cv_dict["email"] = profile["email"].strip()
    if profile.get("phone"):
        cv_dict["phone"] = profile["phone"].strip()
    if profile.get("website"):
        cv_dict["website"] = profile["website"].strip()

    socials = []
    if profile.get("linkedin"):
        li = profile["linkedin"].strip()
        user_match = re.search(r"linkedin\.com/in/([^/?#]+)", li)
        username = user_match.group(1) if user_match else li
        socials.append({"network": "LinkedIn", "username": username})
    if profile.get("github"):
        gh = profile["github"].strip()
        user_match = re.search(r"github\.com/([^/?#]+)", gh)
        username = user_match.group(1) if user_match else gh
        socials.append({"network": "GitHub", "username": username})
    if socials:
        cv_dict["social_networks"] = socials

    # 2. Sections construction
    sections_dict: dict[str, list[Any]] = {}

    for sec_key in order:
        if visibility.get(sec_key) is False:
            continue

        resolved_title = resolve_section_title(sec_key, section_titles.get(sec_key), lang=lang)

        if sec_key == "summary" and profile.get("summary"):
            summary_text = profile["summary"].strip()
            if summary_text:
                sections_dict[resolved_title] = [summary_text]

        elif sec_key == "skills" and structured_data.get("skills"):
            skills_list = structured_data["skills"]
            if skills_list:
                categories: dict[str, list[str]] = {}
                for s in skills_list:
                    name = (s.get("name") or "").strip()
                    if not name:
                        continue
                    cat = (s.get("category") or "Technical").strip()
                    if name not in categories.setdefault(cat, []):
                        categories[cat].append(name)

                cat_entries = []
                for cat_name, items in categories.items():
                    cat_entries.append({
                        "label": cat_name,
                        "details": ", ".join(items),
                    })
                if cat_entries:
                    sections_dict[resolved_title] = cat_entries

        elif sec_key == "experience" and structured_data.get("experience"):
            exp_list = structured_data["experience"]
            exp_entries = []
            for exp in exp_list:
                company = (exp.get("company") or "").strip()
                title = (exp.get("title") or "").strip()
                if not company and not title:
                    continue

                entry: dict[str, Any] = {
                    "company": company or "Organization",
                    "position": title or "Role",
                }
                if exp.get("location"):
                    entry["location"] = exp["location"].strip()

                start = normalize_rendercv_date(exp.get("start_date"))
                if exp.get("is_current"):
                    end = "present"
                else:
                    end = normalize_rendercv_date(exp.get("end_date"))

                if start and end:
                    entry["start_date"] = start
                    entry["end_date"] = end
                elif start:
                    entry["date"] = start
                elif end:
                    entry["date"] = end

                highlights = []
                desc = exp.get("description", "") or ""
                for line in desc.splitlines():
                    cleaned = line.strip().lstrip("-•* ").strip()
                    if cleaned:
                        highlights.append(cleaned)
                for hl in exp.get("highlights", []) or []:
                    cleaned = str(hl).strip().lstrip("-•* ").strip()
                    if cleaned and cleaned not in highlights:
                        highlights.append(cleaned)

                if highlights:
                    entry["highlights"] = highlights

                exp_entries.append(entry)

            if exp_entries:
                sections_dict[resolved_title] = exp_entries

        elif sec_key == "education" and structured_data.get("education"):
            edu_list = structured_data["education"]
            edu_entries = []
            for edu in edu_list:
                institution = (edu.get("institution") or "").strip()
                degree = (edu.get("degree") or "").strip()
                field = (edu.get("field") or "").strip()
                if not institution and not degree and not field:
                    continue

                entry = {
                    "institution": institution or "Academic Institution",
                    "area": field or degree or "Studies",
                    "degree": degree or "Degree",
                }
                if edu.get("location"):
                    entry["location"] = edu["location"].strip()

                start = normalize_rendercv_date(edu.get("start_date"))
                end = normalize_rendercv_date(edu.get("end_date"))
                if start and end:
                    entry["start_date"] = start
                    entry["end_date"] = end
                elif end:
                    entry["date"] = end
                elif start:
                    entry["date"] = start

                highlights = []
                if edu.get("gpa"):
                    highlights.append(f"GPA / Honors: {edu['gpa'].strip()}")
                desc = edu.get("description", "") or ""
                for line in desc.splitlines():
                    cleaned = line.strip().lstrip("-•* ").strip()
                    if cleaned:
                        highlights.append(cleaned)

                if highlights:
                    entry["highlights"] = highlights

                edu_entries.append(entry)

            if edu_entries:
                sections_dict[resolved_title] = edu_entries

        elif sec_key == "projects" and structured_data.get("projects"):
            proj_list = structured_data["projects"]
            proj_entries = []
            for proj in proj_list:
                name = (proj.get("name") or "").strip()
                if not name:
                    continue
                url = (proj.get("url") or "").strip()
                entry_name = f"[{name}]({url})" if url else name
                entry = {"name": entry_name}

                techs = (proj.get("technologies") or "").strip()
                if techs:
                    entry["summary"] = techs

                start = normalize_rendercv_date(proj.get("start_date"))
                end = normalize_rendercv_date(proj.get("end_date"))
                if start and end:
                    entry["start_date"] = start
                    entry["end_date"] = end
                elif start or end:
                    entry["date"] = start or end

                highlights = []
                desc = proj.get("description", "") or ""
                for line in desc.splitlines():
                    cleaned = line.strip().lstrip("-•* ").strip()
                    if cleaned:
                        highlights.append(cleaned)

                if highlights:
                    entry["highlights"] = highlights

                proj_entries.append(entry)

            if proj_entries:
                sections_dict[resolved_title] = proj_entries

        elif sec_key == "certifications" and structured_data.get("certifications"):
            cert_list = structured_data["certifications"]
            cert_entries = []
            for cert in cert_list:
                name = (cert.get("name") or "").strip()
                if not name:
                    continue
                entry = {"name": name}
                if cert.get("issuer"):
                    entry["summary"] = cert["issuer"].strip()
                date_norm = normalize_rendercv_date(cert.get("issue_date"))
                if date_norm:
                    entry["date"] = date_norm
                cert_entries.append(entry)

            if cert_entries:
                sections_dict[resolved_title] = cert_entries

        elif sec_key == "languages" and structured_data.get("languages"):
            lang_list = structured_data["languages"]
            lang_items = []
            for l in lang_list:
                formatted = format_language_display(l.get("language", ""), l.get("proficiency"), lang=lang)
                if formatted:
                    lang_items.append(formatted)
            if lang_items:
                sections_dict[resolved_title] = [
                    {"label": resolved_title, "details": ", ".join(lang_items)}
                ]

        elif sec_key == "custom_sections" and structured_data.get("custom_sections"):
            for c_sec in structured_data["custom_sections"]:
                c_title = (c_sec.get("title") or resolved_title).strip()
                items = [it.strip().lstrip("-•* ").strip() for it in c_sec.get("items", []) if it and it.strip()]
                if c_title and items:
                    sections_dict[c_title] = items

    cv_dict["sections"] = sections_dict

    # 3. Design options
    design_dict: dict[str, Any] = {
        "theme": theme_name,
        "page": {
            "size": page_size,
        },
        "colors": {
            "section_titles": color_rgb_str,
            "name": color_rgb_str,
        },
    }

    # 4. Locale & settings
    yaml_obj: dict[str, Any] = {
        "cv": cv_dict,
        "design": design_dict,
        "locale": {
            "language": locale_name,
        },
    }

    if output_dir:
        yaml_obj["settings"] = {
            "render_command": {
                "output_folder": output_dir.as_posix(),
            }
        }

    return yaml_obj


def dict_to_yaml_string(data: dict[str, Any]) -> str:
    """Convert a dictionary to clean YAML string."""
    from io import StringIO
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    stream = StringIO()
    yaml.dump(data, stream)
    return stream.getvalue()


def render_rendercv_artifacts(
    structured_data: dict[str, Any],
    settings: dict[str, Any] | None = None,
    dest_pdf_path: Path | None = None,
) -> dict[str, Any]:
    """Compile resume via RenderCV Typst engine.

    Returns dictionary containing:
      - 'pdf_path': Path to generated PDF
      - 'png_paths': list of Paths to generated page PNGs
      - 'page_count': total number of pages
      - 'temp_dir': Path to temp directory containing artifacts
    """
    import rendercv.renderer.pdf_png as pp
    import rendercv.renderer.typst as ty
    import rendercv.schema.rendercv_model_builder as mb

    temp_dir = Path(tempfile.mkdtemp(prefix="compust_rcv_"))

    try:
        yaml_dict = build_rendercv_yaml_dict(
            structured_data=structured_data,
            settings=settings,
            output_dir=temp_dir,
        )
        yaml_text = dict_to_yaml_string(yaml_dict)

        _, model = mb.build_rendercv_dictionary_and_model(yaml_text)
        typst_path = ty.generate_typst(model)
        if not typst_path or not typst_path.exists():
            raise RuntimeError("RenderCV Typst source generation failed.")

        pdf_path = pp.generate_pdf(model, typst_path)
        if not pdf_path or not pdf_path.exists() or pdf_path.stat().st_size == 0:
            raise RuntimeError("RenderCV PDF compilation failed or resulted in an empty file.")

        png_paths = pp.generate_png(model, typst_path) or []

        # If a destination PDF path was requested, copy the compiled PDF
        final_pdf_path = pdf_path
        if dest_pdf_path:
            dest_pdf_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pdf_path, dest_pdf_path)
            final_pdf_path = dest_pdf_path

        return {
            "pdf_path": final_pdf_path,
            "png_paths": [Path(p) for p in png_paths if Path(p).exists()],
            "page_count": len(png_paths) if png_paths else 1,
            "temp_dir": temp_dir,
        }
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise exc


def render_rendercv_preview_payload(
    structured_data: dict[str, Any],
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate high-resolution per-page PNG images for live preview."""
    artifacts = render_rendercv_artifacts(
        structured_data=structured_data,
        settings=settings,
    )
    temp_dir = artifacts.get("temp_dir")
    png_paths = artifacts.get("png_paths", [])

    base64_pages: list[str] = []
    try:
        for p in png_paths:
            with open(p, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("ascii")
                base64_pages.append(f"data:image/png;base64,{encoded}")

        theme_name = (settings or {}).get("template", "modern")
        return {
            "pages": base64_pages,
            "page_count": len(base64_pages) if base64_pages else 1,
            "engine": "rendercv-typst",
            "theme": theme_name,
        }
    finally:
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
