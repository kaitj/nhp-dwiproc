# Tractography level

`tractography` level processing is intended to generate whole-brain
tractography from preprocessed data. This includes modelling and reconstruction
using both DTI and FOD models, to generate quantitative maps and to use in tractography
generation.

## Level-specific optional arguments
| Argument | Config Key | Description |
| :- | :- | :- |
| `--single-shell` | `participant.tractography.single_shell` | flag to process single-shell data |
| `--shells [shell ...]` | `participant.tractography.shells` | space separated list of b-values (b=0 must be included explicitly) |
| `--lmax [lmax ...]` | `participant.tractography.lmax` | space separated list of maximum harmonic degrees (b=0 must be included explicitly) |
| `--steps <steps>` | `participant.tractography.steps` | step size (in mm) for tractography - default: `0.5 x voxel size` |
| `--tractography-method <method>` | `participant.tractography.method` | tractography seeding method (one of `wm`, `act`) - default: `wm` |
| `--fa-thresh <threshold>` | `participant.tractography.fa_thresh` | threshold to binarize FA map to generate WM mask - default: `0.10` |
| `--cutoff <cutoff>` | `participant.tractography.cutoff` | cutoff FOD amplitude for track termination - default: `0.10` |
| `--streamlines <streamlines>` | `participant.tractography.streamlines` | number of streamlines to select - default: `10000` |

### Tractography methods

Various methods are implemented for performing tractography.

* `wm` - performs Mrtrix3's iFOD2 method with an FA thresholded WM mask to
spatially constrain candidate streamline paths; threshold is defined using
the `--fa-thresh` argument.
* `act` - performs anatomically constrained tractography (_coming soon_)

</br>
> [!NOTE]
> * If using `--single-shell`, the `msmt_csd` algorithm is still used to estimate
> fiber orientation distribution maps without the use of gray matter response function, which
> results in an error. This allows for the FOD map to be take advantage of the CSF suppression
> in the algorithm.
> * Diffusion tensor fitting is performed two stages, fitting to the log-signal first using
> weight least squares (WLS) and additional iteration of WLS fitting
