from __future__ import absolute_import
import os
import sys
import re
import json
import operator
import itertools
import sqlite3
import pickle
import logging
import hashlib
from collections import defaultdict
from os.path import expanduser


basepath = os.path.dirname(__file__)
NUBASE_PATH = os.path.abspath(os.path.join(basepath, "../db/nubtab12.asc"))
LENRMC_DIR = os.path.join(expanduser('~'), '.lenrmc')


ALTERNATE_LABELS = {
    '1 n':  'n',
    '1H':   'p',
    '2H':   'd',
    '3H':   't',
    '12Cx': '12C',
    '10Bx': '10B',
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


def make_connection():
    try:
        os.mkdir(LENRMC_DIR, 0o755)
    except OSError:
        pass
    conn = sqlite3.connect('{}/lenrmc.db'.format(LENRMC_DIR))
    try:
        conn.execute("""
        create table reactions (parents text, reaction text, q_value_kev real)
        """)
    except sqlite3.OperationalError:
        pass
    return conn


class RejectCombination(RuntimeError):
    pass


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

    _noteworthy = {
        'B-': '→β-',
        'B+': '→β+',
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
        self.notes = set()
        for lvalue, note in self._noteworthy.items():
            if lvalue in decays:
                self.notes.add(note)
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


def vectors3(integer):
    for i in range(integer):
        j = integer - i
        for k in range(j):
            yield (j - k, k, i)


def possible_daughters(totals):
    mass_number, atomic_number = totals
    seen = set()
    for masses in vectors3(mass_number):
        for protons in vectors3(atomic_number):
            pairs = []
            try:
                for i, m in enumerate(masses):
                    p = protons[i]
                    if m < p:
                        raise RejectCombination
                    pair = (m, p)
                    if (0, 0) == pair:
                        continue
                    pairs.append(pair)
            except RejectCombination:
                continue
            pairs = tuple(sorted(pairs))
            if pairs in seen:
                continue
            seen.add(pairs)
            yield pairs


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


class Combinations(object):

    _connection = None

    @classmethod
    def load(cls, **kwargs):
        reactants = kwargs['reactants']
        del kwargs['reactants']
        return cls(reactants, **kwargs)

    def __init__(self, reactants, **kwargs):
        self._reactants = list(reactants)
        self._kwargs = kwargs
        self._lower_bound = float(kwargs['lower_bound']) if 'lower_bound' in kwargs else None
        self.cache_key = self._cache_key()

    def _cache_key(self):
        parents = [(num, n.signature) for num, n in sorted(self._reactants, key=self._sort_key)]
        signature = {'parents': parents}
        for field in ('lower_bound',):
            signature['lower_bound'] = self._kwargs.get('lower_bound')
        string = json.dumps(signature, sort_keys=True).encode('utf-8')
        key = hashlib.sha1(string).hexdigest()
        return key

    def _outcomes(self):
        numbers = [num * n.numbers for num, n in self._reactants]
        mass_number, atomic_number = tuple(map(operator.add, *numbers))
        return possible_daughters((mass_number, atomic_number))

    def _daughters(self):
        nuclides = Nuclides.db()
        pairs = []
        for _pairs in self._outcomes():
            daughters = [nuclides.isomers[pair] for pair in _pairs]
            if not all(daughters):
                continue
            yield from itertools.product(*daughters)

    def reactions(self):
        results = self._cached_results()
        if results:
            yield from results
        else:
            results = []
            for daughters in self._daughters():
                rvalues = ((1, d) for d in daughters)
                r = Reaction(self._reactants, rvalues)
                if not self._allowed(r):
                    continue
                yield r
                results.append(r)
            self._cache_results(results)

    def _allowed(self, r):
        return self._lower_bound is None or r.q_value_kev > self._lower_bound

    def _sort_key(self, pair):
        num, nuclide = pair
        return nuclide.signature

    @property
    def connection(self):
        if self._connection is None:
            self._connection = make_connection()
        return self._connection

    def _cached_results(self):
        cursor = self.connection.execute(
            "select reaction from reactions where parents = ?",
            (self.cache_key,))
        array = list(cursor)
        if array:
            logging.info('reading previously computed values from cache')
            return (pickle.loads(r[0]) for r in array)
        return None

    def _cache_results(self, results):
        self.connection.executemany("""
        insert into reactions (parents, reaction) values (?, ?)
        """, ((self.cache_key, pickle.dumps(r)) for r in results))
        self.connection.commit()

    def __repr__(self):
        return 'Combinations({})'.format(self._reactants)


class System(object):

    @classmethod
    def parse(cls, string, **kwargs):
        system = filter(None, (rs.strip() for rs in string.split(',')))
        combinations = []
        for spec in system:
            for reactants in cls._parse_spec(spec):
                c = Combinations.load(reactants=reactants, **kwargs)
                combinations.append(c)
        return cls(combinations, **kwargs)

    @classmethod
    def _parse_spec(cls, spec):
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

    def __init__(self, combinations, **kwargs):
        self._combinations = list(combinations)
        self._kwargs = kwargs

    def reactions(self):
        for c in self._combinations:
            yield from c.reactions()
