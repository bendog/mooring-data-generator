import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

from .builder import build_random_port

logger = logging.getLogger(__name__)


def run(path: Path) -> None:
    """Continuously generate port data and save to JSON files every 2 seconds.

    - Builds a random port via builder.build_random_port(), store in variable `port`.
    - Forever loop until interrupted (Ctrl+C):
        - Generate filename using pattern: path.parent / f"{path.stem}_{timestamp}{path.suffix}"
        - Save JSON payload from `port.data.model_dump(by_alias=True)` to the file.
          If the file write fails, print a message to stdout and continue.
        - Call `port.update()` to mutate the generated data for next iteration.
        - Sleep for 2 seconds.

    Args:
        path: Pathlib Path object used to build the output filename pattern
    """
    port = build_random_port()
    loops = 0
    payloads = 1
    try:
        while True:
            loops += 1
            try:
                print(f"    loop: {loops:<8} saving payload: {payloads}", end="\r")
                payload = port.data.model_dump(by_alias=True)

                # Build filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                output_file = path.parent / f"{path.stem}_{timestamp}{path.suffix}"

                # Ensure parent directory exists
                output_file.parent.mkdir(parents=True, exist_ok=True)

                # Write JSON to file
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)

                payloads += 1
            except (OSError, IOError) as e:
                # Notify stdout on failure but continue processing
                logger.error(f"File write failed: {e}")

            except Exception as e:
                logger.error(f"Unknown Error: {e}")
                logger.exception(e)
            finally:
                # Update model and wait regardless of write success
                try:
                    port.update()
                except Exception as e:  # Defensive: updating should not kill the loop
                    logger.error(f"Port update failed: {e}")
                    logger.exception(e)
                    raise e
                time.sleep(2)
    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C
        logger.info("Interrupted by user. Exiting.")


if __name__ == "__main__":
    # Allow running this module directly: python -m mooring_data_generator.file_worker <PATH>
    if len(sys.argv) != 2:
        print("Usage: file_worker.py <PATH>")
        sys.exit(1)
    run(Path(sys.argv[1]))
