#!/usr/bin/env python3
import json
import random
import re
import sys
import textwrap
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SUBREDDITS = [
    "funny",
    "technology",
    "programming",
    "selfhosted",
    "devops",
    "artificial",
    "MachineLearning",
]

AI_PATTERN = re.compile(
    r"\b(ai|artificial intelligence|llm|gpt|openai|anthropic|claude|gemini|copilot|agent|agents|machine learning|ml|neural|model)\b",
    re.I,
)

TEMPLATES = [
    {
        "id": "db",
        "name": "Distracted Boyfriend",
        "top": "ME LOOKING FOR TODAY'S REDDIT AI DRAMA",
        "bottom": "ACTUAL PRODUCTIVE WORK",
    },
    {
        "id": "buzz",
        "name": "Buzz",
        "top": "REDDIT TODAY",
        "bottom": "AI TAKES EVERYONE'S BRAIN CELLS",
    },
    {
        "id": "wonka",
        "name": "Condescending Wonka",
        "top": "OH YOU USED AI",
        "bottom": "PLEASE TELL ME MORE ABOUT YOUR ORIGINAL THOUGHTS",
    },
    {
        "id": "sad-biden",
        "name": "Sad Joe Biden",
        "top": "BUILDING ACTUAL SOFTWARE",
        "bottom": "READING ANOTHER REDDIT AI THREAD",
    },
    {
        "id": "live-tucker-reaction",
        "name": "Tucker Reaction",
        "top": "NEW REDDIT AI HOT TAKE DROPS",
        "bottom": "ME PRETENDING I'M NOT GOING TO CLICK IT",
    },
    {
        "id": "disaster-girl",
        "name": "Disaster Girl",
        "top": "AI NEWS CYCLE",
        "bottom": "TOTALLY HEALTHY AND NORMAL",
    },
]


def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "NyxRedditMemeBot/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def pick_posts():
    candidates = []
    for subreddit in SUBREDDITS:
        data = fetch_json(f"https://www.reddit.com/r/{subreddit}/hot.json?limit=20")
        for child in data["data"]["children"]:
            post = child["data"]
            title = (post.get("title") or "").strip()
            body = (post.get("selftext") or "").strip()
            if not AI_PATTERN.search(title + "\n" + body):
                continue
            score = int(post.get("score") or 0)
            comments = int(post.get("num_comments") or 0)
            candidates.append(
                {
                    "subreddit": subreddit,
                    "title": title,
                    "url": "https://reddit.com" + post.get("permalink", ""),
                    "score": score,
                    "comments": comments,
                    "rank": score + comments * 3,
                }
            )
    candidates.sort(key=lambda x: x["rank"], reverse=True)
    return candidates


def shorten(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def slugify_memegen(text: str) -> str:
    text = text.replace("_", "__").replace("-", "--")
    text = text.replace("?", "~q").replace("&", "~a").replace("%", "~p")
    text = text.replace("#", "~h").replace("/", "~s").replace("\\", "~b")
    text = text.replace("<", "~l").replace(">", "~g")
    text = text.replace("\n", "~n")
    text = text.replace('"', "''")
    text = re.sub(r"\s+", "_", text.strip())
    return urllib.parse.quote(text, safe="_~'-().!*")


def build_caption(post):
    title = post["title"]
    subreddit = post["subreddit"]
    top = random.choice([
        f"R/{subreddit.upper()} TODAY",
        "WHEN REDDIT DISCOVERS AI AGAIN",
        "ANOTHER DAY, ANOTHER AI THREAD",
        "ME OPENING REDDIT FOR 2 MINUTES",
    ])
    bottom = shorten(title.upper(), 90)
    return top, bottom


def build_memegen_url(template_id: str, top: str, bottom: str) -> str:
    return (
        f"https://api.memegen.link/images/{template_id}/"
        f"{slugify_memegen(top)}/{slugify_memegen(bottom)}.png?width=1200"
    )


def download(url: str, dest: Path):
    req = urllib.request.Request(url, headers={"User-Agent": "NyxRedditMemeBot/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        dest.write_bytes(response.read())


def main():
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    out_dir.mkdir(parents=True, exist_ok=True)

    posts = pick_posts()
    if not posts:
        raise SystemExit("No AI-related posts found")

    chosen = posts[0]
    top, bottom = build_caption(chosen)
    template = random.choice(TEMPLATES)
    meme_url = build_memegen_url(template["id"], top, bottom)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    image_path = out_dir / f"reddit-ai-meme-{stamp}.png"
    meta_path = out_dir / f"reddit-ai-meme-{stamp}.json"

    download(meme_url, image_path)

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "topPost": chosen,
        "top10": posts[:10],
        "meme": {
            "template": template,
            "topText": top,
            "bottomText": bottom,
            "url": meme_url,
            "imagePath": str(image_path),
        },
        "telegramMessage": textwrap.dedent(
            f"""
            Reddit AI meme test 😼

            Top topic: {chosen['title']}
            Subreddit: r/{chosen['subreddit']}
            Score: {chosen['score']} · Comments: {chosen['comments']}
            Link: {chosen['url']}

            Meme template: {template['name']}
            Meme URL: {meme_url}
            """
        ).strip(),
    }
    meta_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
