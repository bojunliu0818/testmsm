# Author: Robert McGibbon <rmcgibbo@gmail.com>
# Contributors:
# Copyright (c) 2014, Stanford University
# All rights reserved.

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from __future__ import print_function, division, absolute_import
import os
import sys
import json

import pandas as pd

from ..dataset import dataset
from ..cmdline import Command, argument, argument_group, rangetype, FlagAction
from ..msm import MarkovStateModel, implied_timescales


class ImpliedTimescales(Command):
    _group = 'MSM'
    _concrete = True
    description = "Scan the implied timescales of `MarkovStateModel`s with respect to lag time"
    lag_times = argument('-l', '--lag_times', default='1:10', type=rangetype, help='''
        Range of lag times. Specify as 'start:stop' or 'start:stop:step. The endpoints
        are inclusive.''')
    inp = argument(
        '-i', '--inp', help='''Path to input dataset, a collection of 1D integer sequences
        (such as the output from clustering)''', required=True)
    out = argument('--out', help='''Output file''',
        default='timescales.csv')
    fmt = argument('--fmt', help='Output file format', default='csv',
        choices=('csv', 'json', 'excel'))
    _extensions = {'csv': '.csv', 'json': '.json', 'excel': '.xlsx'}

    n_jobs = argument('--n_jobs', help='Number of parallel processes', default=1)

    p = argument_group('MSM parameters')
    n_timescales = p.add_argument('--n_timescales', default=10, help='''
        The number of dynamical timescales to calculate when diagonalizing
        the transition matrix.''',  type=int)
    reversible_type = p.add_argument('--reversible_type', default='mle', help='''
        Method by which the reversibility of the transition matrix
        is enforced. 'mle' uses a maximum likelihood method that is
        solved by numerical optimization, and 'transpose'
        uses a more restrictive (but less computationally complex)
        direct symmetrization of the expected number of counts.''',
        choices=('mle', 'transpose'))
    ergodic_cutoff = p.add_argument('--ergodic_cutoff', default=1, type=int, help='''
        Only the maximal strongly ergodic subgraph of the data is used to build
        an MSM. Ergodicity is determined by ensuring that each state is
        accessible from each other state via one or more paths involving edges
        with a number of observed directed counts greater than or equal to
        ``ergodic_cutoff``. Not that by setting ``ergodic_cutoff`` to 0, this
        trimming is effectively turned off.''')
    prior_counts = p.add_argument('--prior_counts', default=0, help='''Add a number
        of "pseudo counts" to each entry in the counts matrix. When
        prior_counts == 0 (default), the assigned transition probability
        between two states with no observed transitions will be zero, whereas
        when prior_counts > 0, even this unobserved transitions will be
        given nonzero probability.''', type=float)
    verbose = p.add_argument('--verbose', default=True,
        help='Enable verbose printout', action=FlagAction)

    def __init__(self, args):
        self.args = args

    def start(self):
        ds = dataset(self.args.inp, mode='r')
        kwargs = {
            'n_timescales': self.args.n_timescales,
            'reversible_type': self.args.reversible_type,
            'ergodic_cutoff': self.args.ergodic_cutoff,
            'prior_counts': self.args.prior_counts,
            'verbose': self.args.verbose,
        }
        model = MarkovStateModel(**kwargs)
        lines = implied_timescales(
            ds, lag_times=self.args.lag_times, n_timescales=self.args.n_timescales,
            msm=model, n_jobs=self.args.n_jobs, verbose=self.args.verbose)

        cols = ['Timescale %d' % (d+1) for d in range(len(lines[0]))]
        df = pd.DataFrame(data=lines, columns=cols)
        df['Lag Time'] = self.args.lag_times
        df = df.reindex_axis(sorted(df.columns), axis=1)
        self.write_output(df)
        ds.close()

    def write_output(self, df):
        outfile = os.path.splitext(self.args.out)[0] + self._extensions[self.args.fmt]

        print('Writing %s' % outfile)
        if self.args.fmt == 'csv':
            df.to_csv(outfile)
        elif self.args.fmt == 'json':
            with open(outfile, 'w') as f:
                json.dump(df.to_dict(orient='records'), f)
        elif self.args.fmt == 'excel':
            df.to_excel(outfile)
        else:
            raise RuntimeError('unknown fmt: %s' % fmt)
        print('All done!')
