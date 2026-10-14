# Investment Fit Agent

Process עצמאי להערכת התאמה (FR-50 עד FR-56). ראו `docs/09-ai-agent.md`.

```bash
python -m agent
AGENT_MODE=chain python -m agent
python -m agent --once --request <id> --verbose
```

`AGENT_MODE=deep` הוא ברירת המחדל. אחרי שני כשלי פורמט רצה שרשרת הגיבוי. `chain` מדלג על ה-Deep Agent.
כשל של Ollama, Chroma או Tavily נרשם כ-`AssessmentAborted` ומחזיר את הבקשה ל-`SUBMITTED` בלי לצרוך ניסיון.
