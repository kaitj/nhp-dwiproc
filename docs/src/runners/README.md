# Runners

`nhp-dwiproc` makes use of `Styx` to wrap common neuroimaging tools for workflow
plumbing. We also make use of `StyxRunner`s to faciliate running of various workflows.
Available runners include:

- `LocalRunner`
- `DockerRunner`
- `SingularityRunner`

Please refer to the
[styxbook](https://childmindresearch.github.io/styxbook/) for detailed information
regarding `Styx`.

> [!NOTE]
> For the purposes of this notebook, `StyxRunner`s will be indicated by the `Styx`
> prefix (e.g. `LocalRunner` -> `StyxLocal`)

## LocalRunner

This runner assumes that all necessary dependencies are installed and available on the
system.

> [!WARNING]
> Errors may be encountered when using external dependencies that differ in version
> from `Styx` compiled versions.

## DockerRunner

This runner will run external dependencies as needed in Docker containers. If
containers are not already downloaded, the runner will download the container.

> [!NOTE]
> Docker is typically not available on high performance clusters. In these
> instances, the `SingularityRunner` may be better suited.

This is also the runner used if `podman` is selected as the runner.

## SingularityRunner

> [!IMPORTANT]
> Containers will first need to be downloaded prior to running with this runner.

This runner will run external dependencies as needed in Singularity containers. A
mapping of the locally downloaded containers will need to be passed to the runner
via the `--containers` argument. The mapping is a YAML-formatted file, where the key is
the Docker tag and the value is the location of the container. For example:

```yaml
mrtrix3/mrtrix3:3.0.4: /path/to/mrtrix/singularity/container
```

This is also the runner used if `apptainer` is selected as the runner.
