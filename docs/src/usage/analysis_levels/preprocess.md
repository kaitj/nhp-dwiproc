# Preprocess level

`preprocess` level processing is a workflow intended to perform preprocessing from raw
single-shell and multi-shell diffusion weighted data. Currently, the following types of
acquisitions can be preprocessed:

- Single-phase encoding direction (distortion correction method: `fsl`)
- Opposite-phase encoding direction (distortion correction method: `fsl`).

Preprocessing parameters can be updated or stages of preprocessing can be skipped entirely. Given
the multitude of options, follow sub-sections will break down the different stages and associated
options.

## Level-specific optional arguments

### Metadata

If provide via command-line or configuration, metadata values will be used in the workflow. Otherwise, data will be assumed from appropriate keys in the JSON sidecar files:

| Argument                    | Config Key                                     | Description                                                                                                                                                        |
|:----------------------------|:-----------------------------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--pe-dirs [direction ...]` | `participant.preprocess.metadata.pe_dirs`      | set phase encoding direction for dwi acquisition (space-separated for multiple acquisitions), overwriting value provided in metadata (JSON) file - default: `None` |
| `--echo-spacing <spacing>`  | `participant.preprocess.metadata.echo_spacing` | estimated echo spacing to use for all dwi acquisitions, value in metadata (JSON) file will take priority - default: `None`                                       |

### Denoise

Denoising (based on random matrix theory) of the diffusion data is the first stage to be
performed.

| Argument                          | Config Key                                 | Description                                                                                             |
|:----------------------------------|:-------------------------------------------|:--------------------------------------------------------------------------------------------------------|
| `--denoise-skip`                  | `participant.preprocess.denoise.skip`      | flag to skip denoising stage                                                                            |
| `--denoise-extent [extent ...]`   | `participant.preprocess.denoise.extent`    | patch size of denoising filter - default: smallest isotropic patch size exceeding number of dwi volumes |
| `--denoise-map`                   | `participant.preprocess.denoise.map`       | flag to output noise map (the estimated level `sigma` in the data)                                      |
| `--denoise-estimator <estimator>` | `participant.preprocess.denoise.estimator` | noise level estimator; one of `Exp1`, `Exp2` - default: `Exp2`                                          |

### Unring

Minimization of Gibbs ringing artifacts based on local subvoxel-shifts is performed next.

| Argument                     | Config Key                              | Description                                                |
|:-----------------------------|:----------------------------------------|:-----------------------------------------------------------|
| `--unring-skip`              | `participant.preprocess.unring.skip`    | flag to skip unringing stage                               |
| `--unring-axes [axes ...]`   | `participant.preprocess.unring.axes`    | space-separated slice axes; default: `0 1` (e.g. x-y)      |
| `--unring-nshifts <nshifts>` | `participant.preprocess.unring.nshifts` | discretization of subpixel spacing (default: `20`)         |
| `--unring-minw <minw>`       | `participant.preprocess.unring.minW`    | left border of window used for computation (default: `1`)  |
| `--unring-maxw <maxw>`       | `participant.preprocess.unring.maxW`    | right border of window used for computation (default: `3`) |

### Distortion correction

The next stage (and usually the most time-consuming) is the distortion correction stage (susceptibility + eddy current). The current implementations include:

- `topup` (`topup` + `eddy`)

| Argument                      | Config Key                                | Description                                                                           |
|:------------------------------|:------------------------------------------|:--------------------------------------------------------------------------------------|
| `--undistort-method <method>` | `participant.preprocess.undistort.method` | distortion correction method; one of `topup`, `fieldmap`, `eddymotion` - default: `topup` |
| `--eddy-skip`                 | `participant.preprocess.eddy.skip`        | flag to skip eddy correction stage                                                    |

_`fieldmap` uses the `topup` method, but uses the opposite phase-encoding field map from the
`fmap` bids directory instead for `topup._

#### FSL

| Argument                  | Config Key                              | Description                                                                                                                                                                    |
|:--------------------------|:----------------------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--topup-skip`            | `participant.preprocess.topup.skip`     | flag to skip FSL `topup` stage                                                                                                                                                 |
| `--topup-config <config>` | `participant.preprocess.topup.config`   | `topup` configuration file; custom-config can be provided as a path or choose from one of the following: `b02b0`, `b02b0_macaque`, `b02b0_marmoset` - default: `b02b0_macaque` |
| `--eddy-slm <model>`      | `participant.preprocess.eddy.slm`       | model for how diffusion gradients generate eddy currents; one of `None`, `linear`, `quadratic` - default: `None`                                                               |
| `--eddy-cnr-maps`         | `participant.preprocess.eddy.cnr_maps`  | flag to generate cnr maps                                                                                                                                                      |
| `--eddy-repol`            | `participant.preprocess.eddy.repol`     | flag to replace outliers                                                                                                                                                       |
| `--eddy-residuals`        | `participant.preprocess.eddy.residuals` | flag to generate 4d residual volume                                                                                                                                            |
| `--eddy-data-is-shelled`  | `participant.preprocess.eddy.shelled`   | flag to skip eddy checking that data is shelled                                                                                                                                |

#### Eddaymotion

| Argument             | Config Key                                | Description                                                  |
|:---------------------|:------------------------------------------|:-------------------------------------------------------------|
| `--eddymotion-iters` | `participant.preprocess.eddymotion.iters` | number of iterations to repeat for eddymotion - default: `2` |

#### Fugue

> [!NOTE]
> `FUGUE` is included as an option to perform distortion correction
> on legacy datasets acquired with a single phase-encode direction and
> a fieldmap.

| Argument             | Config Key                                | Description                                                  |
|:---------------------|:------------------------------------------|:-------------------------------------------------------------|
| `--fugue-smooth` | `participant.preprocess.fugue.smooth` | 3D gaussian smoothing sigma (in mm) to be applied for FUGUE - default: `None` |

### Biascorrection

The last step prior to registration is a B1 field inhomogeneity correction.

| Argument                           | Config Key                                   | Description                                               |
|:-----------------------------------|:---------------------------------------------|:----------------------------------------------------------|
| `--biascorrect-spacing <spacing>`  | `participant.preprocess.biascorrect.spacing` | initial mesh resolution in mm - default: `100.00`         |
| `--biascorrect-iters <iterations>` | `participant.preprocess.biascorrect.iters`   | number of iterations - default: `1000`                    |
| `--biascorrect-shrink <factor>`    | `participant.preprocess.biascorrect.shrink`  | shrink factor applied to spatial dimension - default: `4` |

### Registration

For downstream analysis, the final stage of the preprocessing performs a --rigid
(6 degrees-of-freedom)-- alignment with the anatomical T1w using `Greedy`.

| Argument                        | Config Key                               | Description                                                                                    |
|:--------------------------------|:-----------------------------------------|:-----------------------------------------------------------------------------------------------|
| `--register-skip`               | `participant.preprocess.register.skip`   | skip registration to participant structural t1w                                                |
| `--register-metric <metric>`    | `participant.preprocess.register.metric` | similarity metric to use for registration; one of `SSD`, `MI`, `NMI`, `MAHAL` - default: `NMI` |
| `--register-iters <iterations>` | `participant.preprocess.register.iters`  | number of iterations per level of multi-res - default: `50x50`                                 |
