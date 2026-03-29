import os, json, base64, re, time
from pathlib import Path
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
DATA_DIR = Path(r"C:\Users\griff\Downloads\hackathon-data-toolkit\data-toolkit\data")
OUTPUT = Path(r"C:\Users\griff\Downloads\War-Room\screenshot_chunks.json")

PROMPT = """You are a senior UX analyst. Analyze this screenshot with EXTREME specificity.
Cover: 1) Screen ID (app, exact view), 2) Layout & visual hierarchy, 3) Every interactive element,
4) UX friction points (be brutal), 5) UX strengths, 6) Onboarding impact (cognitive load 1-10),
7) Competitor comparison. Write 4-6 detailed paragraphs. Be specific enough to reconstruct the screen."""

chunks = []
if OUTPUT.exists() and OUTPUT.stat().st_size > 10:
    chunks = json.load(open(OUTPUT))
done = {c["metadata"]["filename"] for c in chunks}

images = []
for app_dir in sorted(DATA_DIR.iterdir()):
    ss_dir = app_dir / "screenshots"
    if ss_dir.exists():
        for img in sorted(ss_dir.iterdir()):
            if img.suffix.lower() in {".png",".jpg",".jpeg",".webp",".gif"}:
                images.append((app_dir.name, img))

print(f"Found {len(images)} images across {len(set(a for a,_ in images))} apps")

for i,(app,img) in enumerate(images):
    if img.name in done:
        print(f"[{i+1}/{len(images)}] SKIP {app}/{img.name}")
        continue
    print(f"[{i+1}/{len(images)}] {app}/{img.name}...", end=" ", flush=True)
    try:
        b64 = base64.b64encode(open(img,"rb").read()).decode()
        mt = {"png":"image/png","jpg":"image/jpeg","jpeg":"image/jpeg","webp":"image/webp","gif":"image/gif"}.get(img.suffix.lower().strip("."),"image/png")
        r = client.chat.completions.create(model="gpt-4o", max_tokens=1500, messages=[{"role":"user","content":[
            {"type":"text","text":f"This is {app.upper()}.\n\n{PROMPT}"},
            {"type":"image_url","image_url":{"url":f"data:{mt};base64,{b64}","detail":"high"}}]}])
        desc = r.choices[0].message.content
        chunks.append({"id":f"screenshot_{app}_{img.name}","document":f"[{app.upper()} | ui_screenshot | {img.name}]\n\n{desc}",
            "metadata":{"app":app,"source":"screenshot","type":"ui_screenshot","filename":img.name}})
        json.dump(chunks, open(OUTPUT,"w"), indent=2)
        print("OK")
        time.sleep(0.5)
    except Exception as e:
        print(f"ERROR: {e}")

print(f"\nDone. {len(chunks)} total chunks saved to {OUTPUT}")
