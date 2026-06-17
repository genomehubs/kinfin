import pandas as pd

import core.utils


def run(args):
    pd.options.display.max_colwidth = None
    pd.options.display.max_rows = None
    pd.options.display.max_columns = None
    print(core.utils.load(args.t).head(n=args.n))
