"""Unified CLI dispatcher for ravel_bench.

Subcommands:
  infer   --mode {end2end,ravel}   run inference (direct or agentic RAVEL)
  eval    --mode {c3ebench,ravel}  judge outputs with a swappable --judge_model
  results                          regenerate the main results table from CSVs

Run from the repository root:  python -m ravel_bench <subcommand> ...
"""
import argparse

from . import config


def _add_common(p):
    p.add_argument("--lang", default="en", help="en/zh (aliases: english/chinese)")
    p.add_argument("--limit", type=int, default=None, help="cap #items (smoke tests)")
    p.add_argument("--dry-run", action="store_true", help="print plan + cost, do not call the API")


def build_parser():
    ap = argparse.ArgumentParser(prog="python -m ravel_bench")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # ---- infer ----
    pi = sub.add_parser("infer", help="run inference (end2end or ravel)")
    pi.add_argument("--mode", required=True, choices=["end2end", "ravel"])
    pi.add_argument("--model_name", required=True)
    pi.add_argument("--input_file", default=None)
    pi.add_argument("--output_dir", default=None, help="where to write (never a protected result dir)")
    pi.add_argument("--workers", type=int, default=20)
    _add_common(pi)
    # ravel-only
    pi.add_argument("--tau", type=float, default=config.DEFAULT_TAU)
    pi.add_argument("--protocol", default="autonomous", choices=list(config.PROTOCOLS))
    pi.add_argument("--max_steps", type=int, default=config.DEFAULT_T_MAX)
    pi.add_argument("--max_revisions", type=int, default=config.DEFAULT_MAX_REVISIONS)
    pi.add_argument("--planner_model", default=None)
    pi.add_argument("--writer_model", default=None)
    pi.add_argument("--reviewer_model", default=None)
    pi.add_argument("--revisor_model", default=None)

    # ---- eval ----
    pe = sub.add_parser("eval", help="judge outputs (configurable --judge_model)")
    pe.add_argument("--mode", required=True, choices=["c3ebench", "ravel"])
    pe.add_argument("--judge_model", default=config.DEFAULT_JUDGE_MODEL)
    pe.add_argument("--model_name", default=None, help="tested model (c3ebench mode)")
    pe.add_argument("--input_file", default=None, help="c3ebench: inference jsonl to judge")
    pe.add_argument("--root_dir", default=None, help="ravel: dir of <infer_id>/ run dirs")
    pe.add_argument("--dataset_file", default=None, help="ravel: dataset for references")
    pe.add_argument("--model_tag", default=None, help="ravel: label for the output file")
    pe.add_argument("--output_dir", default=None)
    pe.add_argument("--workers", type=int, default=10)
    _add_common(pe)

    # ---- results ----
    pr = sub.add_parser("results", help="regenerate the main results table from evaluation_results/")
    pr.add_argument("--lang", default="english")

    return ap


def _role_models(args):
    rm = {}
    if args.planner_model:
        rm["planner"] = args.planner_model
    if args.writer_model:
        rm["writer"] = args.writer_model
    if args.reviewer_model:
        rm["reviewer"] = args.reviewer_model
    if args.revisor_model:
        rm["revisor"] = args.revisor_model
    return rm or None


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.cmd == "infer":
        from . import inference
        if args.mode == "end2end":
            inference.run_end2end(args.lang, args.model_name, args.input_file,
                                  args.output_dir, args.workers, args.limit, args.dry_run)
        else:
            inference.run_ravel(args.lang, args.model_name, args.input_file, args.output_dir,
                                args.workers, args.tau, args.protocol, _role_models(args),
                                args.max_steps, args.max_revisions, args.limit, args.dry_run)

    elif args.cmd == "eval":
        from . import evaluate
        if args.mode == "c3ebench":
            if not args.model_name:
                raise SystemExit("--model_name is required for --mode c3ebench")
            evaluate.eval_c3ebench(args.lang, args.model_name, args.judge_model,
                                   args.input_file, args.output_dir, args.workers,
                                   args.limit, args.dry_run)
        else:
            if not args.root_dir:
                raise SystemExit("--root_dir is required for --mode ravel")
            evaluate.eval_ravel(args.lang, args.root_dir, args.judge_model,
                                args.dataset_file, args.output_dir, args.model_tag,
                                args.workers, args.limit, args.dry_run)

    elif args.cmd == "results":
        from . import results
        results.main(args.lang)


if __name__ == "__main__":
    main()
