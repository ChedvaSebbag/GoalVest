#!/usr/bin/env bash
# ============================================================
#  GoalVest – הפעלת כל המערכת בפקודה אחת
#
#  הפעלה רגילה:          bash dev.sh
#  אחרי git pull / שינוי: bash dev.sh --setup   (התקנות + מיגרציות)
#  עצירה של הכול:        Ctrl + C
# ============================================================
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
mkdir -p logs
grep -qx "logs/" .gitignore 2>/dev/null || echo "logs/" >> .gitignore

PIDS=()

free_port() {
  local pids
  pids=$(lsof -t -i :"$1" 2>/dev/null || true)
  if [ -n "$pids" ]; then kill $pids 2>/dev/null || true; sleep 1; fi
}

cleanup() {
  echo
  echo "⏹  עוצרת את כל התהליכים..."
  for p in "${PIDS[@]}"; do kill "$p" 2>/dev/null || true; done
  pkill -f "python -m agent" 2>/dev/null || true
  pkill -f "python -m worker.indexer" 2>/dev/null || true
  free_port 5000
  free_port 4200
  echo "✓ הכול נעצר. (Docker ו-Ollama נשארים פתוחים)"
  exit 0
}
trap cleanup INT TERM

wait_for() {  # wait_for <name> <url> <max_seconds>
  local i=0
  until curl -s -o /dev/null "$2"; do
    sleep 2; i=$((i + 2))
    if [ "$i" -ge "$3" ]; then echo "✗ $1 לא עלה תוך $3 שניות – בדקי את logs/"; return 1; fi
  done
  echo "✓ $1"
}

echo "🚀 מפעילה את GoalVest..."

# 1) Docker + ChromaDB
if ! docker info >/dev/null 2>&1; then
  echo "🐳 מפעילה את Docker Desktop (עד דקה)..."
  open -a Docker
  until docker info >/dev/null 2>&1; do sleep 2; done
fi
docker compose up -d chromadb >/dev/null 2>&1
wait_for "ChromaDB" "http://localhost:8000/api/v2/heartbeat" 60

# 2) Ollama
if ! curl -s -o /dev/null http://localhost:11434/api/tags; then
  echo "🦙 מפעילה את Ollama..."
  open -a Ollama
fi
wait_for "Ollama" "http://localhost:11434/api/tags" 60

# 3) סביבת Python
# shellcheck disable=SC1091
source backend/.venv/bin/activate

if [ "${1:-}" = "--setup" ]; then
  echo "📦 מתקינה תלויות ומריצה מיגרציות..."
  (cd backend && pip install -q -r requirements.txt && python -m scripts.migrate) || { echo "✗ ההתקנה בשרת נכשלה"; exit 1; }
  (cd frontend && (npm install --silent || npx -y npm@11 install)) || { echo "✗ npm install נכשל"; exit 1; }
fi

# 4) מנקה תהליכים ישנים שתופסים פורטים
free_port 5000
free_port 4200
pkill -f "python -m agent" 2>/dev/null || true
pkill -f "python -m worker.indexer" 2>/dev/null || true

# 5) מפעילה את כל התהליכים ברקע, כל אחד עם קובץ לוג משלו
(cd backend && exec python wsgi.py)            > logs/api.log     2>&1 & PIDS+=($!)
(exec python -m agent)                          > logs/agent.log   2>&1 & PIDS+=($!)
(exec python -m worker.indexer)                 > logs/indexer.log 2>&1 & PIDS+=($!)
(cd frontend && exec npm start -- --open=false) > logs/web.log     2>&1 & PIDS+=($!)

wait_for "שרת Flask"   "http://127.0.0.1:5000/api/health" 60
wait_for "ממשק Angular" "http://localhost:4200"          180

echo
echo "✅ הכול רץ:  http://localhost:4200"
echo "   לוגים בתיקייה logs/ (api, agent, indexer, web). לעצירה: Ctrl + C"
echo "------------------------------------------------------------"
open "http://localhost:4200"

# מציגה את כל הלוגים בחלון אחד
tail -n 0 -f logs/api.log logs/agent.log logs/indexer.log logs/web.log &
PIDS+=($!)
wait
