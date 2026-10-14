# 10 – RAG ומסד נתונים וקטורי

## 10.1 מה מוטמע

ההקבלה לדרישת המרצה ("קורות חיים יעברו הטמעה במסד וקטורי"): אצלנו מוטמעים גם **מסמכי המוצרים** (המקבילה ל"דרישות המשרה") וגם **פרופילי הבקשות** (המקבילה ל"קורות החיים"), כך שאפשר לבצע התאמה סמנטית בשני הכיוונים.

| Collection ב-ChromaDB | תוכן | מקור | Metadata |
|---|---|---|---|
| `policy_documents` | תנאי פוליסות, תקנוני קרנות, דוחות רבעוניים | העלאה של סוכנים (FR-31) + Seed | product_id, institution_id, doc_type, document_id, page, chunk_index |
| `knowledge_base` | כללי מיסוי לכל אפיק, מדריכים לצרכן, הסברי מושגים, דוחות שוק | Seed של הצוות | topic (tax / liquidity / market), source_url, valid_from |
| `product_profiles` | תיאור טקסטואלי של כל מוצר (נבנה אוטומטית מנתוני המוצר) | Projector על `ProductCreated/Updated` | product_id, type, risk_level, is_active |
| `request_profiles` | תיאור טקסטואלי של כל בקשה: יעד, טווח, סיכון, העדפות (בלי פרטים מזהים) | Worker על `InvestmentRequestSubmitted` | request_id, goal_type, risk_score |

## 10.2 תהליך ההטמעה (Indexer)

1. **חילוץ טקסט**: PDF דרך `pypdf` / `pdfplumber`, DOCX דרך `python-docx`. מסמך סרוק ללא טקסט → `FAILED` עם הודעה "נדרש מסמך עם טקסט".
2. **ניקוי**: הסרת כותרות/פוטרים חוזרים, נרמול רווחים, שמירה על מספרי סעיפים.
3. **פיצול**: `RecursiveCharacterTextSplitter`, ‏800 תווים עם חפיפה של 120, עם העדפה לפיצול לפי כותרות וסעיפים.
4. **הטמעה**: `bge-m3` דרך Ollama, ב-Batches של 32.
5. **שמירה**: `collection.upsert(ids=f"{document_id}:{i}", ...)`. אותם מזהים נכתבים שוב בהרצה חוזרת, בלי כפילויות. מחיקה והטמעה מחדש כשמסמך מוחלף.
6. **אירוע**: `ProductDocumentIndexed` עם מספר ה-chunks, או `ProductDocumentIndexFailed`. עדכון `ConsumerCheckpoints` ורישום האירוע נעשים באותה טרנזקציה, אחרי ה-upsert.

## 10.3 חיפוש

| שימוש | שאילתה | סינון |
|---|---|---|
| סוכן AI – תנאי מוצר | "תנאי משיכה ונזילות" + שם מוצר | `product_id in candidates` |
| סוכן AI – מיסוי | "מיסוי רווחים במשיכה לפני גיל 60 בקופת גמל להשקעה" | `topic = tax` |
| התאמת מוצרים לבקשה | טקסט `request_profiles` של הבקשה | `product_profiles`, `is_active = true`, `risk_level` בטווח |
| חיפוש סמנטי למשתמש (FR-22) | שאלת המשתמש | `product_profiles` + `policy_documents` |

- `k = 6`, סף מרחק קוסינוס (לכיול בבדיקות), החזרת טקסט + metadata לציטוט.
- **Hybrid (Should)**: שילוב תוצאות סמנטיות עם סינון SQL על `rm_products` (סוג, סיכון, דמי ניהול) – הסינון ב-SQL, הדירוג ב-Chroma.

## 10.4 Tool לסוכן

```python
@tool
def search_knowledge_base(query: str, collection: Literal["policy_documents", "knowledge_base", "product_profiles"],
                          product_ids: list[str] | None = None, topic: str | None = None, k: int = 6) -> list[dict]:
    """חיפוש סמנטי במאגר המסמכים. מחזיר קטעים עם title, document_id, excerpt ו-score לציטוט."""
```

## 10.5 בדיקות איכות לאחזור

- סט של 20 שאלות עם המסמך הנכון הצפוי (למשל "מתי אפשר למשוך קרן השתלמות בלי מס?" → מסמך כללי מס השתלמות).
- מדד: Hit@6 ≥ 80%. מריצים אחרי כל שינוי בפיצול או במודל ההטמעה.
