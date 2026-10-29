
import argparse
import json
import socket
import time

HOST, PORT = "127.0.0.1", 5000


class Client:
    def __init__(self, host=HOST, port=PORT, retries=3):
        self.host, self.port, self.retries = host, port, retries
        self.sock = None

    def connect(self):
        last = None
        for i in range(self.retries):
            try:
                self.sock = socket.create_connection(
                    (self.host, self.port), timeout=5
                )
                self.sock_file = self.sock.makefile("rwb")
                return
            except OSError as e:
                last = e
                print(f"[retry {i+1}/{self.retries}] {e}")
                time.sleep(1)
        raise ConnectionError(f"No se pudo conectar: {last}")

    def _send(self, obj):
        self.sock_file.write((json.dumps(obj) + "\n").encode())
        self.sock_file.flush()

    def _recv(self):
        line = self.sock_file.readline()
        if not line:
            raise ConnectionError("Servidor cerró la conexión")
        return json.loads(line)

    def submit(self, payload):
        self._send({"cmd": "submit", "payload": payload})
        return self._recv()["task_id"]

    def wait_result(self, task_id, timeout=30):
        t0 = time.time()
        while time.time() - t0 < timeout:
            self._send({"cmd": "result", "task_id": task_id})
            res = self._recv()
            if res.get("status") != "pending":
                return res
            time.sleep(0.3)
        raise TimeoutError("Timeout esperando resultado")

    def close(self):
        if self.sock:
            self.sock.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("op", choices=["sum", "mul", "sleep"])
    ap.add_argument("a", type=float, nargs="?")
    ap.add_argument("b", type=float, nargs="?")
    ap.add_argument("--host", default=HOST)
    ap.add_argument("--port", type=int, default=PORT)
    args = ap.parse_args()

    payload = {"op": args.op}
    if args.op in ("sum", "mul"):
        payload.update(a=args.a, b=args.b)
    elif args.op == "sleep":
        payload["t"] = args.a

    c = Client(args.host, args.port)
    c.connect()
    try:
        tid = c.submit(payload)
        print(f"Tarea enviada: {tid}")
        res = c.wait_result(tid)
        print(f"Resultado: {res}")
    finally:
        c.close()


if __name__ == "__main__":
    main()