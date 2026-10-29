import queue
import threading
import time
import uuid
import logging
from typing import Any, Dict

log = logging.getLogger("worker_pool")


class WorkerPool:
    def __init__(self, n_workers: int = 8):
        self.tasks: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self.results: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.n_workers = n_workers
        self._threads = []

    def start(self):
        for i in range(self.n_workers):
            t = threading.Thread(
                target=self._worker_loop, name=f"worker-{i}", daemon=True
            )
            t.start()
            self._threads.append(t)
        log.info("Pool iniciado con %d hilos", self.n_workers)

    def submit(self, payload: Dict[str, Any]) -> str:
        task_id = str(uuid.uuid4())
        self.tasks.put({"id": task_id, "payload": payload, "ts": time.time()})
        log.info("Tarea %s encolada", task_id)
        return task_id

    def get_result(self, task_id: str) -> Dict[str, Any] | None:
        with self.lock:
            return self.results.get(task_id)

    def _worker_loop(self):
        while True:
            task = self.tasks.get()
            try:
                out = self._process(task["payload"])
                with self.lock:
                    self.results[task["id"]] = {"ok": True, "result": out}
            except Exception as e:
                with self.lock:
                    self.results[task["id"]] = {"ok": False, "error": str(e)}
            finally:
                self.tasks.task_done()

    @staticmethod
    def _process(payload: Dict[str, Any]) -> Any:
        op = payload.get("op")
        a, b = payload.get("a"), payload.get("b")
        if op == "sum":
            return a + b
        if op == "mul":
            return a * b
        if op == "sleep":
            time.sleep(float(payload.get("t", 1)))
            return "done"
        raise ValueError(f"Operación desconocida: {op}")