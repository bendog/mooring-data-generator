import argparse
import logging
from pathlib import Path

from . import file_worker, http_worker

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="Mooring data generator")
parser.add_argument(
    "url", nargs="?", help="HTTP endpoint URL (required if --file is not provided)"
)
parser.add_argument("--file", type=str, help="Path to output JSON file (e.g., path/filename.json)")


def main() -> None:
    """Run the cli tooling for mooring data generator"""
    args = parser.parse_args()

    # Validate that either url or --file is provided
    if not args.url and not args.file:
        parser.error("Either url or --file must be provided")

    if args.url and args.file:
        parser.error("Cannot use both url and --file at the same time")

    if args.file:
        # Use file_worker
        file_path = Path(args.file)
        logger.info(f"Starting mooring data generator and will save to files: {file_path}")
        print(f"Starting mooring data generator and will save to files: {file_path}")
        print("Press CTRL+C to stop mooring data generator.")
        file_worker.run(file_path)
    else:
        # Use http_worker
        url: str = args.url
        logger.info(f"Starting mooring data generator and will HTTP POST to {url}")
        print(f"Starting mooring data generator and will HTTP POST to {url}")
        print("Press CTRL+C to stop mooring data generator.")
        http_worker.run(url)


if __name__ == "__main__":
    main()
