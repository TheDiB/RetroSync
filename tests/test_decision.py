import json
import tempfile
import unittest
from pathlib import Path

from decision import baseline_hash, decide, load_baseline


def h(char):
    return char * 64


class DecisionTests(unittest.TestCase):
    def test_in_sync_without_baseline(self):
        self.assertEqual(decide(h("a"), h("a")), "IN_SYNC")

    def test_in_sync_even_if_baseline_is_stale(self):
        self.assertEqual(decide(h("b"), h("b"), h("a")), "IN_SYNC")

    def test_push(self):
        self.assertEqual(decide(h("b"), h("a"), h("a")), "PUSH")

    def test_pull(self):
        self.assertEqual(decide(h("a"), h("b"), h("a")), "PULL")

    def test_conflict(self):
        self.assertEqual(decide(h("b"), h("c"), h("a")), "CONFLICT")

    def test_initial_conflict(self):
        self.assertEqual(decide(h("a"), h("b")), "INITIAL_CONFLICT")

    def test_missing_local(self):
        self.assertEqual(decide(None, h("a"), h("a")), "MISSING_LOCAL")

    def test_missing_remote(self):
        self.assertEqual(decide(h("a"), None, h("a")), "MISSING_REMOTE")

    def test_missing_both(self):
        self.assertEqual(decide(None, None), "MISSING_BOTH")

    def test_invalid_digest_rejected(self):
        with self.assertRaises(ValueError):
            decide("not-a-hash", h("a"))

    def test_case_insensitive_hex(self):
        self.assertEqual(decide(h("A"), h("a")), "IN_SYNC")

    def test_wario_known_history(self):
        old = "91f6e75149f3f6477a9cdc72fd1d2879ddf3a24dc265a6687136f9303661018a"
        nas = "14a77e2aa76063a636fd5f65223751baf086e11154e5317b49442ba74e66fa6b"
        self.assertEqual(decide(old, nas, old), "PULL")
        self.assertEqual(decide(old, nas), "INITIAL_CONFLICT")


class BaselineTests(unittest.TestCase):
    def write(self, folder, data):
        path = Path(folder) / "baseline.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_optional_baseline(self):
        self.assertEqual(load_baseline(None, "deck"), {})

    def test_load_baseline(self):
        data = {"schema_version": 1, "device_id": "deck",
                "games": {"wario": {"sram": {"last_synced_sha256": h("a")}}}}
        with tempfile.TemporaryDirectory() as folder:
            games = load_baseline(self.write(folder, data), "deck")
            self.assertEqual(baseline_hash(games, "wario"), h("a"))
            self.assertIsNone(baseline_hash(games, "other"))

    def test_wrong_device_rejected(self):
        data = {"schema_version": 1, "device_id": "other", "games": {}}
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                load_baseline(self.write(folder, data), "deck")

    def test_invalid_hash_rejected(self):
        data = {"schema_version": 1, "device_id": "deck",
                "games": {"wario": {"sram": {"last_synced_sha256": "oops"}}}}
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                load_baseline(self.write(folder, data), "deck")

    def test_null_baseline_means_unknown(self):
        data = {"schema_version": 1, "device_id": "deck",
                "games": {"wario": {"sram": {"last_synced_sha256": None}}}}
        with tempfile.TemporaryDirectory() as folder:
            games = load_baseline(self.write(folder, data), "deck")
            self.assertIsNone(baseline_hash(games, "wario"))


if __name__ == "__main__":
    unittest.main()
