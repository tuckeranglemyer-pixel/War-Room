"""
Screenshot ingestion pipeline: GPT-4o Vision analysis and ChromaDB indexing.

Iterates over product screenshot directories, sends each image to GPT-4o for
detailed UX analysis, and upserts the resulting description chunks into the
``pm_tools`` ChromaDB collection for downstream RAG retrieval.
"""

import os
import base64
import chromadb
from openai import OpenAI
from pathlib import Path

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
DATA_DIR = Path(r"C:\Users\griff\Downloads\hackathon-data-toolkit\data-toolkit\data")
CHROMA_PATH = "./chroma_db"

client_openai = OpenAI(api_key=OPENAI_API_KEY)
client_chroma = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client_chroma.get_collection("pm_tools")

VISION_PROMPT = """You are a UX analyst. Describe this screenshot of a project management app in detail:
1. What app is this and what screen/view is shown?
2. What UI elements are visible (sidebar, toolbar, modals, lists, boards, etc.)?
3. What is the user workflow being shown?
4. What are the strengths of this UI design?
5. What are the weaknesses or friction points a user might experience?
6. How does this compare to standard PM tool patterns?
Be specific. Reference exact UI elements, colors, layout choices, and interaction patterns.
Write 3-5 detailed paragraphs. This description will be used as evidence in an adversarial product debate."""

def encode_image(image_path: str) -> str:
    """Read an image file from disk and return its base64-encoded string.

    Args:
        image_path: Absolute or relative path to the image file.

    Returns:
        Base64-encoded UTF-8 string of the raw image bytes.
    """
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def describe_screenshot(image_path: str) -> str:
    """Send a screenshot to GPT-4o Vision and return a detailed UX analysis.

    Encodes the image as base64, constructs a vision message with the standard
    UX analyst prompt, and returns the model's textual description.

    Args:
        image_path: Path to the screenshot file (png, jpg, jpeg, gif, or webp).

    Returns:
        Multi-paragraph UX analysis string from GPT-4o Vision.
    """
    base64_image = encode_image(image_path)
    ext = Path(image_path).suffix.lower()
    media_type = {".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",".gif":"image/gif",".webp":"image/webp"}.get(ext,"image/png")
    response = client_openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role":"user","content":[{"type":"text","text":VISION_PROMPT},{"type":"image_url","image_url":{"url":f"data:{media_type};base64,{base64_image}","detail":"high"}}]}],
        max_tokens=1000,
    )
    return response.choices[0].message.content

def main() -> None:
    """Walk all app screenshot directories and ingest undescribed images into ChromaDB.

    Skips files already present in the collection (keyed by filename metadata).
    Prints a summary of processed, skipped, and errored files on completion.
    """
    screenshot_dirs = sorted(DATA_DIR.glob("*/screenshots"))
    all_images = []
    for ss_dir in screenshot_dirs:
        app_name = ss_dir.parent.name
        for img in sorted(ss_dir.iterdir()):
            if img.suffix.lower() in {".png",".jpg",".jpeg",".gif",".webp"}:
                all_images.append((app_name, img))
    print(f"Found {len(all_images)} screenshots across {len(screenshot_dirs)} apps\n")
    existing = collection.get(where={"source":"screenshot"}, include=["metadatas"])
    existing_files = set()
    if existing and existing["metadatas"]:
        for m in existing["metadatas"]:
            if "filename" in m:
                existing_files.add(m["filename"])
    skipped = 0; processed = 0; errors = 0
    for i, (app_name, img_path) in enumerate(all_images):
        filename = img_path.name
        if filename in existing_files:
            print(f"  [{i+1}/{len(all_images)}] SKIP: {app_name}/{filename}")
            skipped += 1
            continue
        print(f"  [{i+1}/{len(all_images)}] Processing: {app_name}/{filename} ...", end=" ", flush=True)
        try:
            description = describe_screenshot(str(img_path))
            doc_id = f"screenshot_{app_name}_{filename}"
            chunk_text = f"[Screenshot: {app_name} - {filename}]\n\n{description}"
            collection.add(documents=[chunk_text], metadatas=[{"app":app_name,"source":"screenshot","type":"ui_screenshot","filename":filename}], ids=[doc_id])
            processed += 1
            print("OK")
        except Exception as e:
            errors += 1
            print(f"ERROR: {e}")
    print(f"\n{'='*50}")
    print(f"Done. Processed: {processed} | Skipped: {skipped} | Errors: {errors}")
    print(f"Collection now has {collection.count()} total chunks.")

if __name__ == "__main__":
    main()