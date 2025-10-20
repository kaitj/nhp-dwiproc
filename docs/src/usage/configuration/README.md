# Configuration

To avoid calling a long command at the terminal (potentially repeatedly), `nhp-dwiproc`
provides the ability to pass a YAML-formatted configuration file (see the `Config Key`
column in the arguments tables). If an optional argument is not provided, the default
value is assumed.

> [!TIP]
> It is recommended to put static / minimally changing parameters in the config file.

> [!IMPORTANT]
> Configuration parameters are overwritten, unless otherwise noted, by parameters passed in at the command line.

Below is one example of the configuration file:

```yaml
# Global arguments
opt:
  index_path: /path/to/.index.b2t
  runner:
    name: singularity
    images:
      mcin/docker-fsl:latest: path/to/fsl/singularity/container
      mrtrix3/mrtrix3:3.0.4: path/to/mrtrix/singularity/container
  graph: true
  b0_thresh: 10

# Preprocess arguments
preprocess:
  query:
    t1w: "datatype == 'anat' & run == 1 & suffix == 'T1w' & ext == '.nii.gz'"
    mask: "datatype == 'anat' & run == 1 & desc == 'T1w' & suffix == 'mask' & ext == '.nii.gz'"
  undistort:
    opts:
      topup:
        config: b02b0_macaque
      eddy:
        repol: true
        shelled: true

# Reconstruction arguments
reconstruction:
  tractography:
    single_shell: true
    streamlines: 100_000
    method: wm
```

To use this config, one can call the application as such:

```bash
nhp_dwiproc input_dir output_dir analysis_level \
  --config /path/to/config.yaml
```

Let's also take a look at what this configuration would look like if calling the
preprocess analysis level from the CLI directly:

```bash
nhp_dwiproc bids_dir output_dir preprocess \
  --index-path /path/to/.index.b2t \
  --runner singularity \
  --runner-images "{'mcin/docker-fsl:latest': 'path/to/fsl/singularity/container', 'mrtrix3/mrtrix3:3.0.4': 'path/to/mrtrix/singularity/container'}" \
  --graph \
  --b0_thresh 10 \
  --participant-query "datatype == 'anat' & run == 1 & suffix == 'T1w' & ext == '.nii.gz'" \
  --mask-query "datatype == 'anat' & run == 1 & desc == 'T1w' & suffix == 'mask' & ext == '.nii.gz'" \
  --topup-config b02b0_macaque \
  --eddy-repol \
  --eddy-shelled
```

Please refer to the [template](./template.md) for a configuration file with all available options.
