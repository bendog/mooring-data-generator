import argparse
import logging

from .http_worker import run

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="Mooring data generator")
parser.add_argument("url")


def main() -> None:
    """Run the cli tooling for mooring data generator"""
    args = parser.parse_args()
    url: str = args.url

    # build a random structure for this port
    logger.info(f"Starting mooring data generator and will HTTP POST to {url}")
    print(f"Starting mooring data generator and will HTTP POST to {url}")
    print("Press CTRL+C to stop mooring data generator.")
    run(url)


if __name__ == "__main__":
    main()
