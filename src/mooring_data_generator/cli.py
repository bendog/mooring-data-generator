import argparse
import logging
from pathlib import Path

from . import file_worker, http_worker
from .openapi import generate_openapi_spec

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="Mooring data generator")
parser.add_argument(
    "url", nargs="?", help="HTTP endpoint URL (required if --file is not provided)"
)
parser.add_argument("--file", type=str, help="Path to output JSON file (e.g., path/filename.json)")
parser.add_argument(
    "--openapi",
    action="store_true",
    help="Output OpenAPI specification for the data output instead of running the generator",
)


def main() -> None:
    """Run the cli tooling for mooring data generator"""
    args = parser.parse_args()

    # Handle --openapi flag
    if args.openapi:
        spec = generate_openapi_spec()
        print(spec)
        return

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
