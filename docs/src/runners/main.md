# Runners

`nhp-dwiproc` makes use of `Styx` to wrap common neuroimaging tools for workflow plumbing. We also make use of
`StyxRunner`s to faciliate running of various workflows. Available runners include:

* `LocalRunner`
* `DockerRunner`
* `SingularityRunner`

Please refer to the
[styxbook](https://childmindresearch.github.io/styxbook/) for detailed information regarding `Styx`.

> [!NOTE]
> For the purposes of this notebook, `StyxRunner`s will be indicated by the `Styx` prefix
> (e.g. `LocalRunner` -> `StyxLocal`)
