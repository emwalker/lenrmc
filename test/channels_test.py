import unittest
from lenrmc.base import *


class ChannelsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = Engine.from_csv('fixtures/materials.csv', 'fixtures/channels.csv')
        cls.channel = cls.engine.generations[-1].channel_for('58Ni(d,p)59Ni',  'Ni K x-rays')

    def test_escaping_photons(self):
        values = self.channel.df[['material', 'escaping_photons']].values.tolist()
        self.assertEqual(values, [['lead (1cm)', 0.0], ['lead (2cm)', 0.0], ['lead (5cm)', 0.0]])


if __name__ == '__main__':
    unittest.main()