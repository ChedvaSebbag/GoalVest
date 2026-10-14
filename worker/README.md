# Worker

## Indexer

קורא אירועי `ProductDocumentUploaded` חדשים, מחלץ טקסט, מפצל ל-chunks, ומטמיע ב-Chroma collection `policy_documents`. עדכון `ConsumerCheckpoints` ורישום `ProductDocumentIndexed` או `ProductDocumentIndexFailed` נעשים באותה טרנזקציה. ההטמעה היא upsert עם מזהה `{document_id}:{i}`.

משורש ה-Repo, עם סביבת ה-backend:

```bash
python -m worker.indexer          # לולאה כל 15 שניות
python -m worker.indexer --once   # הרצה אחת
```

## מאגר ידע

```bash
python -m worker.index_knowledge
```

מטמיע את `seed/knowledge/` ל-collection `knowledge_base`. חיפוש: `search_knowledge_base` ב-`worker/rag.py`.
