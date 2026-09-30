import json
import re

from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from APP import config
from services.exporters import save_pdf
from services.gemini_pro import generate_outline
from services.image_generator import generate_image
from services.layout_builder import build_comic_layout

router = APIRouter()

templates = Jinja2Templates(directory=str(config.TEMPLATES_DIR))


def _extract_json_payload(text: str):
    if not text:
        return []

    text = text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", text, flags=re.S)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return []
        return []


def _clean_story_prompt(story_prompt: str, character_name: str) -> str:
    cleaned = re.sub(rf"(?i)\b{re.escape(character_name)}\b", "", story_prompt or "")
    cleaned = re.sub(r"(?i)\b(a|an|the)\b", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:;.,")
    cleaned = cleaned.replace(" explores ", " exploration through ")
    cleaned = cleaned.replace(" explore ", " exploration through ")
    cleaned = cleaned.replace(" seeks ", " search for ")
    cleaned = cleaned.replace(" finds ", " discovery of ")
    cleaned = cleaned.replace(" enters ", " journey into ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:;.,")
    if not cleaned:
        cleaned = "a thrilling adventure"
    return cleaned


async def _generate_comic_layout(story_prompt: str, character_name: str, genre: str, art_style: str):
    setting = f"{genre} world"
    tone = "dramatic and cinematic"

    outline = generate_outline(story_prompt, character_name, setting, tone, art_style)
    outline = _extract_json_payload(outline) if isinstance(outline, str) else outline

    if not isinstance(outline, list) or not outline:
        outline = [
            {
                "panel_number": i,
                "title": f"Panel {i}",
                "scene_description": f"{character_name} continues the {genre.lower()} adventure.",
                "image_prompt": f"{character_name} in a {genre.lower()} scene, {art_style.lower()} art, cinematic lighting"
            }
            for i in range(1, 6)
        ]

    image_paths = []
    for idx, panel in enumerate(outline[: config.NUM_PANELS], start=1):
        prompt = panel.get("image_prompt") or (
            f"{character_name} in a {genre.lower()} scene, {art_style.lower()} art, cinematic composition, panel {idx}"
        )
        filename = f"panel_{idx}.png"
        image_path = generate_image(prompt, filename=filename)
        image_paths.append(image_path)

    full_story = "\n\n".join(
        (
            f"Panel {idx}: {panel.get('title', f'Panel {idx}') }\n"
            f"{panel.get('scene_description', '')}\n"
            f"{panel.get('image_prompt', '')}"
        )
        for idx, panel in enumerate(outline[: config.NUM_PANELS], start=1)
    )

    layout = build_comic_layout(image_paths, full_story, outline[: config.NUM_PANELS])
    pdf_path = save_pdf(layout)

    return layout, pdf_path


@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@router.post("/generate")
async def generate_comic(
    story_prompt: str = Form(...),
    character_name: str = Form(...),
    genre: str = Form(...),
    art_style: str = Form(...),
):
    story_prompt = (story_prompt or "").strip()
    character_name = (character_name or "").strip()
    genre = (genre or "Fantasy").strip()
    art_style = (art_style or "Anime").strip()

    if not story_prompt or not character_name:
        raise HTTPException(status_code=400, detail="Story idea and character name are required.")

    try:
        layout, pdf_path = await _generate_comic_layout(story_prompt, character_name, genre, art_style)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Comic generation failed: {exc}") from exc

    cleaned_prompt = _clean_story_prompt(story_prompt, character_name)
    story = (
        f"{character_name} steps into a {genre.lower()} adventure shaped by {cleaned_prompt}. "
        f"With a {art_style.lower()} visual sensibility, the story follows the hero through danger, "
        f"discovery, and a final turning point that changes their world forever."
    )

    return JSONResponse(
        content={
            "story": story,
            "character": character_name,
            "genre": genre,
            "art_style": art_style,
            "layout": layout,
            "pdf_path": pdf_path,
        }
    )


@router.get("/preview")
async def preview(request: Request):
    sample_layout = [
        {
            "panel": 1,
            "title": "Moonlit Forest",
            "scene_description": "A lone fox slips through a glade of silver trees while a distant glow hints at the path ahead.",
            "text": "The forest breathed in whispers as the hero took the first fearless step toward the hidden valley.",
            "image_path": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1200&q=80",
        },
        {
            "panel": 2,
            "title": "The River's Secret",
            "scene_description": "An old stone bridge reflectively shimmers beneath drifting lantern light.",
            "text": "A sudden ripple revealed the trail to a place no map could ever name.",
            "image_path": "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?auto=format&fit=crop&w=900&q=80",
        },
        {
            "panel": 3,
            "title": "Hidden Valley",
            "scene_description": "The valley opens like a dream—green, glowing, and full of impossible stories.",
            "text": "At the center of the valley, the legend shimmered into view just as the sky turned gold.",
            "image_path": "https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=900&q=80",
        },
        {
            "panel": 4,
            "title": "The Turning Point",
            "scene_description": "The hero now stands beneath a broken star, choosing courage over fear.",
            "text": "The final choice was not easy, but it was the one that changed the world forever.",
            "image_path": "https://images.unsplash.com/photo-1511497584788-876760111969?auto=format&fit=crop&w=900&q=80",
        },
    ]

    return templates.TemplateResponse(
        request=request,
        name="comic_preview.html",
        context={"layout": sample_layout, "pdf_path": ""},
    )


@router.get("/export-success")
async def export_success(request: Request, pdf_path: str = ""):
    return templates.TemplateResponse(
        request=request,
        name="export_success.html",
        context={"pdf_path": pdf_path},
    )