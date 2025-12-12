# Template

> [!NOTE]
>
> - This template configuration contains all available options shown with default
>   values. Not all configuration parameters need to be provided (see example on
>   [configuration](./) page)

```yaml
# Optional parameters
opts:
  threads: 1
  index_path:
  runner:
    name: local
    images:
  graph: false
  seed_number: 99
  work_dir: styx_tmp
  work_keep: false
  b0_thresh: 10

# Index stage-level parameters
index:
  overwrite: false

# Preprocess stage-level parameters
preprocess:
  query:
    participant:
    dwi:
    t1w:
    mask:
    fmap:
  metadata:
    pe_dirs:
    echo_spacing:
  denoise:
    skip: false
    map_: false
    estimator: Exp2
  unring:
    skip: false
    axes: [0, 1]
  undistort:
    method: topup
    opts:
      topup:
        skip: false
        config: b02b0_macaque
      eddy:
        skip: false
        slm:
        cnr: false
        repol: false
        residuals: false
        shelled: false
      eddymotion:
        skip: false
        iters: 2
      fugue:
        skip: false
        smooth:
  biascorrect:
    skip: false
    spacing: 100.0
    iters: 1000
    shrink: 4
  registration:
    skip: false
    spacing: NMI
    iters: 50x50
    init: identity

# Reconstruction stage-level parameters
reconstruction:
  query:
    participant:
    dwi:
    t1w:
    mask:
  tractography:
    single_shell: false
    shells:
    lmax:
    steps:
    cutoff:
    streamlines: 10_000
    method: act
    opts:
      backtrack: false
      nocrop: false

# Connectivity stage-level parameters
connectivity:
  query:
    participant:
  method: connectome
  opts:
    # Connectome options
    atlas: Markov91
    radius: 2.0
    # Tract mapping options
    voxel_size:
    tract_query:
    surf_query:
```
