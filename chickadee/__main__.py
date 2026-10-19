import argparse
import asyncio
from pathlib import Path
import sys

from .demo import DemoSite
from .scanner import ScanConfig, output_directory, scan


def main():
    parser = argparse.ArgumentParser(description="Chickadee Bot - 공공 웹사이트 불법광고 탐지 데모")
    parser.add_argument("--scan", metavar="URL", help="화면 없이 지정 URL 점검")
    parser.add_argument("--demo", action="store_true", help="로컬 데모 사이트 준비")
    parser.add_argument("--cli", action="store_true", help="--demo와 함께 사용해 로컬 데모를 화면 없이 점검")
    parser.add_argument("--output-dir", type=Path, default=output_directory())
    parser.add_argument("--max-pages", type=int, default=50)
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--page-timeout", type=float, default=15)
    parser.add_argument("--settle-ms", type=int, default=500)
    args = parser.parse_args()
    if not args.scan and not args.cli:
        from .gui import launch
        launch(args.output_dir, args.demo)
        return 0
    if args.cli and not args.scan and not args.demo:
        parser.error("--cli에는 --demo 또는 --scan URL이 필요합니다.")
    demo = DemoSite().start() if args.demo else None
    try:
        url = args.scan or demo.url
        config = ScanConfig(url, args.max_pages, args.timeout, args.page_timeout, args.settle_ms)
        outcome = asyncio.run(scan(config))
        path = outcome.save(args.output_dir)
        if sys.stdout:
            print(f"{outcome.report['status']}: {len(outcome.result['findings'])} findings -> {path}")
        return {"completed": 0, "partial": 2, "cancelled": 2, "failed": 1}[outcome.report["status"]]
    except (ValueError, OSError) as exc:
        if sys.stderr:
            print(str(exc), file=sys.stderr)
        return 1
    finally:
        if demo:
            demo.close()


if __name__ == "__main__":
    raise SystemExit(main())
