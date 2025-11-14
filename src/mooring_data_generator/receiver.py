import argparse
import json
import statistics
import sys
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Literal

DEFAULT_PORT = 8000
MAX_SHOW = 1024 * 1


class PrintingRequestHandler(BaseHTTPRequestHandler):
    """A very simple request handler that prints the full request and responds 200.

    - Prints: client address, method, path, HTTP version, headers, and body (if any)
    - Responds: 200 OK with a small text/plain body
    - Avoids using any external packages
    """

    # Max bytes of body to show; set to None for full body
    max_show: int = MAX_SHOW

    # Format mode: None for default, "json" for JSON output
    format_mode: bool = False

    # Summary mode: restrict output to a specific summary
    filter_mode: Literal["lines", "tensions"] | None = None

    # Disable default logging to stderr; we print our own structured output
    def log_message(self, format: str, *args) -> None:  # noqa: A003 - match BaseHTTPRequestHandler
        return

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length > 0:
            return self.rfile.read(length)
        return b""

    def _print_body(self, body: bytes, content_type: str) -> None:
        """Safely limit body printout size (unless max_show is None"""
        if self.format_mode:
            if content_type == "application/json":
                body = json.dumps(json.loads(body.decode("utf-8")), indent=2).encode("utf-8")
        if self.max_show is None:
            shown = body
        else:
            shown = body[: self.max_show]
        try:
            print(shown.decode("utf-8", errors="replace"))
        except Exception as e:
            print(f"-- {e}")
            print(repr(shown))
        if self.max_show is not None and len(body) > self.max_show:
            print(f"-- {len(body) - self.max_show} more bytes not shown --")

    def _print_request(self, body: bytes) -> None:
        """print the request to stdoutmo"""
        # In summary modes, suppress standard request printout and only show summary
        if self.filter_mode == "lines":
            self._print_lines_summary(body)
            sys.stdout.flush()
            return
        if self.filter_mode == "tensions":
            self._print_tensions_summary(body)
            sys.stdout.flush()
            return
        # First line
        http_version = {
            9: "HTTP/0.9",
            10: "HTTP/1.0",
            11: "HTTP/1.1",
        }.get(self.protocol_version_number(), self.protocol_version)

        client_host, client_port = self.client_address
        print("=" * 80)
        print(f"Client: {client_host}:{client_port}")
        print(f"Request: {self.command} {self.path} {http_version}")
        print("-- Headers --")
        for k, v in self.headers.items():
            print(f"{k}: {v}")
        if body:
            print("-- Body (bytes) --")
            content_type = self.headers.get("Content-Type", "")
            self._print_body(body, content_type)
        else:
            print("-- No Body --")
        print("=" * 80)
        sys.stdout.flush()

    def _print_lines_summary(self, body: bytes) -> None:
        """Print a compact summary of berths and counts of line names per berth.

        Expects JSON body compatible with PortData model using alias field names
        (camelCase), e.g. berths[].bollards[].hooks[].attachedLine.
        """
        if not body:
            print("-- No Body --")
            return
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception as e:
            print(f"-- Failed to parse JSON body: {e}")
            return

        berths = payload.get("berths")
        if not isinstance(berths, list):
            print("-- No berths found in payload --")
            return

        # NOTE: I vibecoded this and it's embarrassing, do not judge me

        # Determine line kinds dynamically from the payload (order by first seen)
        count_of_lines: dict[str, int] = defaultdict(int)
        for berth in berths:
            name = berth.get("name", "<unknown>")
            for bollard in berth.get("bollards", []) or []:
                for hook in bollard.get("hooks", []) or []:
                    line = hook.get("attachedLine")
                    if isinstance(line, str):
                        count_of_lines[line] += 1
            # Build a compact one-line summary
            parts = [f"{k}:{v}" for k, v in count_of_lines.items()]
            print(f"{name} -> " + " ".join(parts))

    def _print_tensions_summary(self, body: bytes) -> None:  # noqa: C901
        """Print per-berth tension statistics (min, max, median, mean, std).

        Expects JSON body compatible with PortData model using alias field names
        (camelCase), e.g. berths[].bollards[].hooks[].tension.
        """
        if not body:
            print("-- No Body --")
            return
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception as e:
            print(f"-- Failed to parse JSON body: {e}")
            return

        berths = payload.get("berths")
        if not isinstance(berths, list):
            print("-- No berths found in payload --")
            return

        for berth in berths:
            name = berth.get("name", "<unknown>")
            tensions: list[float] = []
            for bollard in berth.get("bollards", []) or []:
                for hook in bollard.get("hooks", []) or []:
                    t = hook.get("tension")
                    if isinstance(t, (int, float)):
                        tensions.append(float(t))

            if not tensions:
                print(f"{name} -> min=N/A max=N/A median=N/A mean=N/A std=N/A")
                continue

            t_min = min(tensions)
            t_max = max(tensions)
            t_median = statistics.median(tensions)
            t_mean = (
                statistics.fmean(tensions)
                if hasattr(statistics, "fmean")
                else sum(tensions) / len(tensions)
            )
            # Use population standard deviation to avoid ValueError on single sample
            t_std = statistics.pstdev(tensions)

            # Format with up to 2 decimal places, but avoid trailing .0 noise for ints
            def fmt(x: float) -> str:
                if abs(x - round(x)) < 1e-9:
                    return str(int(round(x)))
                return f"{x:.2f}"

            print(
                f"{name} -> min={fmt(t_min)} max={fmt(t_max)} median={fmt(t_median)} mean={fmt(t_mean)} std={fmt(t_std)}"
            )

    def _respond_ok(self) -> None:
        message = b"OK\n"
        self.send_response(200, "OK")
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(message)))
        self.end_headers()
        self.wfile.write(message)

    # Map common methods to the same handler
    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        body = self._read_body()
        self._print_request(body)
        self._respond_ok()

    def do_POST(self) -> None:  # noqa: N802
        body = self._read_body()
        self._print_request(body)
        self._respond_ok()

    def do_PUT(self) -> None:  # noqa: N802
        body = self._read_body()
        self._print_request(body)
        self._respond_ok()

    def do_PATCH(self) -> None:  # noqa: N802
        body = self._read_body()
        self._print_request(body)
        self._respond_ok()

    def do_DELETE(self) -> None:  # noqa: N802
        body = self._read_body()
        self._print_request(body)
        self._respond_ok()

    def do_OPTIONS(self) -> None:  # noqa: N802
        # Minimal CORS-friendly response
        self.send_response(200, "OK")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*, Content-Type, Authorization")
        self.end_headers()

    # Helper to expose numeric protocol version (for display)
    def protocol_version_number(self) -> int:
        try:
            return int(self.protocol_version.split("/")[-1].replace(".", ""))
        except Exception:
            return 11  # assume HTTP/1.1 if unknown


