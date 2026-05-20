import core.utils
import pandas as pd


def run(args):
    pd.options.display.max_colwidth = None
    pd.options.display.max_rows = None
    print(core.utils.load(args.t).tail(n=args.n))
