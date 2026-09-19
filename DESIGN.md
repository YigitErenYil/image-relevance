# Design Doc — AI Image Understanding & Content Matching Engine

## Problem
Given a library of images and a set of blog posts, automatically tag each
image (vision model), find the best-matching image for each post (semantic
similarity), and — critically — refuse to suggest a wrong match instead of
guessing. A fox post should never get a wolf image.

## Non-goal
No frontend build (API + a simple table is enough). No comparing multiple
vision/embedding models — one of each is enough. No massive corpus — 40-50
images across 5 categories.

## Corpus
Animals: fox, wolf, dog, bear, deer (~10 images each, ~50 total), sourced
from Unsplash (free license) via `scripts/fetch_images.py`. Each image's
*search category* (what we searched for) is recorded as a ground-truth label
in `data/images/manifest.json` — used later to sanity-check the vision
model's own tagging and to build the eval set, but never fed to the matching
pipeline itself (that would defeat the point of testing real understanding).

## Data model

```
images
  id (pk)
  filename                -- local path, e.g. data/images/fox/03.jpg
  source_category         -- ground truth from manifest (fox/wolf/dog/bear/deer)
  subject                 -- from vision model, e.g. "red fox"
  category                -- from vision model, e.g. "animal"
  attributes              -- JSON array, e.g. ["orange fur","wild","forest"]
  caption                 -- from vision model
  confidence              -- float 0-1, from vision model
  flagged_low_confidence  -- bool
  processed_at            -- nullable, set once vision job completes

image_embeddings
  id (pk)
  image_id (fk -> images, unique)
  embedding                -- float array (caption embedding)
  created_at

posts
  id (pk)
  title
  content
  created_at

post_embeddings
  id (pk)
  post_id (fk -> posts, unique)
  embedding
  created_at

suggestions
  id (pk)
  post_id (fk -> posts)
  image_id (fk -> images, nullable)   -- null when guard says "no match"
  similarity_score         -- nullable
  guard_verdict            -- 'approved' | 'rejected' | 'no_match'
  explanation               -- human-readable reason
  review_status             -- 'pending' | 'approved' | 'rejected' (human review)
  created_at

processing_jobs
  id (pk)
  job_type                 -- 'vision_tagging' | 'embedding'
  status                    -- 'pending' | 'running' | 'completed' | 'failed'
  total_items
  processed_items
  failed_items
  created_at
  updated_at

cost_log
  id (pk)
  call_type                -- 'vision' | 'embedding'
  reference_id              -- image_id or post_id
  estimated_cost_micros     -- integer, pinned pricing constant per call
  created_at
```

## Image metadata schema (vision output, validated)

```json
{
  "subject": "red fox",
  "category": "animal",
  "attributes": ["orange fur", "wild", "forest"],
  "caption": "A red fox standing in a forest",
  "confidence": 0.94
}
```
Pydantic model. `confidence < 0.6` → `flagged_low_confidence = true`, never
silently trusted, never auto-matched without a warning.

## Matching strategy

1. Embed every image's `caption` (Gemini embeddings, `SEMANTIC_SIMILARITY`
   task type).
2. Embed every post's `title + content`.
3. For a given post, compute cosine similarity against all image embeddings,
   rank descending.
4. Take the top candidate → pass through the mismatch guard.

## The mismatch guard

Combines three signals before approving a suggestion:
1. **Category/subject check** — does the image's vision-extracted `subject`
   share an animal category with what the post is actually about (itself
   extracted from the post via a lightweight subject-extraction step, not
   hardcoded)? A clear mismatch (post about foxes, image tagged "wolf") is
   an automatic reject regardless of embedding similarity — this is what
   catches the fox/wolf near-miss, since a wolf photo can score deceptively
   high on pure caption similarity.
2. **Similarity threshold** — cosine similarity must clear a tuned cutoff
   (set from the labeled eval set in Phase 4, not guessed).
3. **Confidence** — if the image's own vision confidence was flagged low,
   the guard downgrades or rejects even a similarity match.

Guard output is never a bare true/false — always
`{verdict, explanation}`, e.g.
`"Animal category mismatch: expected fox, detected wolf"` or
`"No image cleared the similarity threshold (best: 0.41, cutoff: 0.62)"`.

## API contract (Phase 3/4)

- `POST /batch/tag-images` — kicks off the vision-tagging background job
- `GET /batch/jobs/:id` — job status/progress
- `POST /batch/embed` — embedding job for images + posts
- `GET /posts/:id/images` — ranked suggestions + guard verdict for a post
- `POST /suggestions/:id/review` — approve/reject (human-in-the-loop)
- `GET /costs` — cost log rollup

## Layers
`app/models.py` (data) → `app/services/{vision,embeddings,matching,guard,cost}.py`
(logic) → `app/routers/*.py` (HTTP + Pydantic validation at the boundary).

## Eval plan (Phase 4)
10+ posts, each hand-labeled with the one correct image. Run the pipeline,
compute top-1 precision (share of posts where the top suggestion after the
guard equals the labeled correct image). Number goes in `README.md`.
