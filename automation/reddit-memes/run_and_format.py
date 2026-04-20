#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

BASE = Path('/data/.openclaw/workspace')
TMP = BASE / 'tmp'
SCRIPT = BASE / 'automation' / 'reddit-memes' / 'reddit_memegen.py'


def main():
    proc = subprocess.run(
        ['python3', str(SCRIPT), str(TMP)],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(proc.stdout)
    top = data['topPost']
    meme = data['meme']
    lines = [
        'Reddit AI meme test 😼',
        '',
        f"🔥 Topic: {top['title']}",
        f"📍 Subreddit: r/{top['subreddit']}",
        f"📈 Score: {top['score']} · 💬 {top['comments']} comments",
        f"🔗 {top['url']}",
        '',
        f"🧠 Template: {meme['template']['name']}",
        'A imagem segue em anexo.',
    ]
    print(json.dumps({
        'message': '\n'.join(lines),
        'imagePath': meme['imagePath'],
        'meta': data,
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
