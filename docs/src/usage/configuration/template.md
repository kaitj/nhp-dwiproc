# Template

> [!NOTE]
>
> - This template configuration contains all available options. For use, not all configurations need to be provided
>   (see example on [configuration](./) page)
> - It is recommended to use separate configuration files for different analysis levels to avoid unexpected query
> results with relevant configuration options

```yaml
# nhp-dwiproc configuration

# General application options
opt:
  working_dir: ./styx_tmp
  index_path: ./index.b2t
  runner: None
  container_config: None
  seed_num: 99
  threads: 1
  keep_tmp: false
  graph: false

# Analysis level options
participant:
  query:
  dwi_query:
  t1w_query:
  mask_query:
  b0_thresh: 10

  # Index level
  index:
    overwrite: true

  # Preprocess level
  preprocess:
    metadata:
      pe_dirs:
      echo_spacing: 0.001
    denoise:
      skip: false
      extent:
      map:
      estimator: Exp2
    unring:
      skip: false
      axes: 0 1
      nshifts: 20
      minW: 1
      maxW: 3
    undistort:
      method: fsl
    topup:
      skip: false
      config: b02b0_macaque
    eddy:
      slm:
      cnr_maps: false
      repol: true
      residuals: false
      shelled: true
    eddymotion:
      iters: 2
    biascorrect:
      spacing: 100.00
      iters: 1_000
      shrink: 4
    register:
      skip: false
      metric: NMI
      iters: 50x50

  # Tractography level
  tractography:
    single_shell: false
    shells:
    lmax:
    steps:
    cutoff: 0.10
    streamlines: 10_000

  # Connectivity level
  connectivity:
    atlas:
    radius: 2.00
```
