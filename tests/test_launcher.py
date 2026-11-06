"""Starting, replacing and stopping ChemTutor from the launcher.
Run:  python -m unittest tests.test_launcher
"""
import http.client, json, socket, sys, tempfile, threading, time, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import chemtutor  # noqa: E402
from app import library, web  # noqa: E402


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Stop(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.old = (library.HOME, library.DB)
        library.HOME = Path(self.tmp.name)
        library.DB = library.HOME / "t.sqlite3"

    def tearDown(self):
        library.HOME, library.DB = self.old
        self.tmp.cleanup()

    def start(self, remote=False):
        port = free_port()
        srv = web.make_server(port, remote_access=remote, host="127.0.0.1")
        done = threading.Event()

        def run():
            try:
                srv.serve_forever()
            finally:
                done.set()

        threading.Thread(target=run, daemon=True).start()
        for _ in range(50):
            if chemtutor.chemtutor_at(port):
                break
            time.sleep(0.1)
        return port, srv, done

    def post(self, port, path, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        c.request("POST", path, "{}", {"Content-Type": "application/json", **(headers or {})})
        r = c.getresponse()
        r.read()
        c.close()
        return r.status

    def test_health_reports_version_and_pid(self):
        port, srv, done = self.start()
        try:
            h = chemtutor.chemtutor_at(port)
            self.assertEqual(h["version"], chemtutor.__dict__.get("__version__", h["version"]))
            self.assertIsInstance(h["pid"], int)
        finally:
            srv.shutdown()
            srv.server_close()

    def test_stop_server_really_stops_it_and_frees_the_port(self):
        port, srv, done = self.start()
        self.assertTrue(chemtutor.stop_server(port))
        self.assertTrue(done.wait(5))                 # serve_forever returned: the launcher's wait loop would exit
        self.assertFalse(chemtutor.port_busy(port))
        srv.server_close()

    def test_stopping_when_nothing_runs_is_fine(self):
        self.assertTrue(chemtutor.stop_server(free_port()))

    def test_a_paired_phone_cannot_stop_the_server(self):
        from app import remote
        key = remote.set_enabled(True)
        port, srv, done = self.start(remote=True)
        try:
            self.assertEqual(self.post(port, "/api/shutdown", {"X-Forwarded-For": "100.64.0.9", "Authorization": f"Bearer {key}"}), 403)
            time.sleep(0.3)
            self.assertTrue(chemtutor.chemtutor_at(port))
        finally:
            srv.shutdown()
            srv.server_close()


class RealProcess(unittest.TestCase):
    """The actual command line, in separate processes."""

    def test_run_then_stop_exits_the_first_process(self):
        import os, subprocess
        port = free_port()
        env = {**os.environ, "CHEMTUTOR_HOME": tempfile.mkdtemp(), "LLM_URL": "http://127.0.0.1:9/v1"}
        for k in ("LLM_MODEL", "PORT"):
            env.pop(k, None)
        run = subprocess.Popen([sys.executable, str(ROOT / "chemtutor.py"), "--port", str(port), "--no-browser"], env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            for _ in range(100):
                if chemtutor.chemtutor_at(port):
                    break
                time.sleep(0.2)
            self.assertTrue(chemtutor.chemtutor_at(port), "server did not start")
            out = subprocess.run([sys.executable, str(ROOT / "chemtutor.py"), "stop", "--port", str(port)], env=env,
                                 capture_output=True, text=True, timeout=60).stdout
            self.assertIn("Stopping ChemTutor", out)
            self.assertEqual(run.wait(timeout=15), 0)          # the running window's process ended by itself
            self.assertFalse(chemtutor.port_busy(port))
        finally:
            if run.poll() is None:
                run.kill()
            run.stdout.close()


if __name__ == "__main__":
    unittest.main()
