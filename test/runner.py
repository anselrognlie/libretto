# pylint: disable=missing-module-docstring

import unittest

import test.test_line_type
import test.test_search_conditional
import test.test_line
import test.test_track

# initialize the test suite
loader = unittest.TestLoader()
suite  = unittest.TestSuite()

# add tests to the test suite
suite.addTests(loader.loadTestsFromModule(test.test_line_type))
suite.addTests(loader.loadTestsFromModule(test.test_search_conditional))
suite.addTests(loader.loadTestsFromModule(test.test_line))
suite.addTests(loader.loadTestsFromModule(test.test_track))

# initialize a runner, pass it your suite and run it
runner = unittest.TextTestRunner(verbosity=3)
result = runner.run(suite)
