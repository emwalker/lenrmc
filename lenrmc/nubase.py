from __future__ import absolute_import
import os
import sys
import re
import operator
import itertools
from collections import defaultdict


basepath = os.path.dirname(__file__)
NUBASE_PATH = os.path.abspath(os.path.join(basepath, "../db/nubtab12.asc"))


ALTERNATE_LABELS = {
    '1 n':  'n',
    '1H':   'p',
    '2H':   'd',
    '3H':   't',
    '12Cx': '12C',
    '10Bx': '10B',
    '30Px': '30P',
}

ELEMENTS = {
    'n':  0,
    'H':  1,
    'He': 2,
    'Li': 3,
    'C':  6,
    'Fe': 26,
    'Ni': 28,
    'Pd': 46,
}


class BadNubaseRow(RuntimeError):
    pass


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


def first_match(pattern, string):
    match = re.search(pattern, string)
    if not match:
        return None
    return match.group()


class Nuclide(object):

    _columns = (
        (  4, 'massNumber'              ),
        (  7, 'atomicNumber'            ),
        (  9, 'atomicNumberExtra'       ),
        ( 18, 'nuclide'                 ),
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

    _not_excited = {
        '1 n',
        '3Li',
        '4Li',
        '4H',
        '5H',
        '5He',
        '5Li',
        '6He',
        '8Be',
        '59Ni',
    }

    @classmethod
    def load(cls, **kwargs):
        line = kwargs['line']
        row = {}
        endcol_prev = 0
        for endcol, field in cls._columns:
            text = line[endcol_prev:endcol].strip()
            if text:
                row[field] = text
            endcol_prev = endcol
        return cls(row)

    def __init__(self, row):
        if not 'massExcess' in row:
            raise BadNubaseRow('no mass excess: {}'.format(row))
        self._row = row
        self._label = row['nuclide']
        self.atomic_number = int(first_match(r'\d+', self._row['atomicNumber']))
        self.mass_number = int(self._row['massNumber'])
        decays = self._row.get('decayModesAndIntensities', '')
        g = re.search(r'IS=([\d\.]+)', decays)
        self.isotopic_abundance = float(g.group(1)) if g else 0.
        self.is_stable = g is not None
        self.numbers = (self.mass_number, self.atomic_number)
        if self.is_excited:
            label, self._excitation_level = self._label[:-1], self._label[-1]
            self.label = ALTERNATE_LABELS.get(label, label)
            self.full_label = '{} ({})'.format(self.label, self._excitation_level)
        else:
            label, self._excitation_level = self._label, '0'
            self.label = ALTERNATE_LABELS.get(label, label)
            self.full_label = self.label
        self.signature = (self.label, self._excitation_level)
        kev = first_match(r'[\d\.\-]+', self._row['massExcess'])
        self.mass_excess_kev = float(kev)
        self.spin_and_parity = None
        if 'spinAndParity' in self._row:
            self.spin_and_parity = ' '.join(self._row['spinAndParity'].split())

    _noteworthy = {
        'A':    '→α',
        'B-':   '→β-',
        'B+':   '→β+',
        'B+p':  '→β+p',
        'B+A':  '→β+α',
        'B-n':  '→β-n',
        'B-2n': '→β-2n',
        'B-3n': '→β-3n',
        'B+SF': '→β+SF',
        'B-SF': '→β-SF',
        'B-A':  '→β-α',
        'B-d':  '→β-d',
        'n':    '→n',
        '2n':   '→2n',
        'p':    '→p',
        '2p':   '→2p',
        'EC':   '→ε',
        'IT':   '→IT',
        'SF':   '→SF',
    }

    @property
    def notes(self):
        it = re.split(r'[;=~<]', self._row.get('decayModesAndIntensities', ''))
        return {self._noteworthy.get(token) for token in filter(None, it)} - {None}

    @property
    def is_excited(self):
        if self.isotopic_abundance:
            return False
        if self._label in self._not_excited:
            return False
        return any(self._label.endswith(s) for s in 'ijmnpqrx')

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

    def __eq__(self, o):
        return self.signature == o.signature

    def __hash__(self):
        return hash(self.signature)

    def __repr__(self):
        return 'Nuclide({})'.format(self.full_label)


class Nuclides(object):

    _nuclides = None

    @classmethod
    def db(cls):
        if cls._nuclides is None:
            cls._nuclides = cls.load(path=NUBASE_PATH)
        return cls._nuclides

    @classmethod
    def load(cls, **kwargs):
        path = kwargs['path']
        nuclides = []
        with open(path) as fh:
            for line in fh:
                try:
                    n = Nuclide.load(line=line)
                    nuclides.append(n)
                except BadNubaseRow:
                    continue
        return cls(nuclides)

    def __init__(self, nuclides):
        self._nuclides = list(nuclides)
        self._by_label = {}
        self._by_signature = {}
        self._by_atomic_number = defaultdict(list)
        self.isomers = defaultdict(list)
        for n in self._nuclides:
            self._by_label[n._label] = n
            self._by_signature[n.signature] = n
            self._by_atomic_number[n.atomic_number].append(n)
            self.isomers[n.numbers].append(n)

    def atomic_number(self, number):
        return self._by_atomic_number[number]

    def get(self, signature):
        return self._by_signature.get(signature)

    def __getitem__(self, signature):
        return self._by_signature[signature]


class GammaPhoton(object):

    def __init__(self):
        self.mass_number = 0
        self.full_label = self.label = 'ɣ'
        self.is_stable = False
        self.spin_and_parity = '1-'
        self.numbers = (0, 0)
        self.notes = {'ɣ'}


class Reaction(object):

    @classmethod
    def load(cls, **kwargs):
        nuclides = Nuclides.db()
        reactants = ((num, nuclides[s]) for num, s in kwargs['reactants'])
        daughters = ((num, nuclides[s]) for num, s in kwargs['daughters'])
        return cls(reactants, daughters)

    _noteworthy = {
        '4He': 'α',
        'n':   'n',
        't':   't',
    }

    def __init__(self, lvalues, rvalues):
        self._lvalues = list(lvalues)
        self._rvalues = list(rvalues)
        self.q_value_kev = self._q_value_kev()
        self.is_stable = self._is_stable()

    @property
    def notes(self):
        notes = set()
        for _, d in self._rvalues:
            note = self._noteworthy.get(d.label)
            if note:
                notes.add(note)
            for _, p in self._lvalues:
                if self._neutron_transfer(d, p):
                    notes.add('n-transfer')
        if self.is_stable:
            notes.add('stable')
        if self.has_gamma:
            notes.add('ɣ')
            self._rvalues.append((1, GammaPhoton()))
        for num, d in self._rvalues:
            notes |= d.notes
        return notes

    def _neutron_transfer(self, d, p):
        return d.numbers == tuple(map(operator.add, p.numbers, (1, 0)))

    def _is_stable(self):
        return all(d.is_stable for num, d in self._rvalues)

    @property
    def has_gamma(self):
        if 1 < len(self._rvalues):
            return False
        return all(num == 1 for num, c in self._rvalues)

    def _q_value_kev(self):
        lvalues = sum(num * i.mass_excess_kev for num, i in self._lvalues)
        rvalues = sum(num * i.mass_excess_kev for num, i in self._rvalues)
        return lvalues - rvalues


def parse_spec(spec):
    nuclides = Nuclides.db()
    reactants = []
    for label in (l.strip() for l in spec.split('+')):
        n = nuclides.get((label, '0'))
        if n:
            reactants.append([(1, n)])
        else:
            number = ELEMENTS[label]
            ns = nuclides.atomic_number(number)
            reactants.append((1, n) for n in ns if n.is_stable)
    return itertools.product(*reactants)
