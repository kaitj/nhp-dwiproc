# Command-line interface (CLI)

The command-line interface for `nhp-dwiproc` follows that of a BIDS application:

```bash
nhp_dwiproc [INPUT_DIR] [OUTPUT_DIR] [COMMAND] <OPTIONS>
```

| Argument     | Description                                                                           |
| :----------- | :------------------------------------------------------------------------------------ |
| `INPUT_DIR`  | the input dataset directory                                                           |
| `OUTPUT_DIR` | the output directory                                                                  |
| `COMMAND`    | the processing stage (one of `index`, `preprocess`, `reconstruction`, `connectivity`) |
| `OPTIONS`    | additional stage-specific application options                                         |

</br>
> [!NOTE]
> The majority of CLI options also have a associated config key. Config keys are
> overwritten by parameters provided
> the CLI unless otherwise noted. Each `.` represents a nested level in the config
> (see configuration for details).

## Global options

These optional arguments can be used for all analysis level stages:

| Argument                 | Config Key           | Description                                                                                                                     |
| :----------------------- | :------------------- | :------------------------------------------------------------------------------------------------------------------------------ |
| `--version`              |                      | prints installed version                                                                                                        |
| `--help`                 |                      | prints stage-specific help message                                                                                              |
| `--config <config_path>` |                      | path to application YAML configuration file                                                                                     |
| `--threads <threads>`    | `opts.threads`       | number of threads to use - default: `1`                                                                                         |
| `--index-path`           | `opts.index_path`    | `bids2table` index path - default: `{bids_dir}/index.b2t`                                                                       |
| `--runner <runner>`      | `opts.runner.name`   | workflow runner to use for non-index stages (one of `local`, `docker`, `podman`, `apptainer`, `singularity`) - default: `local` |
| `--runner-images <map>`  | `opts.runner.images` | String dictionary, mapping container overrides. - default: `None                                                                |
| `--graph`                | `opts.graph`         | print mermaid diagram of workflow - default: `False`                                                                            |
| `--seed-num <num>`       | `opts.seed_num`      | fixed seed to use for reproducible results - default: `99`                                                                      |
| `--work-dir <dir>`       | `opts.work_dir`      | working directory to temporarily write files to - default: `./styx_tmp`                                                         |
| `--work-keep`            | `opts.work_keep`     | keep working directory - default: `False`                                                                                       |
| `--b0-thresh <thresh>`   | `opts.b0_thresh`     | threshold for shell to be considered b=0 - default: `10`                                                                        |

</br>
> [!IMPORTANT]
> Most options are reused across multiple non-index stages - please refer to the
> [Analysis levels](./analysis_levels/) page for specific details regarding each
> processing stage, including optional arguments.

### Query example

Query arguments are string arguments passed to search the `bids2table` index for a
specific participant. One can use the argument as such:

```bash
nhp_dwiproc data_dir output_dir analysis_level \
  --participant-query 'sub = "001" AND ses = "YY"' \
  --dwi-query 'run = 1'
```

> [!NOTE]
> While `pandas`-like string queries are partially supported, SQL queries are preferred.
> For SQL-like queries, only the condition needs to be provided
> (e.g. `sub = '001' AND ses = 'AA'`)

The participant-query will identify all participants with matching BIDS entities
`sub-001_ses-YY`, while the DWI query will identify all diffusion-associated files
matching `run-1`. In the example, the workflow will run on diffusion files containing
`sub-001_ses-YY_run-1_dwi.nii.gz` as a result of the combined query.

> [!TIP]
>
> - While the CLI provides an easy way to update arguments to the workflow on-the-go,
>   it can be tedious repeatedly call a long command. It is recommended to use the
>   `--config` argument to pass a configuration file with all desired optional argument
>   values. For details see the [configuration](../configuration/config.md) page.

Queries can also be passed via the configuration, with each stage having its own its
own set of queries. Refer to each analysis-stage's page for additional details.
