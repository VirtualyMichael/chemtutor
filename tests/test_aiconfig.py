"""Ollama / LM Studio selection, against fake OpenAI-compatible servers.
Run:  python -m unittest tests.test_aiconfig
"""
import http.client, json, sys, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import aiconfig, library, web  # noqa: E402


def fake(models, reply="ok", think_tokens=0, reject_effort=False, seen=None, host="127.0.0.1"):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, obj):
            d = json.dumps(obj).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(d)))
            self.end_headers()
            self.wfile.write(d)

        def do_GET(self):
            self._send({"data": [{"id": m} for m in models]})

        def do_POST(self):
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if seen is not None:
                seen.append(req)
            if reject_effort and "reasoning_effort" in req:
                self.send_response(400)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if think_tokens and req.get("max_tokens", 10**9) <= think_tokens:  # a reasoning model that ran out of budget while thinking
                return self._send({"choices": [{"finish_reason": "length", "message": {"content": "", "reasoning_content": "hmm"}}]})
            self._send({"choices": [{"finish_reason": "stop", "message": {"content": reply}}]})

    srv = ThreadingHTTPServer((host, 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://{host}:{srv.server_address[1]}/v1"


class Pure(unittest.TestCase):
    def test_model_matching_and_choice(self):
        self.assertTrue(aiconfig.has_model("qwen2.5:7b", ["qwen2.5:7b", "llama3:8b"]))
        self.assertTrue(aiconfig.has_model("qwen2.5", ["qwen2.5:7b"]))           # no tag: any tag
        self.assertFalse(aiconfig.has_model("qwen2.5:7b", ["qwen2.5:3b"]))
        self.assertEqual(aiconfig.best_model(["gemma-2-2b-it", "qwen2.5-14b-instruct", "llama-3.1-8b", "big-70b"]), "qwen2.5-14b-instruct")
        self.assertEqual(aiconfig.best_model(["big-70b", "huge-31b"]), "huge-31b")                      # all too big: smallest
        self.assertEqual(aiconfig.best_model(["x-12b-uncensored", "y-8b-instruct", "z-coder-13b"]), "y-8b-instruct")
        self.assertEqual(aiconfig.best_model(["alpha", "beta"]), "alpha")
        self.assertIsNone(aiconfig.best_model([]))

    def test_aliases(self):
        self.assertEqual(aiconfig.resolve_url("lmstudio"), "http://127.0.0.1:1234/v1")
        self.assertEqual(aiconfig.resolve_url("OLLAMA"), "http://127.0.0.1:11434/v1")
        self.assertEqual(aiconfig.resolve_url("http://x:1/v1"), "http://x:1/v1")
        self.assertEqual(aiconfig.backend_name("http://localhost:1234/v1/"), "LM Studio")
        self.assertEqual(aiconfig.backend_name("http://100.64.1.2:11434/v1"), "Ollama")

    def test_auto_pick_prefers_default_model_then_largest(self):
        a = {"name": "A", "url": "http://a/v1", "up": True, "models": ["gemma-2b"]}
        b = {"name": "B", "url": "http://b/v1", "up": True, "models": ["qwen2.5:7b", "llama-70b"]}
        down = {"name": "C", "url": "http://c/v1", "up": False, "models": []}
        self.assertEqual(aiconfig.auto_pick([a, b, down]), ("http://b/v1", "qwen2.5:7b"))
        self.assertEqual(aiconfig.auto_pick([a, down]), ("http://a/v1", "gemma-2b"))
        self.assertIsNone(aiconfig.auto_pick([down]))


class Servers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.old = (library.HOME, library.DB, aiconfig.BACKENDS, web.LLM_URL, web.LLM_MODEL, web._auto, aiconfig._other_addresses)
        aiconfig._other_addresses = lambda: []
        library.HOME = Path(self.tmp.name)
        library.DB = library.HOME / "t.sqlite3"
        self.s1, self.u1 = fake(["qwen2.5:7b", "nomic-embed-text:latest"])
        self.s2, self.u2 = fake(["lmstudio-community/qwen2.5-14b-instruct", "text-embedding-nomic"], "<think>hmm, 2+2</think>The answer is 4.")
        aiconfig.BACKENDS = [("Ollama", self.u1), ("LM Studio", self.u2)]
        web._llm_cache["t"] = 0.0

    def tearDown(self):
        for s in (self.s1, self.s2):
            s.shutdown()
            s.server_close()
        library.HOME, library.DB, aiconfig.BACKENDS, web.LLM_URL, web.LLM_MODEL, web._auto, aiconfig._other_addresses = self.old
        web._llm_cache["t"] = 0.0
        self.tmp.cleanup()

    def test_detect_filters_embedding_models(self):
        found = aiconfig.detect()
        self.assertEqual([b["name"] for b in found], ["Ollama", "LM Studio"])
        self.assertEqual(found[0]["models"], ["qwen2.5:7b"])
        self.assertEqual(found[1]["models"], ["lmstudio-community/qwen2.5-14b-instruct"])
        self.assertIsNone(aiconfig.list_models("http://127.0.0.1:9/v1"))

    def test_status_switches_to_lm_studio_when_ollama_is_gone(self):
        web.LLM_URL, web.LLM_MODEL, web._auto = self.u1, "qwen2.5:7b", "all"
        self.assertEqual(web.llm_status(True)[:2], (True, True))
        self.s1.shutdown()
        self.s1.server_close()
        web._llm_cache["t"] = 0.0
        up, have, _ = web.llm_status(True)
        self.assertTrue(up and have)
        self.assertEqual((web.LLM_URL, web.LLM_MODEL), (self.u2, "lmstudio-community/qwen2.5-14b-instruct"))

    def test_exact_settings_are_never_switched(self):
        web.LLM_URL, web.LLM_MODEL, web._auto = self.u1, "not-installed", "off"
        up, have, _ = web.llm_status(True)
        self.assertTrue(up)
        self.assertFalse(have)
        self.assertEqual((web.LLM_URL, web.LLM_MODEL), (self.u1, "not-installed"))

    def test_reasoning_blocks_are_removed_from_replies(self):
        web.LLM_URL, web.LLM_MODEL = self.u2, "lmstudio-community/qwen2.5-14b-instruct"
        self.assertEqual(web.llm([{"role": "user", "content": "2+2?"}]), "The answer is 4.")

    def test_reasoning_model_that_runs_out_of_tokens_is_retried_with_more_room(self):
        srv, url = fake(["thinker-12b"], "Count the digits.", think_tokens=400)
        try:
            web.LLM_URL, web.LLM_MODEL = url, "thinker-12b"
            self.assertEqual(web.llm([{"role": "user", "content": "hint"}], max_tokens=200), "Count the digits.")
        finally:
            srv.shutdown()
            srv.server_close()

    def test_lm_studio_gets_no_thinking_and_falls_back_if_the_model_refuses_the_setting(self):
        seen = []
        srv, url = fake(["m-8b"], "fine", seen=seen)
        srv2, url2 = fake(["m-8b"], "fine too", reject_effort=True, seen=seen)
        try:
            aiconfig.BACKENDS = [("Ollama", self.u1), ("LM Studio", url)]
            web.LLM_URL, web.LLM_MODEL = url, "m-8b"
            self.assertEqual(web.llm([{"role": "user", "content": "x"}]), "fine")
            self.assertEqual(seen[-1].get("reasoning_effort"), "none")
            aiconfig.BACKENDS = [("Ollama", self.u1), ("LM Studio", url2)]
            web.LLM_URL = url2
            self.assertEqual(web.llm([{"role": "user", "content": "x"}]), "fine too")   # retried without the setting
            self.assertNotIn("reasoning_effort", seen[-1])
            web.LLM_URL = self.u1                                                       # other servers never get it
            web.llm([{"role": "user", "content": "x"}])
            self.assertNotIn("reasoning_effort", seen[-1])
        finally:
            for s in (srv, srv2):
                s.shutdown()
                s.server_close()

    def test_empty_hint_is_retried_then_replaced_by_the_safe_hint(self):
        from app import hints
        p = web.load_problems()["gen-sigfigs-06"]
        out = hints.generate(p, 1, lambda *a: "")
        self.assertTrue(out["fallback"])
        self.assertTrue(out["reply"])

    def test_server_that_listens_only_on_another_address_is_found(self):
        # e.g. LM Studio's "network interface" setting pointed at the Tailscale address instead of localhost
        srv, alt = fake(["m-8b"], host="127.0.0.2")
        port = alt.split(":")[2].split("/")[0]
        try:
            aiconfig.BACKENDS = [("Ollama", self.u1), ("LM Studio", f"http://127.0.0.1:{port}/v1")]
            aiconfig._other_addresses = lambda: ["127.0.0.2"]
            found = aiconfig.detect()
            self.assertTrue(found[1]["up"])
            self.assertEqual(found[1]["url"], alt)
            self.assertEqual(found[1]["models"], ["m-8b"])
            self.assertEqual(aiconfig.auto_pick(found, "nope")[0], self.u1 if found[0]["up"] and found[0]["models"] else alt)
        finally:
            srv.shutdown()
            srv.server_close()

    def test_choice_is_saved_and_restored(self):
        aiconfig.save(self.u2, "lmstudio-community/qwen2.5-14b-instruct")
        import os
        for k in ("LLM_URL", "LLM_MODEL"):
            os.environ.pop(k, None)
        web.init_llm()
        self.assertEqual((web.LLM_URL, web.LLM_MODEL), (self.u2, "lmstudio-community/qwen2.5-14b-instruct"))
        self.assertEqual(web._auto, "all")


class Endpoint(Servers):
    def setUp(self):
        super().setUp()
        self.srv = web.make_server(0, remote_access=True, host="127.0.0.1")
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.key = __import__("app.remote", fromlist=["x"]).set_enabled(True)
        web.LLM_URL, web.LLM_MODEL = self.u1, "qwen2.5:7b"

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        super().tearDown()

    def call(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.srv.server_address[1], timeout=20)
        h = dict(headers or {})
        c.request(method, path, json.dumps(body) if body is not None else None, {"Content-Type": "application/json", **h})
        r = c.getresponse()
        out = (r.status, json.loads(r.read() or b"{}"))
        c.close()
        return out

    def test_this_computer_can_switch_and_it_sticks(self):
        s, d = self.call("GET", "/api/ai")
        self.assertEqual(s, 200)
        self.assertTrue(d["can_change"])
        self.assertEqual(len(d["backends"]), 2)
        s, d = self.call("POST", "/api/ai", {"url": self.u2, "model": "lmstudio-community/qwen2.5-14b-instruct"})
        self.assertEqual(s, 200)
        self.assertEqual(web.LLM_URL, self.u2)
        self.assertEqual(aiconfig.load()["model"], "lmstudio-community/qwen2.5-14b-instruct")
        cfg = self.call("GET", "/api/config")[1]
        self.assertTrue(cfg["llm_ok"])

    def test_bad_choices_are_rejected(self):
        self.assertEqual(self.call("POST", "/api/ai", {"url": "http://evil.example/v1", "model": "x"})[0], 400)
        self.assertEqual(self.call("POST", "/api/ai", {"url": self.u1, "model": "no-such-model"})[0], 400)
        self.assertEqual(web.LLM_URL, self.u1)

    def test_a_paired_phone_cannot_change_the_model(self):
        phone = {"X-Forwarded-For": "100.64.0.9", "Authorization": f"Bearer {self.key}"}
        self.assertFalse(self.call("GET", "/api/ai", headers=phone)[1]["can_change"])
        self.assertEqual(self.call("POST", "/api/ai", {"url": self.u2, "model": "lmstudio-community/qwen2.5-14b-instruct"}, phone)[0], 403)
        self.assertEqual(web.LLM_URL, self.u1)


if __name__ == "__main__":
    unittest.main()
