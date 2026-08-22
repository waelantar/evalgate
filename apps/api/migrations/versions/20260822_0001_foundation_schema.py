"""Create the governed PostgreSQL/pgvector foundation schema.

Revision ID: 20260822_0001
Revises:
Create Date: 2026-08-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260822_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Install pgvector and create the reviewed foundation schema."""

    op.execute(
        """
        DO $$
        BEGIN
            IF current_setting('server_version_num')::integer / 10000 <> 18 THEN
                RAISE EXCEPTION 'EvalGate requires PostgreSQL major version 18';
            END IF;
        END
        $$
        """
    )
    op.execute("CREATE EXTENSION IF NOT EXISTS vector VERSION '0.8.5'")
    op.execute(
        """
        DO $$
        BEGIN
            IF (SELECT extversion FROM pg_extension WHERE extname = 'vector') <> '0.8.5' THEN
                RAISE EXCEPTION 'EvalGate requires pgvector extension version 0.8.5';
            END IF;
        END
        $$
        """
    )
    op.execute(
        """
        CREATE TABLE corpus_versions (
            id uuid PRIMARY KEY,
            corpus_key text NOT NULL,
            version text NOT NULL,
            manifest_sha256 text NOT NULL,
            created_at timestamptz NOT NULL,
            CONSTRAINT uq_corpus_versions_key_version UNIQUE (corpus_key, version),
            CONSTRAINT ck_corpus_versions_key_nonempty
                CHECK (length(btrim(corpus_key)) > 0),
            CONSTRAINT ck_corpus_versions_version_nonempty
                CHECK (length(btrim(version)) > 0),
            CONSTRAINT ck_corpus_versions_manifest_sha256
                CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$')
        )
        """
    )
    op.execute(
        """
        CREATE TABLE index_versions (
            id uuid PRIMARY KEY,
            corpus_version_id uuid NOT NULL
                REFERENCES corpus_versions (id) ON DELETE RESTRICT,
            index_key text NOT NULL,
            chunking_version text NOT NULL,
            chunking_policy_sha256 text NOT NULL,
            lexical_config_sha256 text NOT NULL,
            embedding_model text NOT NULL,
            embedding_revision text NOT NULL,
            embedding_checksum text NOT NULL,
            embedding_dimension integer NOT NULL,
            created_at timestamptz NOT NULL,
            CONSTRAINT uq_index_versions_index_key UNIQUE (index_key),
            CONSTRAINT uq_index_versions_id_corpus
                UNIQUE (id, corpus_version_id),
            CONSTRAINT ck_index_versions_index_key_nonempty
                CHECK (length(btrim(index_key)) > 0),
            CONSTRAINT ck_index_versions_chunking_version_nonempty
                CHECK (length(btrim(chunking_version)) > 0),
            CONSTRAINT ck_index_versions_chunking_policy_sha256
                CHECK (chunking_policy_sha256 ~ '^[0-9a-f]{64}$'),
            CONSTRAINT ck_index_versions_lexical_config_sha256
                CHECK (lexical_config_sha256 ~ '^[0-9a-f]{64}$'),
            CONSTRAINT ck_index_versions_embedding_model_nonempty
                CHECK (length(btrim(embedding_model)) > 0),
            CONSTRAINT ck_index_versions_embedding_revision_nonempty
                CHECK (length(btrim(embedding_revision)) > 0),
            CONSTRAINT ck_index_versions_embedding_checksum
                CHECK (embedding_checksum ~ '^[0-9a-f]{64}$'),
            CONSTRAINT ck_index_versions_embedding_dimension_384
                CHECK (embedding_dimension = 384)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE documents (
            id uuid PRIMARY KEY,
            corpus_version_id uuid NOT NULL
                REFERENCES corpus_versions (id) ON DELETE RESTRICT,
            source_key text NOT NULL,
            title text NOT NULL,
            license_id text NOT NULL,
            content_sha256 text NOT NULL,
            metadata jsonb NOT NULL,
            CONSTRAINT uq_documents_corpus_source
                UNIQUE (corpus_version_id, source_key),
            CONSTRAINT uq_documents_id_corpus
                UNIQUE (id, corpus_version_id),
            CONSTRAINT ck_documents_source_key_nonempty
                CHECK (length(btrim(source_key)) > 0),
            CONSTRAINT ck_documents_title_nonempty
                CHECK (length(btrim(title)) > 0),
            CONSTRAINT ck_documents_license_id_nonempty
                CHECK (length(btrim(license_id)) > 0),
            CONSTRAINT ck_documents_content_sha256
                CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
            CONSTRAINT ck_documents_metadata_object
                CHECK (jsonb_typeof(metadata) = 'object')
        )
        """
    )
    op.execute(
        """
        CREATE TABLE chunks (
            id uuid PRIMARY KEY,
            corpus_version_id uuid NOT NULL,
            index_version_id uuid NOT NULL,
            document_id uuid NOT NULL,
            ordinal integer NOT NULL,
            section_key text NOT NULL,
            source_start integer NOT NULL,
            source_end integer NOT NULL,
            content text NOT NULL,
            content_sha256 text NOT NULL,
            token_count integer NOT NULL,
            search_vector tsvector NOT NULL,
            embedding_384 vector(384) NOT NULL,
            CONSTRAINT fk_chunks_index_corpus
                FOREIGN KEY (index_version_id, corpus_version_id)
                REFERENCES index_versions (id, corpus_version_id) ON DELETE RESTRICT,
            CONSTRAINT fk_chunks_document_corpus
                FOREIGN KEY (document_id, corpus_version_id)
                REFERENCES documents (id, corpus_version_id) ON DELETE RESTRICT,
            CONSTRAINT uq_chunks_index_document_ordinal
                UNIQUE (index_version_id, document_id, ordinal),
            CONSTRAINT ck_chunks_ordinal_nonnegative CHECK (ordinal >= 0),
            CONSTRAINT ck_chunks_section_key_nonempty
                CHECK (length(btrim(section_key)) > 0),
            CONSTRAINT ck_chunks_source_offsets
                CHECK (source_start >= 0 AND source_end > source_start),
            CONSTRAINT ck_chunks_content_nonempty
                CHECK (length(content) > 0),
            CONSTRAINT ck_chunks_content_sha256
                CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
            CONSTRAINT ck_chunks_token_count_positive CHECK (token_count > 0)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE eval_datasets (
            id uuid PRIMARY KEY,
            version text NOT NULL,
            manifest_sha256 text NOT NULL,
            review_status text NOT NULL,
            CONSTRAINT uq_eval_datasets_version UNIQUE (version),
            CONSTRAINT ck_eval_datasets_version_nonempty
                CHECK (length(btrim(version)) > 0),
            CONSTRAINT ck_eval_datasets_manifest_sha256
                CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$'),
            CONSTRAINT ck_eval_datasets_review_status_nonempty
                CHECK (length(btrim(review_status)) > 0)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE eval_cases (
            id uuid PRIMARY KEY,
            dataset_id uuid NOT NULL
                REFERENCES eval_datasets (id) ON DELETE RESTRICT,
            stable_key text NOT NULL,
            split text NOT NULL,
            question text NOT NULL,
            answerable boolean NOT NULL,
            reference_evidence jsonb NOT NULL,
            tags jsonb NOT NULL,
            CONSTRAINT uq_eval_cases_dataset_stable_key
                UNIQUE (dataset_id, stable_key),
            CONSTRAINT uq_eval_cases_id_dataset UNIQUE (id, dataset_id),
            CONSTRAINT ck_eval_cases_stable_key_nonempty
                CHECK (length(btrim(stable_key)) > 0),
            CONSTRAINT ck_eval_cases_split_nonempty
                CHECK (length(btrim(split)) > 0),
            CONSTRAINT ck_eval_cases_question_nonempty
                CHECK (length(btrim(question)) > 0)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE eval_runs (
            id uuid PRIMARY KEY,
            run_key text NOT NULL,
            index_version_id uuid NOT NULL
                REFERENCES index_versions (id) ON DELETE RESTRICT,
            eval_dataset_id uuid NOT NULL
                REFERENCES eval_datasets (id) ON DELETE RESTRICT,
            mode text NOT NULL,
            status text NOT NULL,
            code_sha text NOT NULL,
            version_manifest jsonb NOT NULL,
            artifact_sha256 text NOT NULL,
            CONSTRAINT uq_eval_runs_run_key UNIQUE (run_key),
            CONSTRAINT uq_eval_runs_id_dataset UNIQUE (id, eval_dataset_id),
            CONSTRAINT ck_eval_runs_run_key_nonempty
                CHECK (length(btrim(run_key)) > 0),
            CONSTRAINT ck_eval_runs_mode_nonempty
                CHECK (length(btrim(mode)) > 0),
            CONSTRAINT ck_eval_runs_status_nonempty
                CHECK (length(btrim(status)) > 0),
            CONSTRAINT ck_eval_runs_code_sha
                CHECK (code_sha ~ '^[0-9a-f]{40}$'),
            CONSTRAINT ck_eval_runs_version_manifest_object
                CHECK (jsonb_typeof(version_manifest) = 'object'),
            CONSTRAINT ck_eval_runs_artifact_sha256
                CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$')
        )
        """
    )
    op.execute(
        """
        CREATE TABLE eval_case_results (
            id uuid PRIMARY KEY,
            eval_dataset_id uuid NOT NULL,
            eval_run_id uuid NOT NULL,
            eval_case_id uuid NOT NULL,
            retrieval_evidence jsonb NOT NULL,
            citation_evidence jsonb NOT NULL,
            metric_values jsonb NOT NULL,
            status text NOT NULL,
            CONSTRAINT fk_eval_case_results_run_dataset
                FOREIGN KEY (eval_run_id, eval_dataset_id)
                REFERENCES eval_runs (id, eval_dataset_id) ON DELETE RESTRICT,
            CONSTRAINT fk_eval_case_results_case_dataset
                FOREIGN KEY (eval_case_id, eval_dataset_id)
                REFERENCES eval_cases (id, dataset_id) ON DELETE RESTRICT,
            CONSTRAINT uq_eval_case_results_run_case
                UNIQUE (eval_run_id, eval_case_id),
            CONSTRAINT ck_eval_case_results_status_nonempty
                CHECK (length(btrim(status)) > 0)
        )
        """
    )
    op.execute("CREATE INDEX ix_index_versions_corpus ON index_versions (corpus_version_id)")
    op.execute(
        "CREATE INDEX ix_chunks_index_corpus ON chunks (index_version_id, corpus_version_id)"
    )
    op.execute("CREATE INDEX ix_chunks_document_corpus ON chunks (document_id, corpus_version_id)")
    op.execute("CREATE INDEX ix_eval_runs_index ON eval_runs (index_version_id)")
    op.execute("CREATE INDEX ix_eval_runs_dataset ON eval_runs (eval_dataset_id)")
    op.execute(
        "CREATE INDEX ix_eval_case_results_run_dataset "
        "ON eval_case_results (eval_run_id, eval_dataset_id)"
    )
    op.execute(
        "CREATE INDEX ix_eval_case_results_case_dataset "
        "ON eval_case_results (eval_case_id, eval_dataset_id)"
    )


def downgrade() -> None:
    """Remove the fully reproducible foundation schema for an explicit reset."""

    op.execute("DROP TABLE eval_case_results")
    op.execute("DROP TABLE eval_runs")
    op.execute("DROP TABLE eval_cases")
    op.execute("DROP TABLE eval_datasets")
    op.execute("DROP TABLE chunks")
    op.execute("DROP TABLE documents")
    op.execute("DROP TABLE index_versions")
    op.execute("DROP TABLE corpus_versions")
    op.execute("DROP EXTENSION vector")
