import unittest

from lenrmc.nubase import System
from lenrmc.terminal import TerminalView, TerminalLine, StudiesTerminalView


class SystemTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.maxDiff = None

    def test_outcomes(self):
        s = System.parse('p+7Li')
        outcomes = list(s._combinations[0]._outcomes())
        self.assertEqual(42, len(outcomes))
        self.assertEqual(((8, 4),), outcomes[0])

    def test_spins(self):
        s = System.parse('p+7Li')
        self.assertEqual(
            ['p + 7Li → 2·4He + 17346 keV                             4He, stable               1/2+, 3/2-           0+, 0+',
             'p + 7Li → ɣ + 8Be + 17254 keV                           ɣ                         1/2+, 3/2-           0+, 1-',
             'p + 7Li → ɣ + 8Be (i) + 628 keV                         ɣ                         1/2+, 3/2-           1-, 2+ frg T=1',
             'p + 7Li → 2·d + 4He + -6500 keV                         4He, n-transfer, stable   1/2+, 3/2-           0+, 1+, 1+',
             'p + 7Li → d + 6Li + -5027 keV                           n-transfer, stable        1/2+, 3/2-           1+, 1+',
             'p + 7Li → p + 7Li + 0 keV                               stable                    1/2+, 3/2-           1/2+, 3/2-',
             'p + 7Li → d + 6Li (i) + -8589 keV                       n-transfer                1/2+, 3/2-           0+ T=1, 1+',
             'p + 7Li → p + d + 5He + -9460 keV                       n-transfer                1/2+, 3/2-           1+, 1/2+, 3/2-',
             'p + 7Li → d + 3He + t + -20821 keV                      n-transfer, t             1/2+, 3/2-           1+, 1/2+, 1/2+',
             'p + 7Li → p + t + 4He + -2468 keV                       4He, t                    1/2+, 3/2-           0+, 1/2+, 1/2+',
             'p + 7Li → 3He + 5He + -3966 keV                                                   1/2+, 3/2-           1/2+, 3/2-',
             'p + 7Li → t + 5Li + -4434 keV                           t                         1/2+, 3/2-           1/2+, 3/2-',
             'p + 7Li → 2·p + 6He + -9974 keV                                                   1/2+, 3/2-           0+, 1/2+, 1/2+',
             'p + 7Li → p + 7Li (i) + -11243 keV                                                1/2+, 3/2-           1/2+, 3/2- T=3/2',
             'p + 7Li → p + 3He + 4H + -24644 keV                                               1/2+, 3/2-           1/2+, 1/2+, 2-',
             'p + 7Li → 4H + 4Li + -27744 keV                                                   1/2+, 3/2-           2-, 2-',
             'p + 7Li → 3Li + 5H + -39364 keV                                                   1/2+, 3/2-           (1/2+)',
             'p + 7Li → n + d + 5Li + -10691 keV                      n, n-transfer             1/2+, 3/2-           1+, 1/2+, 3/2-',
             'p + 7Li → n + 3He + 4He + -3231 keV                     4He, n                    1/2+, 3/2-           0+, 1/2+, 1/2+',
             'p + 7Li → ɣ + 8Be (j) + -10240 keV                      ɣ                         1/2+, 3/2-           0+ T=2, 1-',
             'p + 7Li → n + 7Be + -1644 keV                           n                         1/2+, 3/2-           1/2+, 3/2-',
             'p + 7Li → n + p + 6Li + -7251 keV                       n                         1/2+, 3/2-           1+, 1/2+, 1/2+',
             'p + 7Li → n + p + 6Li (i) + -10814 keV                  n                         1/2+, 3/2-           0+ T=1, 1/2+, 1/2+',
             'p + 7Li → 2·n + 6Be + -12322 keV                        n                         1/2+, 3/2-           0+, 1/2+, 1/2+',
             'p + 7Li → n + 7Be (i) + -12625 keV                      n                         1/2+, 3/2-           1/2+, 3/2- T=3/2',
             'p + 7Li → n + t + 4Li + -26145 keV                      n, t                      1/2+, 3/2-           1/2+, 1/2+, 2-',
             'p + 7Li → n + 3Li + 4H + -39165 keV                     n                         1/2+, 3/2-           1/2+, 2-']
        , TerminalView(s).lines(spins=True))

    def test_references(self):
        s = System.parse('p+7Li')
        self.assertEqual(
            ['p + 7Li → 2·4He + 17346 keV                             4He, stable',
             'p + 7Li → ɣ + 8Be + 17254 keV                           ɣ',
             'p + 7Li → ɣ + 8Be (i) + 628 keV                         ɣ',
             'p + 7Li → 2·d + 4He + -6500 keV                         4He, n-transfer, stable',
             'p + 7Li → d + 6Li + -5027 keV                           n-transfer, stable          ✓ 6Li [L15]',
             'p + 7Li → p + 7Li + 0 keV                               stable                      ✗ 7Li [L15]',
             'p + 7Li → d + 6Li (i) + -8589 keV                       n-transfer                  ✓ 6Li [L15]',
             'p + 7Li → p + d + 5He + -9460 keV                       n-transfer',
             'p + 7Li → d + 3He + t + -20821 keV                      n-transfer, t',
             'p + 7Li → p + t + 4He + -2468 keV                       4He, t',
             'p + 7Li → 3He + 5He + -3966 keV',
             'p + 7Li → t + 5Li + -4434 keV                           t',
             'p + 7Li → 2·p + 6He + -9974 keV',
             'p + 7Li → p + 7Li (i) + -11243 keV                                                  ✗ 7Li [L15]',
             'p + 7Li → p + 3He + 4H + -24644 keV',
             'p + 7Li → 4H + 4Li + -27744 keV',
             'p + 7Li → 3Li + 5H + -39364 keV',
             'p + 7Li → n + d + 5Li + -10691 keV                      n, n-transfer',
             'p + 7Li → n + 3He + 4He + -3231 keV                     4He, n',
             'p + 7Li → ɣ + 8Be (j) + -10240 keV                      ɣ',
             'p + 7Li → n + 7Be + -1644 keV                           n',
             'p + 7Li → n + p + 6Li + -7251 keV                       n                           ✓ 6Li [L15]',
             'p + 7Li → n + p + 6Li (i) + -10814 keV                  n                           ✓ 6Li [L15]',
             'p + 7Li → 2·n + 6Be + -12322 keV                        n',
             'p + 7Li → n + 7Be (i) + -12625 keV                      n',
             'p + 7Li → n + t + 4Li + -26145 keV                      n, t',
             'p + 7Li → n + 3Li + 4H + -39165 keV                     n',
             '',
             '[L15] 2015 Lugano E-Cat test by Levi et al.']
        , TerminalView(s).lines(references=True))

    def test_reactions_2(self):
        s = System.parse('6Li+6Li')
        t = TerminalView(s)
        self.assertTrue(any('2·6Li → 3·4He + 20899 keV' in l for l in t.lines()))

    def test_element_shorthand(self):
        s = System.parse('H+Li')
        self.assertEqual(4, len(s._combinations))


