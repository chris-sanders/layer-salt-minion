import os
import stat
import subprocess
import yaml

import pytest

# Treat all tests as coroutines
pytestmark = pytest.mark.asyncio

juju_repository = os.getenv("JUJU_REPOSITORY", ".").rstrip("/")
series = [
    "xenial",
    "bionic",
    # pytest.param("disco", marks=pytest.mark.xfail(reason="canary")),
]
sources = [
    ("local", "{}/builds/salt-minion".format(juju_repository)),
    ("jujucharms", "cs:~chris.sanders/salt-minion"),
]


# Custom fixtures
@pytest.fixture(params=series)
def series(request):
    return request.param


@pytest.fixture(params=sources, ids=[s[0] for s in sources])
def source(request):
    return request.param


@pytest.fixture
async def salt_app(model, source):
    app_name = "salt-minion-{}".format(source[0])
    return await model._wait_for_new("application", app_name)


@pytest.fixture
async def ubuntu_app(model, series, source):
    app_name = "ubuntu-{}-{}".format(series, source[0])
    return await model._wait_for_new("application", app_name)


@pytest.mark.deploy
@pytest.mark.timeout(30)
async def test_saltminion_deploy(model, source, request):
    # Starts a deploy for each series
    # Using subprocess b/c libjuju fails with JAAS
    # https://github.com/juju/python-libjuju/issues/221
    application_name = "salt-minion-{}".format(source[0])
    cmd = ["juju", "deploy", source[1], "-m", model.info.name, application_name]
    subprocess.check_call(cmd)


@pytest.mark.deploy
@pytest.mark.timeout(30)
async def test_master_deploy(model):
    # Starts a deploy for each series
    # Using subprocess b/c libjuju fails with JAAS
    # https://github.com/juju/python-libjuju/issues/221
    cmd = [
        "juju",
        "deploy",
        "cs:~chris.sanders/salt-master",
        "-m",
        model.info.name,
        "--series",
        "xenial",
    ]
    subprocess.check_call(cmd)


@pytest.mark.deploy
@pytest.mark.timeout(30)
async def test_ubuntu_deploy(model, series, source, request):
    # Starts a deploy for each series
    # Using subprocess b/c libjuju fails with JAAS
    # https://github.com/juju/python-libjuju/issues/221
    application_name = "ubuntu-{}-{}".format(series, source[0])
    cmd = [
        "juju",
        "deploy",
        "cs:ubuntu",
        "-m",
        model.info.name,
        "--series",
        series,
        application_name,
    ]
    if request.node.get_closest_marker("xfail"):
        # If series is 'xfail' force install to allow testing against versions not in
        # metadata.yaml
        cmd.append("--force")
    subprocess.check_call(cmd)


@pytest.mark.timeout(30)
@pytest.mark.deploy
async def test_subordinate_relate(model, salt_app, ubuntu_app):
    if salt_app.name.split("-")[-1] != ubuntu_app.name.split("-")[-1]:
        pytest.skip()  # Only deploy minions on ubuntus of the same source
    await model.add_relation("{}:juju-info".format(salt_app.name), ubuntu_app.name)


@pytest.mark.deploy
@pytest.mark.timeout(300)
async def test_charm_upgrade(model, salt_app):
    if salt_app.name.endswith("local"):
        pytest.skip()  # No need to upgrade local charm already at test version
    await model.block_until(lambda: salt_app.status == "active")
    unit = salt_app.units[0]
    await model.block_until(lambda: unit.agent_status == "idle")
    subprocess.check_call(
        [
            "juju",
            "upgrade-charm",
            "--switch={}".format(sources[0][1]),
            "-m",
            model.info.name,
            salt_app.name,
        ]
    )
    await model.block_until(lambda: unit.agent_status == "executing")


@pytest.mark.deploy
@pytest.mark.timeout(300)
async def test_saltminion_status(model, salt_app):
    # Verifies status for all deployed series of the charm
    await model.block_until(lambda: salt_app.status == "active")
    unit = salt_app.units[0]
    await model.block_until(lambda: unit.agent_status == "idle")


# Tests
async def test_run_command(salt_app, jujutools):
    unit = salt_app.units[0]
    cmd = "hostname --all-ip-addresses"
    results = await jujutools.run_command(cmd, unit)
    assert results["Code"] == "0"
    assert unit.public_address in results["Stdout"]


async def test_file_stat(salt_app, jujutools):
    unit = salt_app.units[0]
    path = "/var/lib/juju/agents/unit-{}/charm/metadata.yaml".format(
        unit.entity_id.replace("/", "-")
    )
    fstat = await jujutools.file_stat(path, unit)
    assert stat.filemode(fstat.st_mode) == "-rw-r--r--"
    assert fstat.st_uid == 0
    assert fstat.st_gid == 0


async def test_service_status(salt_app, jujutools):
    unit = salt_app.units[0]
    status = await jujutools.service_status("salt-minion", unit)
    print(status)
    assert status["Code"] == "0"
    assert "Active: active (running)" in status["Stdout"]


@pytest.mark.timeout(120)
@pytest.mark.deploy
async def test_master_relate(model, salt_app):
    master = model.applications["salt-master"]
    master_unit = master.units[0]
    await model.block_until(lambda: master_unit.agent_status == "idle")
    await model.add_relation("{}:saltmaster".format(salt_app.name), "salt-master")
    for unit in salt_app.units:
        await model.block_until(lambda: unit.agent_status == "executing")
        await model.block_until(lambda: unit.agent_status == "idle")


@pytest.mark.timeout(30)
async def test_minion_registered(jujutools, model, ubuntu_app):
    master = model.applications["salt-master"]
    master_unit = master.units[0]
    output = await jujutools.run_command("salt-key -L --output=yaml", master_unit)
    keys = yaml.safe_load(output["Stdout"])
    print(keys)
    assert output["Code"] == "0"
    # minion_name = "ubuntu-{}-{}-0".format(series, source[0])
    ubuntu_unit = ubuntu_app.units[0]
    minion_name = ubuntu_unit.name.replace("/", "-")
    assert minion_name in keys["minions"]
    # assert not keys["minions_denied"]
    # assert not keys["minions_rejected"]


@pytest.mark.timeout(30)
async def test_minions_denied(jujutools, model):
    master = model.applications["salt-master"]
    master_unit = master.units[0]
    output = await jujutools.run_command("salt-key -L --output=yaml", master_unit)
    keys = yaml.safe_load(output["Stdout"])
    print(keys)
    assert output["Code"] == "0"
    assert not keys["minions_denied"]
    assert not keys["minions_rejected"]
