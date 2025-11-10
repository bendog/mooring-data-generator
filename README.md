# Mooring Data Generator

A simple script to generate fake mooring data for use in a hackathon.
This script will send data payloads to and endpoint to simulate the data which might exist.

These will be http POST queries to the url provided as an argument at run time.

The script will run forever until the user sends a Ctrl+C command to end the script.

## Usage

### With UV (recommended)

If you don't have UV on your system, read [the install instructions for UV](https://docs.astral.sh/uv/getting-started/installation/)

```shell
uvx mooring-data-generator http://127.0.0.1:8000/my/endpoint/
```

[//]: # (TODO: this needs to be confirmed after we release the package to PyPI)

> [!IMPORTANT]
> replace `http://127.0.0.1:8000/my/endpoint/` with the appropriate url for your system

### Vanilla python (If you don't want UV)

#### Install the package

```shell
pip install -U mooring-data-generator
```

### Running the package

```shell
mooring-data-generator http://127.0.0.1:8000/my/endpoint/
```

> [!IMPORTANT]
> replace `http://127.0.0.1:8000/my/endpoint/` with the appropriate url for your system

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
