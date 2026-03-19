from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from pep_lang.bytecode import compile_program, save_artifact
from pep_lang.parser import parse_program
from pep_lang.planner import build_plan
from pep_lang.runtime import Runtime, RuntimeErrorPep


def _load_script(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def cmd_run(args: argparse.Namespace) -> int:
    source = _load_script(args.script)
    base_path = str(Path(args.script).resolve().parent)
    runtime = Runtime(base_path=base_path)
    try:
        runtime.run_script(source)
        if runtime.servers and not args.detach:
            print("server mode active; press Ctrl+C to stop")
            try:
                while True:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                print("stopping servers...")
    except RuntimeErrorPep as exc:
        print(f"\n[erro] {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[erro inesperado] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        runtime.shutdown()
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    source = _load_script(args.script)
    base_path = str(Path(args.script).resolve().parent)
    runtime = Runtime(base_path=base_path)
    try:
        runtime.run_script(source)
        runtime._watch(args.pipeline, runtime.globals)  # intentionally exposes watch command
    except RuntimeErrorPep as exc:
        print(f"\n[erro] {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[erro inesperado] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        runtime.shutdown()
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    source = _load_script(args.script)
    program = parse_program(source)
    plan = build_plan(program, mode=args.mode)
    text = json.dumps(plan.to_dict(), indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


def cmd_compile(args: argparse.Namespace) -> int:
    source = _load_script(args.script)
    program = parse_program(source)
    artifact = compile_program(program)
    out = args.out or (str(Path(args.script).with_suffix(".pepc")))
    save_artifact(out, artifact)
    print(f"compiled to {out}")
    return 0


def cmd_repl(_: argparse.Namespace) -> int:
    runtime = Runtime()
    print("pep# REPL v0.1. Type :quit to exit.")
    try:
        while True:
            try:
                line = input("pep> ").strip()
            except EOFError:
                print()
                return 0
            if not line:
                continue
            if line in {":quit", ":exit"}:
                return 0

            try:
                runtime.run_script(line)
            except RuntimeErrorPep as exc:
                print(f"Runtime error: {exc}")
    finally:
        runtime.shutdown()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pep", description="pep# language CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run a .pep script")
    run_p.add_argument("script", help="Path to script.pep")
    run_p.add_argument("--detach", action="store_true", help="Do not block when server is started")
    run_p.set_defaults(func=cmd_run)

    watch_p = sub.add_parser("watch", help="Run script and print pipeline metrics")
    watch_p.add_argument("script", help="Path to script.pep")
    watch_p.add_argument("--pipeline", required=True, help="Pipeline variable name")
    watch_p.set_defaults(func=cmd_watch)

    plan_p = sub.add_parser("plan", help="Generate execution plan for a script")
    plan_p.add_argument("script", help="Path to script.pep")
    plan_p.add_argument("--mode", choices=["local", "cluster"], default="local")
    plan_p.add_argument("--out", help="Write plan JSON to file")
    plan_p.set_defaults(func=cmd_plan)

    compile_p = sub.add_parser("compile", help="Compile script to .pepc artifact")
    compile_p.add_argument("script", help="Path to script.pep")
    compile_p.add_argument("--out", help="Output artifact path")
    compile_p.set_defaults(func=cmd_compile)

    repl_p = sub.add_parser("repl", help="Open interactive pep# shell")
    repl_p.set_defaults(func=cmd_repl)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
