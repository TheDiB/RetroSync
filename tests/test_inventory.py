import tempfile
import unittest
from pathlib import Path

from retro_sync import classify, digest, inventory


class InventoryTests(unittest.TestCase):
    def test_classify(self):
        base = "Example Game"
        self.assertEqual(classify(base + ".srm", base), "SRAM")
        self.assertEqual(classify(base + ".state", base), "STATE")
        self.assertEqual(classify(base + ".state10", base), "STATE")
        self.assertIsNone(classify(base + ".state.png", base))
        self.assertIsNone(classify(base + ".stateX", base))

    def test_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "Example Game.srm").write_bytes(b"save")
            (folder / "Example Game.state1").write_bytes(b"state")
            (folder / "Other.srm").write_bytes(b"ignored")
            result = inventory(folder, "Example Game")
            self.assertEqual(set(result), {"Example Game.srm", "Example Game.state1"})
            self.assertEqual(result["Example Game.srm"]["sha256"], digest(folder / "Example Game.srm"))


if __name__ == "__main__":
    unittest.main()
