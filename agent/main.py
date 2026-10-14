"""לולאת הסוכן. python -m agent, או הרצה אחת עם --once --request."""

import argparse
import logging
import os
import signal
import time
from uuid import UUID

from app.config import Config
from app.infrastructure.db import get_engine
from app.queries.assessments import request_for_assessment
from sqlalchemy.orm import Session

from agent.loop import clock, process_batch, run_request
from agent.runtime import build_services
from agent.trace import print_step, print_summary

logger = logging.getLogger("agent")
_HEARTBEAT_SECONDS = 60


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    mode = os.getenv("AGENT_MODE", "deep")
    if mode not in {"deep", "chain"}:
        print("AGENT_MODE חייב להיות deep או chain")
        return 2
    if args.request and not args.once:
        print("--request דורש --once")
        return 2
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.once and args.request:
        return _once(UUID(args.request), mode, args.verbose)
    if args.once:
        return _batch(mode, args.verbose)
    return _serve(mode)


def _once(request_id: UUID, mode: str, verbose: bool) -> int:
    now = clock()
    with Session(get_engine(Config.DB_CONNECTION_STRING)) as session:
        row = request_for_assessment(session, request_id)
        if row is None:
            print("הבקשה לא נמצאה")
            return 1
        if row["status"] != "SUBMITTED":
            print(f"הבקשה בסטטוס {row['status']} ולא בתור")
            return 1
        report = print_step if verbose else None
        status, outcome = run_request(
            session,
            request_id,
            lambda snapshot: build_services(session, snapshot, mode, today=now.date()),
            now=now,
            report=report,
        )
    duration = outcome.trace.duration_ms if outcome and outcome.trace else 0
    print_summary(status, duration)
    return 0 if status == "completed" else 1


def _batch(mode: str, verbose: bool) -> int:
    now = clock()
    with Session(get_engine(Config.DB_CONNECTION_STRING)) as session:
        process_batch(
            session,
            lambda snapshot: build_services(session, snapshot, mode, today=now.date()),
            now=now,
        )
    if verbose:
        print("סבב אחד הסתיים")
    return 0


def _serve(mode: str) -> int:
    stop = False

    def _stop(_signum, _frame) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    interval = int(os.getenv("AGENT_POLL_SECONDS", "20"))
    last_beat = time.monotonic()
    logger.info("הסוכן עלה. מצב %s, המתנה %s שניות", mode, interval)
    while not stop:
        now = clock()
        try:
            with Session(get_engine(Config.DB_CONNECTION_STRING)) as session:
                process_batch(
                    session,
                    lambda snapshot, moment=now: build_services(session, snapshot, mode, today=moment.date()),
                    now=now,
                )
        except Exception:
            logger.exception("סבב ההערכה נכשל")
        if time.monotonic() - last_beat >= _HEARTBEAT_SECONDS:
            logger.info("הסוכן פעיל")
            last_beat = time.monotonic()
        _sleep(interval, lambda: stop)
    logger.info("הסוכן נעצר")
    return 0


def _sleep(seconds: int, stopped) -> None:
    for _ in range(max(seconds, 1)):
        if stopped():
            return
        time.sleep(1)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="סוכן הערכת התאמה של GoalVest")
    parser.add_argument("--once", action="store_true", help="סבב אחד, בלי לולאה")
    parser.add_argument("--request", help="מזהה בקשה להרצה אחת")
    parser.add_argument("--verbose", action="store_true", help="הדפסת כל שלב")
    return parser
