import glob
import os


def child_exit(server, worker):
    prom_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if not prom_dir:
        return
    for path in glob.glob(os.path.join(prom_dir, f"*_{worker.pid}.db")):
        try:
            os.remove(path)
        except OSError:
            pass
