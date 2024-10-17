# Command-line interface (CLI)

The command-line interface for `nhp-dwiproc` follows that of a BIDS application:

```bash
nhp_dwiproc bids_dir output_dir analysis_level [options]
```

| Argument | Description |
| :- | :- |
| `bids_dir` | the input dataset directory |
| `output_dir` | the output directory |
| `analysis_level` | the processing stage (one of `index`, `preprocess`, `tractography`, `connectivity`) |
| `options` | additional application options |

</br>
> [!NOTE]
> The majority of CLI options also have a associated config key. Config keys are overwritten by parameters provided
> the CLI unless otherwise noted. Each `.` represents a nested level in the config (see configuration for details).

## Global options
These optional arguments can be used for all analysis level stages:
| Argument | Config Key | Description |
| :- | :- | :- |
| `--help` | | prints help message |
| `--config <config_path>` | | path to application configuration file |
| `--runner <runner>` | `opt.runner` | workflow runner to use (one of `None`, `Docker`, `Singularity`, `Apptainer`) - default: `None`|
| `--working-dir <directory>` | `opt.working_dir` | working directory to temporarily write files to - default: `./styx_tmp` |
| `--container-config <config> ` | `opt.containers` | path to YAML config file mapping containers to local paths for Singularity/Apptainer |
| `--seed-num <num>` | `opt.seed_num` | fixed seed to use for reproducible results - default: `99` |
| `--threads <threads>` | `opt.threads` | number of threads to use - default: `1` |
| `--keep-tmp` | `opt.keep_tmp` | flag to keep all intermediate files |
| `--graph` | `opt.graph` | flag to print diagram of workflow |
| `--index-path` | `opt.index_path` | `bids2table` index path - default: `{bids_dir}/index.b2t` |
| `--participant-query <query>` | `participant.query` | participant `subject` & `session` string query |
| `--dwi-query <query>` | `participant.query_dwi` | string query for DWI-associated BIDS entities |
| `--t1w-query <query>` | `participant.query_t1w` | string query for T1w-associated BIDS entities |
| `--mask-query <query>` | `participant.query_mask` | string query for custom mask-associated BIDS entities (in T1w space) |
| `--fmap-query <query>` | `participant.query_fmap` | string query for fieldmap-associated BIDS entities |
| `--b0-thresh <thresh>` | `participant.b0_thresh` | threshold for shell to be considered b=0 - default: `10` |

</br>
> [!IMPORTANT]
> Please refer to the [Analysis levels](./analysis_levels/) page for specific details regarding each processing
> stage, including associated optional arguments.

### Query example

Query arguments are string arguments passed to search the `bids2table` index for a specific participant. One can use the argument as such:

```bash
nhp_dwiproc bids_dir output_dir analysis_level \
  --participant-query 'sub=="001" & ses=="YY' \
  --dwi-query 'run==1'
```

The participant-query will identify all participants with matching BIDS entities
 `sub-001_ses-YY`, while the DWI query will identify all diffusion-associated files matching
 `run-1`. In the example, the workflow will run on diffusion files containing
 `sub-001_ses-YY_run-1_dwi.nii.gz` as a result of the combined query.

> [!TIP]
> * While the CLI provides an easy way to update arguments to the workflow on-the-go, it can be tedious repeatedly call
> a long command. It is recommended to use the `--config` argument to pass a configuration file with all desired
> optional argument values. For details see the [configuration](../configuration/config.md) page.
> * Underscores (`_`) and dashes (`-`), except for the leading `--`, can be used interchangeably in all arguments
> (including analysis-level specific ones)
