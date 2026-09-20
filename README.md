# AI Image Understanding & Content Matching Engine

Given a library of images and a set of blog posts, this service tags every
image with a vision model, finds the best-matching image for each post via
semantic similarity, and — the actual point of the project — refuses to
suggest a wrong match instead of guessing. A fox post gets a fox image; a
similar-looking wolf photo is rejected with an explanation, not silently
served.

## What it does

1. **Vision tagging** — every image is run through a local vision model
   (Ollama/llava), producing schema-validated `{subject, category,
   attributes, caption, confidence}`. Low-confidence and malformed
   responses are flagged/retried, never silently trusted.
2. **Semantic matching** — image captions and post text are embedded
   (Ollama/nomic-embed-text) and ranked by cosine similarity, so "red fox",
   "Vulpes vulpes", and "wild fox species" all match despite different words.
3. **The mismatch guard** — combines a category/subject check, a tuned
   similarity threshold, and the vision model's own confidence flag to
   decide whether a suggestion is trustworthy. A verdict is always
   explained, never a bare yes/no.
4. **Background processing** — tagging and embedding both run as
   background batch jobs, off the request path, with retries and progress
   tracking.
5. **Review API** — inspect every suggestion and its guard verdict/reason;
   approve or reject any of them.

## Architecture

```
Images --(batch job)--> Vision Model (Ollama/llava)
  --> {subject, category, attributes, caption, confidence}
  --> validated (schema + placeholder-echo check) --> images table
  --> embed(caption) --> image_embeddings

Posts --> POST /posts --> embed(title+content) --> post_embeddings

GET /posts/:id/images
  --> Similarity Ranking (image_embeddings x post_embedding, cosine)
  --> Mismatch Guard:
        1. category/subject check (post text vs image subject)
        2. vision confidence check
        3. similarity threshold
  --> {verdict: approved | rejected | no_match, explanation}
  --> persisted as a Suggestion row

GET /suggestions            -- inspect every suggestion + why
POST /suggestions/:id/review -- human approve/reject
```

Layers: `app/models.py` (data) -> `app/services/{vision,embeddings,matching,
guard,batch,cost}.py` (logic) -> `app/routers/*.py` (HTTP + Pydantic
validation at the boundary).

## Setup & run (clean machine)

Requires Docker Desktop.

```bash
git clone <this-repo-url>
cd flyrank-capstone-imagerelevance   # or whatever you named the repo
cp .env.example .env
# fill in UNSPLASH_ACCESS_KEY and GEMINI_API_KEY in .env if you want to
# re-fetch the corpus from scratch (GEMINI_API_KEY is currently unused —
# see "Why Ollama, not Gemini" below)

docker compose up --build
```

In a second terminal, pull the local models (one-time, ~5GB total):

```bash
docker compose exec ollama ollama pull llava
docker compose exec ollama ollama pull nomic-embed-text
```

Fetch the image corpus and load it into the database:

```bash
python scripts/fetch_images.py          # downloads ~50 images from Unsplash
docker compose exec api python seed_images.py
```

Run the pipeline:

```bash
curl -X POST http://localhost:8000/batch/tag-images     # vision tagging
# poll: curl http://localhost:8000/batch/jobs/<job_id>

python scripts/seed_posts.py             # creates 12 sample blog posts
curl -X POST http://localhost:8000/batch/embed           # embeds images + posts
# poll the same way
```

Try it:

```bash
curl http://localhost:8000/posts
curl http://localhost:8000/posts/<post_id>/images
```

Run the eval:

```bash
python scripts/run_eval.py
```

## Eval results

10 hand-labeled posts (2 per category: fox, wolf, dog, bear, deer), each
labeled with a canonical correct image (`<category>/00.jpg`):

- **Category-level top-1 precision: 100% (10/10)**
- **Exact-image top-1 precision: 20% (2/10)**

These two numbers need explaining, and the gap between them is itself a
real finding, not a bug: the eval posts are generic topic posts (e.g. "Why
golden retrievers make great family dogs"), not posts tied to one specific
photo. Any image in the correct category is a genuinely correct match for
a post like that — which is exactly what the system delivered, 10 times
out of 10. Exact-image precision only credits the single, arbitrarily
chosen `00.jpg` per category, even though every other same-category image
in the corpus is an equally valid answer — it's reported for transparency,
not as the headline quality number. **Category-level precision is the
metric that reflects real system quality here.**

Two additional posts were checked qualitatively (not included in the
precision count): a "fox vs wolf" comparison post, which the system
correctly routed to a fox image (a legitimately ambiguous case scored
sensibly); and an unrelated gardening post, which correctly returned
`no_match` rather than forcing an irrelevant animal photo on it.

The guard was also directly probed by forcing a wolf image as a candidate
for a fox post — see `EVIDENCE.md` for the full transcript. It was
rejected with `"Animal category mismatch: expected fox, detected wolf"`,
even though its cosine similarity (0.58) cleared the similarity threshold
(0.55) on its own — proving the category check catches exactly the
near-miss case the whole guard exists for.

## Why Ollama, not Gemini

The original design used Gemini (per the brief's suggested free-tier
stack). During Phase 2, Gemini's free-tier request-per-day quota was cut
to as low as 20/day across every Flash model tried (`gemini-2.5-flash`,
`gemini-3.6-flash`, `gemini-2.5-flash-lite` — the latter two also got
deprecated for new users mid-build). A Google Developer Relations reply on
the official forum confirmed this was a deliberate, sitewide free-tier
reduction, not a bug on our end. 50 images could not be processed in a
single day under those limits, so the vision AND embedding pipelines were
both moved to local Ollama models (llava, nomic-embed-text) — no rate
limits, no API key, fully reproducible by anyone who clones this repo.
Full details and the forum citation are in `BUILDLOG.md`.

## Known limitations

- CPU-only local inference (no GPU passthrough configured) — the full
  50-image tagging batch takes several minutes; fine for this capstone's
  scope, would need GPU or a hosted API for a larger corpus.
- The mismatch guard's category detection is a transparent keyword map
  over our fixed 5-category domain (see `app/config.py:CATEGORY_KEYWORDS`)
  — appropriate for this capstone's bounded scope, not a general-purpose
  subject-extraction solution.
- Exact-image eval precision (20%) is a known artifact of the labeling
  scheme, not a matching-quality problem — see "Eval results" above.
- No test suite (optional per the brief); verification is via the
  transcripts in `EVIDENCE.md` and the eval script's own output.
