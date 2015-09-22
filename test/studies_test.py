import unittest

from lenrmc.studies import Studies


class StudiesTest(unittest.TestCase):

    def test_simple_case(self):
        results = Studies.db().isotopes(['6Li'])
        self.assertEqual([
            {'shortDescription': '2015 Lugano E-Cat test by Levi et al.',
             'label': '6Li',
             'change': 'increase'}
        ], results.json)