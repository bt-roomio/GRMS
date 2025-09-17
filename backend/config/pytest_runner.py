import pytest
from django.test.runner import DiscoverRunner


class PytestTestRunner(DiscoverRunner):
    """Allows you to run pytest via ./manage.py test"""

    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        args = list(test_labels) if test_labels else []
        return pytest.main(args)
