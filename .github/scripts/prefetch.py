#!/usr/bin/env python3
"""Prefetch external sources - runs on GitHub Actions (outside GFW)."""
import json, urllib.request, re, ssl
from html import unescape
from datetime import datetime
import os

ssl_ctx = ssl.create_default_context()
ua = 'Mozilla/5.0 (compatible; HermesBot/1.0)'

def clean(text):
    if not text: return ''
    text = re.sub(r'<[^>]+>', '', text)
    text = unescape(text)
    return re.sub(r'\s+', ' ', text).strip()[:500]

def http_get(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': ua})
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as r:
            return r.status, r.read().decode('utf-8', 'replace')
    except Exception as e:
        return 0, str(e)

results = {'timestamp': datetime.utcnow().isoformat(), 'sources': {}}

# HuggingFace Blog
print('Fetching HuggingFace Blog...')
status, html = http_get('https://huggingface.co/blog')
articles = []
if status == 200:
    links = re.findall(r'<a[^>]*href="(/blog/[^"]+)"[^>]*>.*?<h2[^>]*>(.*?)</h2>', html, re.DOTALL)
    for link, title in links[:8]:
        t = clean(title)
        if t: articles.append({'title': t, 'url': f'https://huggingface.co{link}'})
results['sources']['huggingface'] = articles
print(f'  Got {len(articles)} articles')

# Hacker News AI
print('Fetching Hacker News...')
status, body = http_get('https://hn.algolia.com/api/v1/search?query=AI+artificial+intelligence+machine+learning&tags=story&hitsPerPage=10&numericFilters=points>50')
hn_items = []
if status == 200:
    data = json.loads(body)
    for hit in data.get('hits', [])[:10]:
        hn_items.append({
            'title': clean(hit.get('title','')),
            'url': hit.get('url') or f"https://news.ycombinator.com/item?id={hit.get('objectID','')}",
            'points': hit.get('points', 0)
        })
results['sources']['hackernews'] = hn_items
print(f'  Got {len(hn_items)} items')

# TechCrunch AI RSS
print('Fetching TechCrunch...')
status, body = http_get('https://techcrunch.com/feed/')
tc_items = []
if status == 200:
    items = re.findall(r'<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>.*?<pubDate>(.*?)</pubDate>.*?<description>(.*?)</description>', body, re.DOTALL)
    for title, link, pubdate, desc in items[:6]:
        t = clean(title)
        if t and ('AI' in t or 'artificial' in t.lower()):
            tc_items.append({
                'title': t,
                'url': clean(link),
                'published': clean(pubdate),
                'summary': clean(desc)[:300]
            })
results['sources']['techcrunch'] = tc_items
print(f'  Got {len(tc_items)} items')

# Save
os.makedirs('prefetch_data', exist_ok=True)
ts = datetime.utcnow().strftime('%Y-%m-%d_%H')
path = f'prefetch_data/{ts}.json'
with open(path, 'w') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f'\nSaved to {path}')
