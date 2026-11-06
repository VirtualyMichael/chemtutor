"""Phone access: the access key, the loopback exemption and the installable-app files.
Run:  python -m unittest tests.test_remote
"""
import http.client, json, sys, tempfile, threading, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import library, remote, web  # noqa: E402

REMOTE = {"X-Forwarded-For": "100.64.0.9"}  # what a proxy such as `tailscale serve` adds; marks the request as not-from-this-computer


class RemoteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.old = (library.DB, library.HOME)
        library.HOME = Path(cls.tmp.name)
        library.DB = library.HOME / "test.sqlite3"
        cls.key = remote.set_enabled(True)
        cls.srv = web.make_server(0, remote_access=True, host="127.0.0.1")
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.port = cls.srv.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        library.DB, library.HOME = cls.old
        cls.tmp.cleanup()

    def req(self, method, path, headers=None, body=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=20)
        h = dict(headers or {})
        if body is not None:
            h["Content-Type"] = "application/json"
        c.request(method, path, json.dumps(body) if body is not None else None, h)
        r = c.getresponse()
        data = r.read()
        out = (r.status, dict(r.getheaders()), data)
        c.close()
        return out


class Gate(RemoteTest):
    def test_this_computer_needs_no_key(self):
        self.assertEqual(self.req("GET", "/api/progress")[0], 200)
        self.assertEqual(self.req("GET", "/")[0], 200)

    def test_other_devices_are_refused_without_the_key(self):
        s, _, body = self.req("GET", "/api/progress", REMOTE)
        self.assertEqual(s, 401)
        self.assertIn("paired", json.loads(body)["error"])
        self.assertEqual(self.req("GET", "/", REMOTE)[0], 401)
        self.assertEqual(self.req("POST", "/api/check", REMOTE, {"id": "x", "answer": "1"})[0], 401)
        self.assertEqual(self.req("GET", "/api/progress?key=wrong", REMOTE)[0], 401)

    def test_pairing_link_sets_a_cookie_that_then_works(self):
        s, h, _ = self.req("GET", f"/?key={self.key}", REMOTE)
        self.assertEqual(s, 302)
        self.assertEqual(h["Location"], "/")                       # key is removed from the address bar
        cookie = h["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        pair = cookie.split(";")[0]
        self.assertEqual(self.req("GET", "/api/progress", {**REMOTE, "Cookie": pair})[0], 200)
        self.assertEqual(self.req("GET", "/", {**REMOTE, "Cookie": pair})[0], 200)
        self.assertEqual(self.req("POST", "/api/check", {**REMOTE, "Cookie": pair}, {"id": "nope", "answer": "1"})[0], 404)  # past the gate

    def test_bearer_header_works(self):
        self.assertEqual(self.req("GET", "/api/progress", {**REMOTE, "Authorization": f"Bearer {self.key}"})[0], 200)

    def test_public_files_need_no_key(self):
        for path in ("/api/health", "/manifest.webmanifest", "/sw.js", "/icons/icon-192.png", "/icons/maskable-512.png"):
            self.assertEqual(self.req("GET", path, REMOTE)[0], 200, path)

    def test_foreign_host_name_on_loopback_is_not_trusted(self):
        # DNS-rebinding style request: connects from 127.0.0.1 but names another host
        self.assertEqual(self.req("GET", "/api/progress", {"Host": "evil.example"})[0], 401)
        self.assertEqual(self.req("GET", "/api/progress", {"Host": "localhost:8765"})[0], 200)

    def test_local_only_mode_is_unchanged(self):
        srv = web.make_server(0)
        self.assertEqual(srv.server_address[0], "127.0.0.1")
        self.assertFalse(srv.remote)
        srv.server_close()


class KeyStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.old = library.HOME
        library.HOME = Path(self.tmp.name)

    def tearDown(self):
        library.HOME = self.old
        self.tmp.cleanup()

    def test_off_by_default_and_key_is_stable_until_reset(self):
        self.assertFalse(remote.enabled())
        k = remote.set_enabled(True)
        self.assertTrue(remote.enabled())
        self.assertGreaterEqual(len(k), 30)
        self.assertEqual(remote.token(), k)
        k2 = remote.reset_token()
        self.assertNotEqual(k, k2)
        remote.set_enabled(False)
        self.assertFalse(remote.enabled())
        self.assertEqual(remote.token(), k2)

    def test_tailscale_range(self):
        self.assertTrue(remote._is_tailscale("100.101.5.5"))
        self.assertFalse(remote._is_tailscale("100.20.0.1"))
        self.assertFalse(remote._is_tailscale("192.168.1.5"))


class AppFiles(unittest.TestCase):
    root = Path(__file__).resolve().parents[1] / "web"

    def test_manifest_is_installable(self):
        m = json.loads((self.root / "manifest.webmanifest").read_text(encoding="utf-8"))
        self.assertEqual(m["display"], "standalone")
        sizes = {i["sizes"] for i in m["icons"]}
        self.assertTrue({"192x192", "512x512"} <= sizes)
        self.assertTrue(any(i["purpose"] == "maskable" for i in m["icons"]))
        for i in m["icons"]:
            self.assertTrue((self.root / i["src"].lstrip("/")).is_file(), i["src"])

    def test_page_links_the_app_files(self):
        html = (self.root / "index.html").read_text(encoding="utf-8")
        for needle in ("/manifest.webmanifest", "serviceWorker", "viewport-fit=cover", "theme-color"):
            self.assertIn(needle, html)
        self.assertTrue((self.root / "sw.js").is_file())


if __name__ == "__main__":
    unittest.main()
