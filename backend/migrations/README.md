Schema v2: users, audit, datasets (immutable write sequence plus resumable batch lifecycle), dataset_segments (per-upload receipt), configs (bounded LSM parameters), trials (immutable sealed snapshot and JSON result).

## datasets lifecycle

- `status` is `receiving` while disconnected sites upload segments, `sealed` once the declared sequence is complete. Legacy/complete registrations are born `sealed`.
- `total_count` is the declared operation count (1..2000). `entries` stays empty until sealing; the seal transaction fills it in original sequence order.
- `revision` increments on every newly persisted segment, so clients can tell whether an acknowledged upload already landed.
- `sealed_at` records the one-way transition; no segment may be appended afterwards.

## dataset_segments

Each accepted upload is stored once with `start_seq`, `count`, `operations` (the ordered JSON slice) and `content_hash` (SHA-256 of the canonical slice). Retries of the same content produce no new row; conflicting content rejects the whole segment transaction. Rows are kept even for fully overlapped ranges as upload receipts.

MySQL stores metadata and the operation JSON only. Run `python -m scripts.seed_demo` for create-if-missing and natural-key seed; startup applies the idempotent v1 -> v2 column migration.
