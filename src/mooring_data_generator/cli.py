import argparse

parser = argparse.ArgumentParser(description="Mooring data generator")
parser.add_argument("url")


def main() -> None:
    """Run the cli tooling for mooring data generator"""
    args = parser.parse_args()
    url: str = args.url

    # build a random structure for this port
    print(f"Starting mooring data generator and will HTTP POST to {url}")


if __name__ == "__main__":
    main()
