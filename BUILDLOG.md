# Build Log — AI usage

Built with Claude assisting on design and implementation; I ran, tested,
and debugged everything locally and made the product/scope decisions.

## Where AI helped
- Drafted `DESIGN.md` (schema, vision output shape, matching strategy,
  guard design) from the capstone brief.
- Wrote the FastAPI/SQLAlchemy scaffolding: `models.py`, `schemas.py`,
  `services/{vision,embeddings,matching,guard,batch,cost}.py`,
  `routers/*.py`.
- Wrote the corpus-fetch script (`scripts/fetch_images.py`, Unsplash API),
  seed scripts, and the eval script (`scripts/run_eval.py`).

## Where it was wrong / needed a fix
- **Gemini model churn.** Started with `gemini-2.5-flash`; it got
  deprecated for new users mid-build (404). Switched to `gemini-3.6-flash`
  — hit a 20-requests/day free-tier limit, far too low for a 50-image
  batch. Tried `gemini-2.5-flash-lite` (normally 1,000/day) — also
  deprecated for new users by the time we tried it. Confirmed via the
  official Google AI forum that Google had cut free-tier limits sitewide,
  more than 10x, shortly before this: a Google DevRel reply says "There is
  a huge amount of growing demand for 3.0 Pro and Nano Banana Pro so we
  had to shuffle compute there... [the free tier] was not designed to be a
  long term solution to build things on top of."
  (https://discuss.ai.google.dev/t/gemini-rate-limit-20-rpd/111274)
  Decision: moved both vision AND embeddings to local Ollama models
  (llava, nomic-embed-text) — no rate limits, fully reproducible.
- **Windows path separators.** `scripts/fetch_images.py` originally saved
  manifest filenames with `\` on Windows; the Linux container couldn't
  find the files. Fixed the script to always save forward slashes, and
  made the batch/reprocess code tolerant of either direction for the rows
  that were already saved wrong.
- **`docker-compose.yml` missing volume mounts** for `seed_images.py`,
  `scripts/`, and later `seed_images.py` again after a rewrite — same
  class of mistake as the billing capstone; fixed each time it surfaced.
- **`scripts/reprocess.py` couldn't import `app`** — running a script from
  `scripts/` puts that directory (not `/code`) on `sys.path`. Fixed by
  inserting the repo root into `sys.path` explicitly.
- **Placeholder-echo bug (the most interesting one).** After the first
  full tagging run, 3 of 50 images had the vision model literally copying
  the prompt's own instructional text back as its answer (e.g. subject:
  `"the specific thing shown, e.g. dog"`) instead of describing the image.
  Syntactically valid JSON, so schema validation alone didn't catch it.
  Fixed two ways: rewrote the prompt to use an unrelated example (a
  bicycle) with an explicit "don't copy this" instruction, AND added a
  Pydantic validator that rejects known placeholder phrases outright,
  forcing a retry. Reprocessed just the 3 affected images.
- **Eval methodology artifact.** First eval run showed 20% top-1
  precision, which looked like a broken matching system. On inspection,
  every single suggestion was actually category-correct (10/10) — the
  eval script was just crediting only one arbitrarily-chosen "canonical"
  image per category as "correct," when the posts are generic topic posts
  that any same-category image legitimately answers. Fixed the eval
  script to report both category-level precision (100%) and exact-image
  precision (20%), with an explanation of why the gap exists, rather than
  quietly picking whichever number looked better.

## What I decided myself
- Chose Ollama over sticking with Gemini once the rate-limit problem was
  clear, and chose `llava` (over `moondream`) for vision quality on the
  fox/wolf distinction specifically.
- Chose the animal corpus (fox/wolf/dog/bear/deer) and the specific post
  titles/content in `scripts/seed_posts.py`, including which posts use
  scientific names and which is deliberately unrelated (gardening) to
  test the no-match path.
- Chose the `SIMILARITY_THRESHOLD` (0.55) and the keyword-based category
  map in `app/config.py`.
- Ran every command myself (Docker, git, curl tests, the eval script) and
  diagnosed each failure from the actual logs before applying a fix.

I can walk through any 2-3 lines of this codebase and explain what they do
and why.
