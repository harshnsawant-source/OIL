"""OIL — private, cited document intelligence. Local-first.

Package layout (as it gets built):
    ingest      load documents -> chunks with source + page metadata
    index       local embeddings + chunked vector store + retrieval
    answer      grounded, cited answer with a calibrated refusal path
    audit       access log (which documents were read)
"""

__version__ = "0.0.1"
