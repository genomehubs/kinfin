#!/usr/bin/env python3

import cli

if __name__ == "__main__":
    args = cli.args.get_argparse()
    if not args.command == "serve":
        if args.command == "analysis":
            cli.analyse.run(args)
        elif args.command == "bed":
            cli.bed.run(args)
        elif args.command == "plot":
            cli.plot.run(args)
        elif args.command == "view":
            cli.view.run(args)
        elif args.command == "head":
            cli.head.run(args)
        elif args.command == "tail":
            cli.tail.run(args)
        elif args.command == "preprocess":
            cli.preprocess.run(args)
        elif args.command == "convert":
            cli.convert.run(args)
        elif args.command == "taxid":
            cli.taxid.run(args)
        else:
            pass
    # else:
    #     run_server(
    #         args=args,
    #         nodesdb_f=args.nodesdb_f,
    #         go_mapping_f=args.go_mapping_f,
    #         ipr_mapping_f=args.ipr_mapping_f,
    #         pfam_mapping_f=args.pfam_mapping_f,
    #         cluster_f="",  # dummy
    #         sequence_ids_f="",  # dummy
    #         taxon_idx_mapping_file="",  # dummy
    #     )
