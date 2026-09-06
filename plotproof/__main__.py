"""Launch the native desktop or review a manuscript from the terminal."""

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .engine import analyze
from .export import html_report
from .providers import ProviderError, Settings


def main():
    parser = argparse.ArgumentParser(prog="plotproof", description="Evidence-backed story continuity review.")
    parser.add_argument("--version", action="version", version=__version__)
    subs = parser.add_subparsers(dest="command")
    serve = subs.add_parser("serve", help="Start the optional local JSON API (headless)")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--no-browser", action="store_true", help=argparse.SUPPRESS)
    serve.add_argument("--data-dir", type=Path, default=Path(".plotproof"))
    check = subs.add_parser("check", help="Analyze TXT, Markdown or Word manuscripts")
    check.add_argument("file", type=Path)
    check.add_argument("--provider", choices=["rules", "ollama", "compatible"], default="rules")
    check.add_argument("--base-url", default="")
    check.add_argument("--model", default="")
    check.add_argument("--language", choices=["zh", "en"], default="en")
    check.add_argument("--output", type=Path)
    check.add_argument("--format", choices=["json", "html"], default="json")
    check.add_argument("--fail-on-findings", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "check":
            settings = Settings(
                args.provider,
                args.base_url,
                args.model,
                os.environ.get("PLOTPROOF_API_KEY", ""),
                args.language,
            )
            from .importers import read_manuscript

            text, _ = read_manuscript(args.file)
            report = analyze(text, settings)
            doc = {"title": args.file.stem, "revision": 1, "report": report}
            output = (
                html_report(doc)
                if args.format == "html"
                else json.dumps(report, ensure_ascii=False, indent=2)
            )
            if args.output:
                args.output.write_text(output, encoding="utf-8")
            else:
                print(output)
            return 1 if args.fail_on_findings and report["findings"] else 0
        if not args.command:
            from .desktop.app import main as desktop_main

            return desktop_main([])
        from .server import make_server

        root = Path(__file__).resolve().parent
        static = root / "static"
        port, data_dir = (args.port, args.data_dir) if args.command else (8765, Path(".plotproof"))
        server = make_server(port, data_dir, static)
        url = f"http://127.0.0.1:{server.server_port}"
        print(f"PlotProof {__version__} · {url}\nLocal projects: {data_dir.resolve()}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
            server.app.close()
        return 0
    except (OSError, UnicodeError, ValueError, ProviderError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
