# Database migrations

Revision `20260822_0001` creates the reviewed foundation schema and enables pgvector. The
embedding column is literally `vector(384)`; no runtime setting can alter migration shape.

Normal setup is forward-only:

```sh
uv run --project apps/api evalgate-db seed-empty
```

The destructive reset exists only because all current database state is reproducible. It is
rejected in `public` mode, rejected for non-loopback database hosts, restricted to a database
named `evalgate` or prefixed `evalgate_test_`, and requires an explicit acknowledgement:

```sh
uv run --project apps/api evalgate-db reset --confirm-destroy-local-data
```

Application rollback uses the previous immutable image. Alembic downgrade is not a normal
deployment rollback; it is used only by the explicit local/CI reset path and integration tests.
If a forward upgrade fails, preserve the error, correct its cause, and rerun `seed-empty`; the
transactional revision does not record the head until it completes. Use the confirmed reset only
for a disposable local/CI database whose contents are known to be reproducible.
