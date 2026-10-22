"""Database-backed worker. Run separately from the API: `python -m app.worker`."""
import logging
import time

from app.config import get_settings
from app.database import SessionLocal
from app.services import claim_next_run, execute_run

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def run_once() -> bool:
    with SessionLocal() as db:
        run = claim_next_run(db)
        if not run: return False
        logging.info("Executing run %s", run.id)
        execute_run(db, run)
        return True


def main():
    settings = get_settings()
    while True:
        if not run_once(): time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__": main()
