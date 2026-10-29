import argparse
import json
import logging
import socket
import threading

from server.worker_pool import WorkerPool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)s] %(levelname)s %(message)s",
)
log = logging.getLogger("server")


def handle_client(conn: socket.socket, addr, pool: WorkerPool):
    log.info("Cliente conectado: %s", addr)
    buf = b""
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    conn.sendall(b'{"error":"json invalido"}\n')
                    continue

                cmd = msg.get("cmd")
                if cmd == "submit":
                    task_id = pool.submit(msg["payload"])
                    conn.sendall((json.dumps({"task_id": task_id}) + "\n").encode())
                elif cmd == "result":
                    res = pool.get_result(msg["task_id"])
                    if res is None:
                        conn.sendall(b'{"status":"pending"}\n')
                    else:
                        conn.sendall((json.dumps(res) + "\n").encode())
                elif cmd == "ping":
                    conn.sendall(b'{"pong":true}\n')
                else:
                    conn.sendall(b'{"error":"comando desconocido"}\n')
    except ConnectionResetError:
        pass
    finally:
        conn.close()
        log.info("Cliente desconectado: %s", addr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    pool = WorkerPool(n_workers=args.workers)
    pool.start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((args.host, args.port))
        srv.listen(128)
        log.info(
            "Servidor escuchando en %s:%d (workers=%d)",
            args.host, args.port, args.workers,
        )
        while True:
            conn, addr = srv.accept()
            threading.Thread(
                target=handle_client, args=(conn, addr, pool), daemon=True
            ).start()


if __name__ == "__main__":
    main()