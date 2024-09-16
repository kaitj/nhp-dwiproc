# StyxDocker

`StyxDocker` is the `DockerRunner` provided by `Styx`. This runner will run
external dependencies as needed in Docker containers. If containers are not
already downloaded, the runner will download the container.

> [!NOTE]
> Docker is typically not available on high performance clusters. In these
> instances, the `SingularityRunner` may be better suited.
