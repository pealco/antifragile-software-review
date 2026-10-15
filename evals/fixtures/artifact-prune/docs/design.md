# Design notes

## Storage layout

Each run is stored as one gzipped tarball, `s3://<bucket>/<prefix>/<run>.tar.gz`, whose top-level
directory is the run name. We archive whole runs rather than syncing files because a run has tens
of thousands of small trial files, and per-object requests made the first version of this tool
slow and expensive.

Pushing a run again replaces its archive with the current contents of the run directory. Runs grow
when they are resumed, so the newest push is the most complete copy.

Uploads go through `upload_file`, which switches to multipart above 64 MB, and every part is sent
with a SHA-256 checksum that S3 verifies. After the upload, `push` compares the object's size with
the local tarball.

## Local runs

`runs_dir` in `runstash.toml` holds one directory per run. A directory counts as a run if it has a
`run.json`. Anything else in `runs_dir` (judge outputs, notebooks, plots) is ignored by every
command.

## Configuration

`runstash.toml` is committed with the project. `~/.config/runstash/config.toml` holds per-user
settings and uses the same keys.
