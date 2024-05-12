import configparser
import sys
import tomllib
import click
import subprocess
from pathlib import Path


DAEMON_ARGS = ["supervisord", "-c", Path.cwd() / "supervisord.conf"]
CLIENT_ARGS = ["supervisorctl", "-c", Path.cwd() / "supervisord.conf"]


def load_template():
    with (Path.cwd() / "supervisord_template.conf").open("r") as f:
        config = configparser.ConfigParser()
        config.read_file(f)
        return config


def read_manifest(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def manifest_to_supervisor_config(services_section: dict) -> dict:
    sv_config = {}
    for service in services_section.keys():
        sv_name = f"program:{service}"
        sv_config[sv_name] = services_section[service]
    return sv_config


def make_sv_config(manifest: dict):
    sv_config = load_template()
    sv_programs = manifest_to_supervisor_config(manifest["services"])
    for program in sv_programs:
        sv_config[program] = sv_programs[program]
    with (Path.cwd() / "supervisord.conf").open("w") as f:
        sv_config.write(f)


def supervisor_is_running() -> bool:
    try:
        subprocess.run(CLIENT_ARGS + ["status"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        return False
    finally:
        return True


def start_supervisor():
    subprocess.run(DAEMON_ARGS, check=True)


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    "-m",
    "--manifest",
    "manifest_path",
    default=(Path.cwd() / "manifest.toml"),
    show_default=True,
    type=click.Path(exists=True, dir_okay=False),
    help="path to a manifest.toml file",
)
def init(manifest_path):
    """Create the supervisor config file"""
    manifest = read_manifest(manifest_path)
    make_sv_config(manifest)


@cli.command()
@click.argument("services", nargs=-1)
def start(services):
    """Start services"""
    if not supervisor_is_running():
        start_supervisor()
    to_start = ["all"]
    if len(services) != 0:
        to_start = services
    subprocess.run(CLIENT_ARGS + ["start"] + to_start, check=True)


@cli.command()
@click.argument("services", nargs=-1)
def stop(services):
    """Stop services"""
    if not supervisor_is_running():
        start_supervisor()
    to_stop = ["all"]
    if len(services) != 0:
        to_stop = services
    subprocess.run(CLIENT_ARGS + ["stop"] + to_stop, check=True)


@cli.command()
@click.argument("services", nargs=-1)
def restart(services):
    """Restart services"""
    if not supervisor_is_running():
        start_supervisor()
    to_restart = ["all"]
    if len(services) != 0:
        to_restart = services
    subprocess.run(CLIENT_ARGS + ["restart"] + to_restart, check=True)


@cli.command()
def shutdown():
    """Shut down all services and the daemon"""
    subprocess.run(CLIENT_ARGS + ["shutdown"], check=True)


@cli.command()
@click.argument("services", nargs=-1)
def status(services):
    """Display the status of services"""
    if not supervisor_is_running():
        print("Services not started")
        sys.exit(1)
    to_show = []  # empty means "all"
    if len(services) != 0:
        to_show = services
    subprocess.run(CLIENT_ARGS + ["status"] + to_show, check=True)


if __name__ == "__main__":
    cli()