def serve(port: int = DEFAULT_PORT, host: str = "0.0.0.0") -> tuple[str, int]:
    """Start the HTTP server and block forever.

    Returns the actual bound address (host, port). Useful when passing port=0.
    """
    server = ThreadingHTTPServer((host, port), PrintingRequestHandler)
    bound_host, bound_port = server.server_address
    print(f"Listening on http://{bound_host}:{bound_port} (press Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        server.server_close()
    return bound_host, bound_port


def cli(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Simple HTTP request printer")
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to listen on (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--host",
        "-H",
        default="0.0.0.0",
        help="Host/interface to bind (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Print full request bodies without truncation",
    )
    parser.add_argument(
        "--format",
        action="store_true",
        help="Output format for request content (json uses json.dumps, otherwise content as received)",
    )
    parser.add_argument(
        "--lines",
        action="store_true",
        help=(
            "Only output a list of berth names with counts of each line type per berth. "
            "Suppresses full request printing."
        ),
    )
    parser.add_argument(
        "--tensions",
        action="store_true",
        help=(
            "Only output a list of berths with max/min/median/mean/std of hook tensions per berth. "
            "Suppresses full request printing."
        ),
    )

    args = parser.parse_args(argv)

    # Configure handler truncation behavior
    if args.full:
        PrintingRequestHandler.max_show = None  # show full body
    else:
        PrintingRequestHandler.max_show = MAX_SHOW

    # Configure output format
    if args.format:
        PrintingRequestHandler.format_mode = args.format

    # Configure summary modes (tensions takes precedence if both are set)
    if getattr(args, "tensions", False):
        PrintingRequestHandler.filter_mode = "tensions"
    elif getattr(args, "lines", False):
        PrintingRequestHandler.filter_mode = "lines"

    serve(port=args.port, host=args.host)


if __name__ == "__main__":
    cli()
