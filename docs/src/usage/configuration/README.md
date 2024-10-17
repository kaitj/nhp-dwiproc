# Configuration

To avoid calling a long command at the terminal (potentially repeatedly), `nhp-dwiproc` provides the ability to pass a
configuration YAML file (see the `Config Key` column in the arguments tables). If an optional argument is not provided,
the default value is assumed.

> [!TIP]
> It is recommended to put static / minimally changing parameters in the config file.

> [!IMPORTANT]
> Configuration parameters are overwritten, unless otherwise noted, by parameters passed in at the command line.

Below is one example of the configuration file:

```yaml
# Example nhp-dwiproc config
opt:
  runner: Singularity
  containers: /path/to/containers.yaml
  index_path: /path/to/.index.b2t
  graph: true

# General participant analysis-level arguments
participant:
  b0_thresh: 10
  query_t1w: "datatype == 'anat' & run == 1 & suffix == 'T1w' & ext == '.nii.gz'"
  query_mask: "datatype == 'anat' & run == 1 & desc == 'T1w' & suffix == 'mask' & ext == '.nii.gz'"

  # Preprocess analysis-level arguments
  preprocess:
    topup:
      config: b02b0_macaque
    eddy:
      repol: true
      shelled: true

  # Tractography analysis-level arguments
  tractography:
    single_shell: true
    streamlines: 100_000
```

To use this config, one can call the application as such:

```bash
nhp_dwiproc bids_dir output_dir analysis_level \
  --config /path/to/config.yaml
```

Let's also take a look at what this configuration would look like if calling the preprocess analysis
level from the CLI directly:

```bash
nhp_dwiproc bids_dir output_dir preprocess \
  --runner Singularity \
  --container-config /path/to/containers.yaml \
  --index-path /path/to/.index.b2t \
  --graph \
  --b0_thresh 10 \
  --participant-query "datatype == 'anat' & run == 1 & suffix == 'T1w' & ext == '.nii.gz'" \
  --mask-query "datatype == 'anat' & run == 1 & desc == 'T1w' & suffix == 'mask' & ext == '.nii.gz'" \
  --topup-config b02b0_macaque \
  --eddy-repol \
  --eddy-data-is-shelled
```

Please refer to the [template](./template.md) for a configuration file with all available options.
