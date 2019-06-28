#!/usr/local/bin/python3

import unittest

import test_LineType
import test_SearchConditional
import test_Line
import test_Track

# initialize the test suite
loader = unittest.TestLoader()
suite  = unittest.TestSuite()

# add tests to the test suite
suite.addTests(loader.loadTestsFromModule(test_LineType))
suite.addTests(loader.loadTestsFromModule(test_SearchConditional))
suite.addTests(loader.loadTestsFromModule(test_Line))
suite.addTests(loader.loadTestsFromModule(test_Track))

# initialize a runner, pass it your suite and run it
runner = unittest.TextTestRunner(verbosity=3)
result = runner.run(suite)
