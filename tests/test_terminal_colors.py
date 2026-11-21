import unittest

from terminal_colors import colorize_status, use_color


class FakeStream:
    def __init__(self, tty):
        self.tty = tty

    def isatty(self):
        return self.tty


class TerminalColorsTests(unittest.TestCase):
    def test_auto_terminal_enables_colors(self):
        self.assertTrue(use_color("auto", FakeStream(True), {"TERM": "xterm-256color"}))

    def test_auto_redirected_output_disables_colors(self):
        self.assertFalse(use_color("auto", FakeStream(False), {"TERM": "xterm"}))

    def test_no_color_disables_auto(self):
        self.assertFalse(use_color("auto", FakeStream(True), {"NO_COLOR": "", "TERM": "xterm"}))

    def test_dumb_terminal_disables_auto(self):
        self.assertFalse(use_color("auto", FakeStream(True), {"TERM": "dumb"}))

    def test_always_and_never_override_auto(self):
        self.assertTrue(use_color("always", FakeStream(False), {"NO_COLOR": ""}))
        self.assertFalse(use_color("never", FakeStream(True), {}))

    def test_invalid_mode_rejected(self):
        with self.assertRaises(ValueError):
            use_color("sometimes", FakeStream(True), {})

    def test_status_colors_and_reset(self):
        for status, code in (("PASS", "32"), ("FAIL", "31"),
                             ("UNKNOWN", "33"), ("WARN", "33"), ("SKIP", "90")):
            self.assertEqual(colorize_status(status, True),
                             f"\x1b[{code}m[{status}]\x1b[0m")

    def test_plain_output_has_no_escape_sequences(self):
        self.assertEqual(colorize_status("FAIL", False), "[FAIL]")
        self.assertEqual(colorize_status("OTHER", True), "[OTHER]")


if __name__ == "__main__":
    unittest.main()
