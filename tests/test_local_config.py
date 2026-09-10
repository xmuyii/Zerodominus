import importlib
import os
import sys
import unittest


class LocalConfigTests(unittest.TestCase):
    def setUp(self):
        self.original_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)
        sys.modules.pop("config", None)

    def test_bot_token_prefers_bot_token_env_var(self):
        os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
        os.environ["API_TOKEN"] = "placeholder"
        os.environ["ENVIRONMENT"] = "prod"

        config = importlib.import_module("config")
        self.assertEqual(config.BOT_TOKEN, "123456:TESTTOKEN")


if __name__ == "__main__":
    unittest.main()
