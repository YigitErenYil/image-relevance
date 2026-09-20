"""
Creates sample blog posts via the running API, spanning all 5 animal
categories, including a couple that use scientific names instead of common
names (to test that embeddings match "Vulpes vulpes" to a fox image via
meaning, not exact words, per the design doc's semantic matching test).

Usage (from the host machine, requests already in requirements.txt):
    python scripts/seed_posts.py
"""
import os
import requests

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

POSTS = [
    {
        "title": "The secret life of the red fox",
        "content": "Red foxes are among the most adaptable wild canids, "
                    "thriving from remote forests to city parks. Their "
                    "bushy tails and sharp features make them instantly "
                    "recognizable across the northern hemisphere.",
    },
    {
        "title": "Vulpes vulpes: a species profile",
        "content": "Vulpes vulpes, the scientific name for the common fox, "
                    "is the largest of the true foxes. This species profile "
                    "covers its range, diet, and reproductive behavior.",
    },
    {
        "title": "Understanding wolf pack dynamics",
        "content": "Wolves live and hunt in tightly organized packs with a "
                    "clear social hierarchy. This post explores how gray "
                    "wolves communicate and cooperate to bring down large prey.",
    },
    {
        "title": "Canis lupus: apex predator of the north",
        "content": "Canis lupus, commonly known as the gray wolf, once "
                    "ranged across most of the northern hemisphere. We look "
                    "at its comeback in parts of Europe and North America.",
    },
    {
        "title": "Why golden retrievers make great family dogs",
        "content": "Golden retrievers are famous for their friendly, "
                    "patient temperament. This guide covers what makes this "
                    "dog breed such a popular choice for families.",
    },
    {
        "title": "A beginner's guide to dog training",
        "content": "Training a new dog takes patience and consistency. "
                    "Here are the fundamentals every dog owner should know, "
                    "from basic commands to leash manners.",
    },
    {
        "title": "Brown bears preparing for hibernation",
        "content": "As autumn arrives, brown bears enter a period of "
                    "intense feeding called hyperphagia, packing on fat "
                    "reserves before winter denning begins.",
    },
    {
        "title": "Ursus arctos across three continents",
        "content": "Ursus arctos, the brown bear, has one of the widest "
                    "ranges of any large land mammal, found across North "
                    "America, Europe, and Asia in various subspecies.",
    },
    {
        "title": "Deer rutting season explained",
        "content": "Every autumn, male deer compete for mates during the "
                    "rutting season, marked by antler clashes and loud "
                    "vocalizations echoing through the forest.",
    },
    {
        "title": "How deer antlers grow and shed each year",
        "content": "Unlike horns, deer antlers are shed and regrown "
                    "annually. This remarkable biological process is fueled "
                    "by one of the fastest-growing tissues in nature.",
    },
    {
        "title": "Comparing fox and wolf hunting strategies",
        "content": "While both are wild canids, foxes hunt alone for small "
                    "prey like rodents, while wolves rely on pack "
                    "coordination to take down much larger animals.",
    },
    {
        "title": "Weekly newsletter: garden tips for autumn",
        "content": "This week we cover composting, bulb planting, and how "
                    "to protect tender perennials before the first frost "
                    "hits your garden.",
    },
]

created = []
for post in POSTS:
    resp = requests.post(f"{API_BASE}/posts", json=post)
    resp.raise_for_status()
    data = resp.json()
    created.append(data)
    print(f"  created: {data['id']}  {post['title']}")

print(f"\nDone. Created {len(created)} posts.")
print("Now run: curl -X POST http://localhost:8000/batch/embed")
