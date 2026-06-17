import core.utils


def run(args):
    core.utils.dump(
        core.utils.load(args.t),
        fn=core.utils.format_fn(
            args.t,
            prefix=".",
            suffix=f".{args.F}",
        ),
        index=args.i,
    )
