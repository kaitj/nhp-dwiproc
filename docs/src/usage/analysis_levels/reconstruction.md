# Reconstruction

The `reconstruction` stage models preprocessed diffusion data using DTI and
FOD models. Whole-brain tractography is also generated.

## Stage-specific optional arguments

### Query

Query options for preprocessing:

| Argument              | Config Key                         | Description                                                             |
| :-------------------- | :--------------------------------- | :---------------------------------------------------------------------- |
| `--participant-query` | `reconstruction.query.participant` | string query for 'subject' and 'session' - default: `None`              |
| `--dwi-query`         | `reconstruction.query.dwi`         | string query for DWI-associated BIDS entities - default: `None`         |
| `--t1w-query`         | `reconstruction.query.t1w`         | string query for T1w-associated BIDS entities - default: `None`         |
| `--mask-query`        | `reconstruction.query.mask`        | string query for custom mask-associated BIDS entities - default: `None` |

### Tractography

| Argument                      | Config Key                                 | Description                                                                                                         |
| :---------------------------- | :----------------------------------------- | :------------------------------------------------------------------------------------------------------------------ |
| `--single-shell`              | `reconstruction.tractography.single_shell` | indicate single shell data                                                                                          |
| `--shells <shell>`            | `reconstruction.tractography.shells`       | b-value of shells (b0 must be explicitly included); invoke multiple times for multiple shells                       |
| `--lmax <lmax>`               | `reconstruction.tractography.lmax`         | maximum harmonic degree for each shell (b=0 must be explicitly included); invoke multiple times for multiple shells |
| `--steps <steps>`             | `reconstruction.tractography.steps`        | step size (in mm) for tractography - default: `0.5 x voxel size`                                                    |
| `--cutoff <cutoff>`           | `reconstruction.tractography.cutoff`       | FOD cutoff amplitude for track termination - default: `0.10`                                                        |
| `--streamlines <streamlines>` | `reconstruction.tractography.streamlines`  | number of streamlines to select - default: `10000`                                                                  |
| `--max-length <max-length>`   | `reconstruction.tractography.max_length`   | maximum length (in mm) for a track (default: 100 x voxel size)                                                      |
| `--tractography-method`       | `reconstruction.tractography.method`       | tractography seeding method; one of `wm`, `act` - default: `wm`                                                     |

> [!NOTE]
>
> - If using `--single-shell`, the `ss3t_csd_beta1` algorithm from `Mrtrix3Tissue` is
>   used to estimate fiber orientation distribution maps.

> [!WARNING]
> Extremely poor contrast between WM and GM may result in an error being thrown during
> tissue normalization if using the single-shell method. If this occurs, The workflow
> will revert to using the multi-shell method, using only the WM and CSF FODs for
> normalization to provide some compensation for partial volume effects.

#### Anatomically constrained

| Argument                       | Config Key                                  | Description                                                                               |
| :----------------------------- | :------------------------------------------ | :---------------------------------------------------------------------------------------- |
| `--tractography-act-backtrack` | `reconstruction.tractography.act.backtrack` | allow tracks to be truncated and re-tracked due to poor structural termination during ACT |
| `--tractography-act-nocrop`    | `reconstruction.tractography.act.gmwmi`     | do not crop streamline end points as they cross GM-WM interface (default: `False`)        |
