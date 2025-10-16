# Tractography level

`tractography` level processing is intended to generate whole-brain
tractography from preprocessed data. This includes modelling and reconstruction
using both DTI and FOD models, to generate quantitative maps and to use in tractography
generation.

## Level-specific optional arguments

| Argument                      | Config Key                              | Description                                                                        |
| :---------------------------- | :-------------------------------------- | :--------------------------------------------------------------------------------- |
| `--single-shell`              | `participant.tractography.single_shell` | flag to process single-shell data                                                  |
| `--shells [shell ...]`        | `participant.tractography.shells`       | space separated list of b-values (b=0 must be included explicitly)                 |
| `--lmax [lmax ...]`           | `participant.tractography.lmax`         | space separated list of maximum harmonic degrees (b=0 must be included explicitly) |
| `--steps <steps>`             | `participant.tractography.steps`        | step size (in mm) for tractography - default: `0.5 x voxel size`                   |
| `--tractography-method`       | `participant.tractography.method`       | tractography seeding method; one of `wm`, `act` - default: `wm`                    |
| `--cutoff <cutoff>`           | `participant.tractography.cutoff`       | cutoff FOD amplitude for track termination - default: `0.10`                       |
| `--streamlines <streamlines>` | `participant.tractography.streamlines`  | number of streamlines to select - default: `10000`                                 |
| `--max-length <max-length>`   | `participant.tractography.maxlength`    | maximum length (in mm) for a track (default: 100 x voxel size)                     |

</br>
> [!NOTE]
> - If using `--single-shell`, the `ss3t_csd_beta1` algorithm from `Mrtrix3Tissue` is used to estimate
> fiber orientation distribution maps.
> - Diffusion tensor fitting is performed two stages, fitting to the log-signal first using
> weight least squares (WLS) and additional iteration of WLS fitting

> [!IMPORTANT]
> If there is not enough contrast to different WM From GM, the single-shell method may error when
> attempting to normalize the tissue. In these situations, the application will automatically
> revert to using the same algorithm as multi-shell, but using only `WM` and `CSF` for normalization
> to provide some compensation for partial volume effects.

### Anatomically constrained tractography optional arguments

| Argument         | Config Key                               | Description                                                                               |
| :--------------- | :--------------------------------------- | :---------------------------------------------------------------------------------------- |
| `--backtrack`    | `participant.tractography.act.backtrack` | allow tracks to be truncated and re-tracked due to poor structural termination during ACT |
| `--nocrop-gmwmi` | `participant.tractography.act.gmwmi`     | do not crop streamline end points as they cross GM-WM interface (default: `False`)        |
