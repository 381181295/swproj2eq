import os
import tempfile
import unittest

from swproj2eq.state.store import load_state, save_state


class StateStoreTests(unittest.TestCase):
    def test_save_and_load_state(self):
        old_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as td:
            os.environ["HOME"] = td
            state = load_state()
            state["active_profile_id"] = "abc123"
            save_state(state)

            loaded = load_state()
            self.assertEqual(loaded["active_profile_id"], "abc123")
            self.assertIn("runtime", loaded)
        if old_home is not None:
            os.environ["HOME"] = old_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
