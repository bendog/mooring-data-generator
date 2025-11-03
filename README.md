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

> [!IMPORTANT]
> replace `http://127.0.0.1:8000/my/endpoint/` with the appropriate url for your system

### Vanilla python (If you don't want UV)

#### Install the package

```shell
pip install mooring-data-generator
```

#### Running the package

```shell
python -m mooring-data-generator http://127.0.0.1:8000/my/endpoint/
```

> [!IMPORTANT]
> replace `http://127.0.0.1:8000/my/endpoint/` with the appropriate url for your system
