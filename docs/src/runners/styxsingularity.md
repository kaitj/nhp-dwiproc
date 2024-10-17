# StyxSingularity

`StyxSingularity` is the `SingularityRunner` provided by `Styx`.

> [!NOTE]
> `apptainer` is analogous to `singularity` for the purposes of this runner.

> [!IMPORTANT]
> Containers will first need to be downloaded prior to running with this runner.

This runner will run external dependencies as needed in Singularity containers. A mapping
of the locally downloaded containers will need to be passed to the runner via the `--containers`
argument. The mapping is a YAML file, where the key is the Docker tag and the value is the
location of the container. For example:

```yaml
mrtrix3/mrtrix3:3.0.4: /path/to/mrtrix/singularity/container
```
