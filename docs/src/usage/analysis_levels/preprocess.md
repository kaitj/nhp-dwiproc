# Preprocess level

`preprocess` level processing is a workflow intended to perform preprocessing from raw
single-shell and multi-shell diffusion weighted data. Currently, the following types of
acquisition sampling schemes can be preprocessed:

- Q-space sampling (single and opposite phase-encoding)
- Cartesian sampling

Parameters for individual preprocessing steps can be updates via CLI or configuration
file, or can be skipped entirely. Given the multitude of options, the following
sub-sections will break down the different steps and associated options.

## Level-specific optional arguments

### Query

Query options for preprocessing:

| Argument              | Config Key                     | Description                                                             |
| :-------------------- | :----------------------------- | :---------------------------------------------------------------------- |
| `--participant-query` | `preprocess.query.participant` | string query for 'subject' and 'session' - default: `None`              |
| `--dwi-query`         | `preprocess.query.dwi`         | string query for DWI-associated BIDS entities - default: `None`         |
| `--t1w-query`         | `preprocess.query.t1w`         | string query for T1w-associated BIDS entities - default: `None`         |
| `--mask-query`        | `preprocess.query.mask`        | string query for custom mask-associated BIDS entities - default: `None` |
| `--fmap-query`        | `preprocess.query.fmap`        | string query for fieldmap-associated BIDS entities - default: `None`    |

### Metadata

If provided via command-line or configuration, metadata values will be used in the
workflow. Otherwise, data will be assumed from appropriate keys in the JSON sidecar
files:

| Argument                   | Config Key                         | Description                                                                                                                                                          |
| :------------------------- | :--------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--pe-dirs <direction>`    | `preprocess.metadata.pe_dirs`      | set phase encoding direction for dwi acquisition, overwriting value provided in metadata (JSON) file; invoke multiple times for multple directions - default: `None` |
| `--echo-spacing <spacing>` | `preprocess.metadata.echo_spacing` | estimated echo spacing to use for all dwi acquisitions, value in metadata (JSON) file will take priority - default: `None`                                           |

### Denoise

Denoising of diffusion data based on random matrix theory.

| Argument                          | Config Key                     | Description                                                    |
| :-------------------------------- | :----------------------------- | :------------------------------------------------------------- |
| `--denoise-skip`                  | `preprocess.denoise.skip`      | skip denoising step                                            |
| `--denoise-map`                   | `preprocess.denoise.map_`      | output noise map (the estimated level `sigma` in the data)     |
| `--denoise-estimator <estimator>` | `preprocess.denoise.estimator` | noise level estimator; one of `Exp1`, `Exp2` - default: `Exp2` |

### Unring

Minimization of Gibbs ringing artifacts based on local subvoxel-shifts.

| Argument                   | Config Key               | Description                                           |
| :------------------------- | :----------------------- | :---------------------------------------------------- |
| `--unring-skip`            | `preprocess.unring.skip` | skip unringing step                                   |
| `--unring-axes [axes ...]` | `preprocess.unring.axes` | space-separated slice axes; default: `0 1` (e.g. x-y) |

### Distortion correction

The distortion correction step (susceptibility + eddy current) is usually the most
time-consuming step. The current implementations include:

- `topup` (`topup` + `eddy`)
- `fieldmap` (`topup` + `eddy` using field maps found in the `fmap` directory)
- `eddymotion`
- `fugue`

| Argument                      | Config Key                    | Description                                                                                                                                                 |     |
| :---------------------------- | :---------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------- | --- |
| `--undistort-method <method>` | `preprocess.undistort.method` | distortion correction method (one of `topup`, `fieldmap`, `eddymotion`, `fugue`); `topup` performed unless skipped or using `eddymotion` - default: `topup` |     |

> [!Note]
> Tool-specific parameters will have no effect if the tool is not invoked (e.g.
> parameters for `eddymotion` will have no effect on `topup`)

#### FSL

| Argument                  | Config Key                  | Description                                                                                                                                                                    |
| :------------------------ | :-------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--topup-skip`            | `preprocess.topup.skip`     | skip `topup` step                                                                                                                                                              |
| `--topup-config <method>` | `preprocess.topup.config`   | `topup` configuration file; custom-config can be provided as a path or choose from one of the following: `b02b0`, `b02b0_macaque`, `b02b0_marmoset` - default: `b02b0_macaque` |
| `--eddy-skip`             | `preprocess.eddy.skip`      | skip `eddy` step                                                                                                                                                               |
| `--eddy-slm <model>`      | `preprocess.eddy.slm`       | diffusion gradient model for generating eddy currents; one of `None`, `linear`, `quadratic` - default: `None`                                                                  |
| `--eddy-cnr`              | `preprocess.eddy.cnr_maps`  | generate cnr maps                                                                                                                                                              |
| `--eddy-repol`            | `preprocess.eddy.repol`     | replace outliers                                                                                                                                                               |
| `--eddy-residuals`        | `preprocess.eddy.residuals` | generate 4D residual volume                                                                                                                                                    |
| `--eddy-shelled`          | `preprocess.eddy.shelled`   | indicate diffusion data is shelled, skipping check                                                                                                                             |

