from __future__ import annotations

import io
import json
import threading
import traceback
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime

from models import db
from models.model_training_run import ModelTrainingRun


_lock = threading.Lock()
_active_thread: threading.Thread | None = None


def _run_training_job(run_id: int) -> None:
    buf = io.StringIO()
    started_at = datetime.utcnow()

    try:
        from app import create_app

        app = create_app("development")
        with app.app_context():
            run = ModelTrainingRun.query.get(run_id)
            if not run:
                return
            run.status = "running"
            run.started_at = started_at
            db.session.commit()

            from train_models import ModelTrainer

            with redirect_stdout(buf), redirect_stderr(buf):
                trainer = ModelTrainer()
                run = ModelTrainingRun.query.get(run_id)
                dataset_id = run.dataset_id if run else None
                sources = []
                if run and run.sources:
                    sources = [s.strip() for s in run.sources.split(",") if s.strip()]
                min_samples = (run.min_samples if run and run.min_samples is not None else None)

                metrics = trainer.train_all_models(dataset_id=dataset_id, sources=sources or None, min_samples=min_samples)

            run = ModelTrainingRun.query.get(run_id)
            if not run:
                return
            run.status = "success"
            run.finished_at = datetime.utcnow()
            run.metrics_json = json.dumps(metrics or {}, ensure_ascii=False)
            run.logs_text = buf.getvalue()
            db.session.commit()

    except Exception as e:
        try:
            from app import create_app

            app = create_app("development")
            with app.app_context():
                run = ModelTrainingRun.query.get(run_id)
                if run:
                    run.status = "failed"
                    run.finished_at = datetime.utcnow()
                    run.error_message = str(e)
                    run.logs_text = buf.getvalue() + "\n\n" + traceback.format_exc()
                    db.session.commit()
        except Exception:
            # Best-effort; don't re-raise from a background thread.
            pass

    finally:
        global _active_thread
        with _lock:
            _active_thread = None


def trigger_training(*, dataset_id: int | None = None, sources: list[str] | None = None, min_samples: int | None = None) -> ModelTrainingRun:
    global _active_thread

    with _lock:
        if _active_thread and _active_thread.is_alive():
            raise RuntimeError("A training job is already running")

        run = ModelTrainingRun(status="queued", created_at=datetime.utcnow())
        if dataset_id is not None:
            run.dataset_id = int(dataset_id)
        if sources:
            run.sources = ",".join([s.strip() for s in sources if s and str(s).strip()])
        if min_samples is not None:
            run.min_samples = int(min_samples)
        db.session.add(run)
        db.session.commit()

        thread = threading.Thread(target=_run_training_job, args=(run.id,), daemon=True)
        _active_thread = thread
        thread.start()

        return run
