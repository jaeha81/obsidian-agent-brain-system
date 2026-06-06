"""
Pytest session configuration.

test_daily_plus_discord_intake.py imports discord_bot.py, which monkey-patches
builtins.print and modifies sys.stdout at module level. Under Python 3.14, this
interacts badly with pytest's capture tmpfile during teardown (ValueError: I/O
operation on closed file). Run that file via:
    python -m unittest tests.test_daily_plus_discord_intake
"""
collect_ignore = ["tests/test_daily_plus_discord_intake.py"]
