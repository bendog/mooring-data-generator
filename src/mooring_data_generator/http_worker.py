import json
import logging
import sys
import time
import urllib.error
import urllib.request

from .builder import build_random_port

logger = logging.getLogger(__name__)


def run(url: str) -> None:
    """Continuously POST generated port data to the given URL every 2 seconds.

    - Builds a random port via builder.build_random_port(), store in variable `port`.
    - Forever loop until interrupted (Ctrl+C):
        - Send JSON payload from `port.data.model_dump(by_alias=True)` to the URL.
          If the HTTP request fails, print a message to stdout and continue.
        - Call `port.update()` to mutate the generated data for next iteration.
        - Sleep for 2 seconds.
    """
    port = build_random_port()
    loops = 0
    payloads = 1
    try:
        while True:
            loops += 1
            try:
                print(f"    loop: {loops:<8} sending payload: {payloads}", end="\r")
                payload = port.data.model_dump(by_alias=True)
                data_bytes = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=data_bytes,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 (stdlib only)
                    # We don't need to print on success; quietly proceed.
                    _ = resp.read()
                payloads += 1
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
                # Notify stdout on failure but continue processing
                logger.error(f"HTTP send failed: {e}")

            except Exception as e:
                logger.error(f"Unknown Error: {e}")
                logger.exception(e)
            finally:
                # Update model and wait regardless of send success
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
    # Allow running this module directly: python -m mooring_data_generator.http_worker <URL>
    if len(sys.argv) != 2:
        print("Usage: http_worker.py <URL>")
        sys.exit(1)
    run(sys.argv[1])
