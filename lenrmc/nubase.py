import os
import sys
import re


basepath = os.path.dirname(__file__)
DB_PATH = os.path.abspath(os.path.join(basepath, "../db/nubtab12.asc"))


class HalfLife(object):

    def __init__(self, value, unit):
        self.value = value
        self.unit = unit

    @property
    def seconds(self):
        if 's' == self.unit:
            return float(self.value)
        raise ValueError('do not know how to convert unit: {}'.format(self.unit))

    def __str__(self):
        return '{} {}'.format(self.value, self.unit)


class Nuclide(object):

    COLUMNS = (
        (  4, 'id'                      ),
        (  9, 'atomicNumber'            ),
        ( 19, 'nuclide'                 ),
        ( 39, 'massExcess'              ),
        ( 61, 'excitationEnergy'        ),
        ( 69, 'halfLife'                ),
        ( 71, 'halfLifeUnit'            ),
        ( 79, 'unknown'                 ),
        ( 93, 'spinAndParity'           ),
        ( 96, 'ensdfArchiveFileYear'    ),
        (105, 'reference'               ),
        (110, 'yearOfDiscovery'         ),
        ( -1, 'decayModesAndIntensities'),
    )

    @classmethod
    def load(cls, **kwargs):
        line = kwargs['line']
        row = {}
        endcol_prev = 0
        for endcol, field in cls.COLUMNS:
            text = line[endcol_prev:endcol]
            row[field] = text.strip()
            endcol_prev = endcol
        return cls(row)

    def __init__(self, row):
        self._row = row
        self.label = row['nuclide']
        self.atomic_number = int(re.search(r'\d+', self._row['atomicNumber']).group())
        self.mass_number = int(re.search(r'\d+', self._row['nuclide']).group())
        g = re.search(r'IS=([\d\.]+)', self._row['decayModesAndIntensities'])
        self.isotopic_abundance = float(g.group(1)) if g else 0.

    @property
    def half_life(self):
        return HalfLife(self._row['halfLife'], self._row['halfLifeUnit'])

    def json(self):
        return {
            'halfLife':     self.half_life.seconds,
            'atomicNumber': self.atomic_number,
            'massNumber':   self.mass_number,
        }

    def __iter__(self):
        return self.json().iteritems()


class Nuclides(object):

    _nuclides = None

    @classmethod
    def get(cls):
        if cls._nuclides is None:
            cls._nuclides = cls.load(path=DB_PATH)
        return cls._nuclides

    @classmethod
    def load(cls, **kwargs):
        path = kwargs['path']
        with open(path) as fh:
            nuclides = [Nuclide.load(line=l) for l in fh]
        return cls(nuclides)

    def __init__(self, nuclides):
        self._nuclides = list(nuclides)
        self._by_label = {}
        for n in self._nuclides:
            self._by_label[n.label] = n

    def __getitem__(self, label):
        return self._by_label[label]