> [!NOTE]
> FSL's eddy expects the readout time (echo spacing \* (number of phase encodes - 1)) to
> be within 0.01 and 0.2. If outside of this range, the readout time will be doubled or
> halved accordingly with a warning message. To avoid this, one can also manually
> provide an echo spacing value.

#### Eddaymotion

| Argument             | Config Key                    | Description                                                    |
| :------------------- | :---------------------------- | :------------------------------------------------------------- |
| `--eddymotion-skip`  | `preprocess.eddymotion.skip`  | skip `eddymotion` step                                         |
| `--eddymotion-iters` | `preprocess.eddymotion.iters` | number of iterations to repeat for `eddymotion` - default: `2` |

#### Fugue

> [!NOTE] > `FUGUE` is included as an option to perform distortion correction on legacy
> datasets acquired with a single phase-encode direction and a fieldmap. Original /
> provided echo-spacing value will be used in this step.

| Argument         | Config Key                | Description                         |
| :--------------- | :------------------------ | :---------------------------------- |
| `--fugue-skip`   | `preprocess.fugue.skip`   | skip fugue step                     |
| `--fugue-smooth` | `preprocess.fugue.smooth` | 3D Gaussian smoothing sigma (in mm) |

### Biascorrection

B1 field inhomogeneity correction prior to registration (if performed)

| Argument                           | Config Key                       | Description                                               |
| :--------------------------------- | :------------------------------- | :-------------------------------------------------------- |
| `--biascorrect-skip`               | `preproess.biascorrect.skip`     | skip biascorrection step                                  |
| `--biascorrect-spacing <spacing>`  | `preprocess.biascorrect.spacing` | initial mesh resolution in mm - default: `100.00`         |
| `--biascorrect-iters <iterations>` | `preprocess.biascorrect.iters`   | number of iterations - default: `1000`                    |
| `--biascorrect-shrink <factor>`    | `preprocess.biascorrect.shrink`  | shrink factor applied to spatial dimension - default: `4` |

### Registration

Rigid (6 degrees-of-freedom) alignment with the anatomical T1w using `Greedy`.

| Argument                        | Config Key                   | Description                                                                                                             |
| :------------------------------ | :--------------------------- | :---------------------------------------------------------------------------------------------------------------------- |
| `--register-skip`               | `preprocess.register.skip`   | skip registration to participant anatomical                                                                             |
| `--register-metric <metric>`    | `preprocess.register.metric` | similarity metric to use for registration; one of `SSD`, `MI`, `NMI`, `MAHAL` - default: `NMI`                          |
| `--register-iters <iterations>` | `preprocess.register.iters`  | number of iterations per level of multi-res - default: `50x50`                                                          |
| `--register-init <method>`      | `preprocess.register.init`   | initialization method; one of `identity` (NIFTI Header), `image-centers` (matching image centers) - default: `identity` |