class TestStudiesView(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.maxDiff = None

    def test_output(self):
        s = System.parse('p+7Li')
        v = StudiesTerminalView(s)
        self.assertEqual(
            ['p + 7Li → d + 6Li + -5027 keV                           n-transfer, stable          ✓ 6Li [L15]',
             'p + 7Li → d + 6Li (i) + -8589 keV                       n-transfer                  ✓ 6Li [L15]',
             'p + 7Li → t + 5Li + -4434 keV                           t',
             'p + 7Li → 3He + 5He + -3966 keV',
             'p + 7Li → 3Li + 5H + -39364 keV',
             'p + 7Li → 4H + 4Li + -27744 keV',
             'p + 7Li → 2·4He + 17346 keV                             4He, stable',
             'p + 7Li → 2·p + 6He + -9974 keV',
             'p + 7Li → p + d + 5He + -9460 keV                       n-transfer',
             'p + 7Li → p + t + 4He + -2468 keV                       4He, t',
             'p + 7Li → p + 3He + 4H + -24644 keV',
             'p + 7Li → 2·d + 4He + -6500 keV                         4He, n-transfer, stable',
             'p + 7Li → d + 3He + t + -20821 keV                      n-transfer, t',
             'p + 7Li → p + 7Li + 0 keV                               stable                      ✗ 7Li [L15]',
             'p + 7Li → p + 7Li (i) + -11243 keV                                                  ✗ 7Li [L15]',
             '',
             '[L15] 2015 Lugano E-Cat test by Levi et al.']
        , v.lines(references=True))