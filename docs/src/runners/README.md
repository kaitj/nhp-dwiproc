# Runners

`nhp-dwiproc` makes use of `NiWrap` to facilitate the use of common neuroimaging tools
for workflow plumbing. We also make use of `Styx` and it's runners to help manage
workflow execution. Available runners include:

- `LocalRunner`
- `DockerRunner`
- `SingularityRunner`

Please refer to the
[styxbook](https://childmindresearch.github.io/styxbook/) for detailed information
regarding `Styx`.

## LocalRunner

The `LocalRunner` assumes that all necessary dependencies are installed and available on
the system.

> [!WARNING]
> Errors may be encountered when using external dependencies installed with a version
> that differs from `Styx` compiled versions.

## DockerRunner

The `DockerRunner` will execute the workflow, calling upon external dependencies as
needed from Docker containers. If containers are not already downloaded, the runner will
download the container.

This is also the runner used if `podman` is selected as the runner.

## SingularityRunner

The `SingularityRunner` will execute the workflow, calling upon external dependencies as
needed from Singularity containers. If containers are not already downloaded, the runner
will download the container.

This is also the runner used if `apptainer` is selected as the runner.
