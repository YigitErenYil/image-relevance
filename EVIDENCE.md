# Evidence

One proof per requirement box in the capstone brief (Section 6). All
transcripts below are real output from this running system.

## AI processing

**Vision model produces structured output validated against a schema;
invalid responses never trusted.**

Real bug caught and fixed by validation: 3 of 50 images initially came
back with the vision model echoing the prompt's own instructional text
instead of describing the image —

```
"subject": "the specific thing shown, e.g. dog"
"attributes": ["3-5 short descriptive tags, e.g. forest, misty, woodland"]
```

Syntactically valid JSON, so a schema-shape check alone didn't catch it.
Added a Pydantic validator that rejects known placeholder phrasing,
forcing a retry with a rewritten prompt. After reprocessing:

```
dog/08.jpg   -> subject: "dog", caption: "An image of a dog with long fur,
                displaying a playful behavior"
deer/03.jpg  -> attributes: ["antlers","eyes","forest"]
deer/09.jpg  -> caption: "Two deer standing on a grassy hillside
                overlooking a mountain range."
```

Full account of the fix in `BUILDLOG.md`.

**Low-confidence classifications are flagged instead of accepted.**

```
$ curl http://localhost:8000/images
...
{"filename":"data/images/dog/08.jpg", "subject":"dog", "category":"animal",
 "confidence":0.4, "flagged_low_confidence":true, ...}
```
(from the original tagging pass, before the placeholder-echo fix — a
genuinely blurry image, correctly flagged rather than guessed on).

**Images are processed through a batch background job with retries.**

```
$ curl -X POST http://localhost:8000/batch/tag-images
{"job_id":"...","message":"Tagging job started"}

$ curl http://localhost:8000/batch/jobs/<id>
{"status":"completed","total_items":50,"processed_items":50,"failed_items":0}
```
`app/services/vision.py:classify_image` retries each image up to 3 times
(schema validation failure OR HTTP error both count as a failure and
trigger a retry) before the batch job counts it as failed and moves on.

**Vision and embedding costs are tracked per call.**

```
$ curl http://localhost:8000/costs
{"by_call_type":[{"call_type":"vision","call_count":50,...},
                  {"call_type":"embedding","call_count":62,...}],
 "total_estimated_cost_micros": ...}
```
Every tagging and embedding call writes a `cost_log` row (see
`app/services/cost.py`), attributed to the specific image/post. Vision and
embeddings run on local Ollama, so actual spend is $0 — but the
per-call log line still exists, which is what "tracked" requires.

## Matching system

**Image and post embeddings are stored; posts return ranked image
suggestions.**

```
$ curl http://localhost:8000/posts/<fox-post-id>/images
{"image_filename":"data/images/fox/05.jpg",
 "similarity_score":0.7543687803935321,
 "guard_verdict":"approved",
 "explanation":"Category match (fox) and similarity 0.75 clears the 0.55 threshold."}
```

**Semantic matching works for equivalent concepts — "red fox" matches
"Vulpes vulpes".**

The post titled "Vulpes vulpes: a species profile" (no English word "fox"
anywhere in the title) correctly matched a fox image:
```
$ curl http://localhost:8000/posts/<vulpes-post-id>/images
{"image_filename":"data/images/fox/04.jpg", "guard_verdict":"approved", ...}
```

## Safety layer (the mismatch guard)

**The guard rejects incorrect recommendations — the wolf-on-a-fox-post
scenario provably fails.**

```
$ curl -X POST ".../posts/<fox-post-id>/images/force-check?image_filename=data/images/wolf/00.jpg"
{"image_id":null,
 "similarity_score":0.5775592004549375,
 "guard_verdict":"rejected",
 "explanation":"Animal category mismatch: expected fox, detected wolf (image subject: 'gray wolf')"}
```
Note the similarity score (0.58) *clears* the 0.55 threshold on its own —
a pure-similarity system would have recommended this wolf photo for the
fox post. The category check is what catches it.

**Rejections include a human-readable explanation.** — every example
above includes one; the guard (`app/services/guard.py:evaluate_match`)
never returns a bare verdict.

**When no image clears the bar, the system answers "no confident match"
with reasons.**

```
$ curl http://localhost:8000/posts/<garden-post-id>/images
{"image_id":null, "guard_verdict":"no_match",
 "explanation":"No image cleared the similarity threshold (best: 0.52, cutoff: 0.55)."}
```

## Backend

**Database models for images, tags, embeddings, posts, suggestions,
approvals/rejections — with the required indexes.**

`app/models.py`: `images`, `image_embeddings` (unique FK on `image_id`),
`posts`, `post_embeddings` (unique FK on `post_id`), `suggestions`,
`processing_jobs`, `cost_log`. `usage_events`-style uniqueness constraints
are used where retried writes must collapse to one row (`image_embeddings.
image_id`, `post_embeddings.post_id`).

**API endpoints validated; the review workflow (approve / reject / inspect
why) exists.**

```
$ curl http://localhost:8000/suggestions
[{"id":"...", "post_title":"The secret life of the red fox",
  "image_filename":"data/images/fox/05.jpg", "guard_verdict":"approved",
  "review_status":"pending", ...}, ...]

$ curl -X POST http://localhost:8000/suggestions/<id>/review -d '{"review_status":"approved"}'
{"review_status":"approved", ...}
```
Pydantic validation at the boundary rejects a bad `review_status` (must be
`approved`/`rejected`) with a clean 422, never a 500.

## Quality & documentation

**A small labeled evaluation dataset measures top-1 precision — the
number is in the README.**

```
$ python scripts/run_eval.py
=== Category-level top-1 precision: 10/10 = 100.00% ===
=== Exact-image top-1 precision:    2/10 = 20.00% ===
```
Full explanation of why both numbers are reported (and which one reflects
real system quality) is in `README.md` under "Eval results".

**README with architecture explanation and diagram; the required files
from Section 11 present.** — `README.md`, `capstone.yaml`, `EVIDENCE.md`
(this file), `BUILDLOG.md`, `.env.example` are all in the repo root.
