# Mooring Data Generator

A simple script to generate fake mooring data for use in a hackathon.
This script will send data payloads to and endpoint to simulate the data which might exist.

These will be http POST queries to the url provided as an argument at run time.

The script will run forever until the user sends a Ctrl+C command to end the script.

## Install

### With UV (recommended)

If you don't have UV on your system, read [the install instructions for UV](https://docs.astral.sh/uv/getting-started/installation/)

```shell
uv tool install -U mooring-data-generator
```

### Vanilla python (If you don't want UV)

```shell
pip install -U mooring-data-generator
```

## Usage

### Running the package

#### Sending data via HTTP POST

```shell
mooring-data-generator http://127.0.0.1:8000/my/endpoint/
```

> [!IMPORTANT]
> replace `http://127.0.0.1:8000/my/endpoint/` with the appropriate url for your system

#### Saving data to a file

You can also save the generated mooring data to a JSON file instead of sending it via HTTP:

```shell
mooring-data-generator --file output.json
```

This will continuously generate mooring data and save it to the specified file.

> [!NOTE]
> You can only use either the URL (HTTP POST) or `--file` option, not both at the same time

#### Getting the OpenAPI specification

You can output an OpenAPI 3.0 specification for the mooring data format:

```shell
mooring-data-generator --openapi
```

This will print a complete OpenAPI specification in JSON format
that describes the structure of the mooring data being generated.
This is useful for:

- Understanding the data format
- Generating client libraries
- API documentation
- Integration planning

The specification can be saved to a file for use with OpenAPI tools:

```shell
mooring-data-generator --openapi > openapi.json
```

## Testing data is being sent

There's a helper application included in this package
to allow you to check that the data is being sent.

`mooring-data-receiver` will display to the console all http traffic it receives.

```shell
mooring-data-receiver
```

By default it will run listening to any traffic `0.0.0.0` on port `8000`

You can adjust this if needed by using a commend like

```shell
mooring-data-receiver --host 127.0.0.1 --port 5000
```

### Formatting output

You can use the `--format` flag to control how the request body is displayed:

```shell
mooring-data-receiver --format
```

When `--format` is used, the request body content
will be formatted using `json.dumps(indent=2)` for better readability.
Without this flag, the content is displayed as received.

## Troubleshooting

### Command not found

If you are having trouble with the command not being found,
you can attempt to run it as a module calling python

```shell
python -m mooring-data-generator http://127.0.0.1:8000/my/endpoint/
```

### Pip not found

If `pip` can't be found on your system.

First, make sure you have Python installed.

```shell
python --version
```

you can call `pip` from python directly as a module.

```shell
python -m pip install -U mooring-data-generator
```

## Release a new version

### Be sure the tests pass

```shell
uv sync --all-groups
uv run ruff format
uv run ruff check
uv run tox
```

### bump version and tag new release

```shell
uv version --bump minor
git commit -am "Release version v$(uv version --short)"
git tag -a "v$(uv version --short)" -m "v$(uv version --short)"
```

### push to github

```shell
git push
git push --tags
```
