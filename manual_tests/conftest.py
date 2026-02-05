import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-manual-tests",
        action="store_true",
        default=False,
        help="Run manual tests that require real network/auth/session state.",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-manual-tests"):
        return
    skip_manual = pytest.mark.skip(
        reason="manual test skipped (use --run-manual-tests to enable)"
    )
    for item in items:
        if "manual" in item.keywords:
            item.add_marker(skip_manual)
