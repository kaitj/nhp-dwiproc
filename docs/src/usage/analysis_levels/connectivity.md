# Connectivity level

`connectivity` level is intended to generate useful output files that may be directly or
indirectly useful for analysis, such as structural connectivity matrices (providing
information about the connectivity between pairs of regions from a parcellation), or
identifiy individual tracts using regions of interest.

## Level-specific optional arguments

| Argument | Config Key | Description |
| :- | :- | :- |
| `--atlas <atlas>` | `participant.connectivity.atlas` | volumetric atlas name (assumed to be processed) for connectivity matrix |
| `--radius <radius>` | `participant.connectivity.radius` | distance (in mm) to map to nearest parcel (default: 2.00) |

If you wish to query individual tracts using inclusion / exclusion ROIs, you may also
do so. By default, only a tract-density map is generated from these. Additionally, if
an associated surface can be found, end points of the tract are mapped to the surfaces.

> [!NOTE]
> End points are only mapped if an inflated surface can be found!

| Argument | Config Key | Description |
| :- | :- | :- |
| `--vox-mm` | `participant.connectivity.vox_mm` | isotropic voxel size (in mm) or space-separated listed of voxel sizes to map tracts to |
| `--surf-query` | `participant.connectivity.query_surf` | string query for bids entities associated with surfaces to perform ribbon constrained mapping of streamlines to (subject & session is assumed); surface type (e.g. white, pial, etc.) will be automatically identified |
| `--include-query` | `participant.connectivity.query_include` | string query for bids entities associated with inclusion ROI(s) (subject & session is assumed) |
| `--exclude-query` | `participant.connectivity.query_exclude` | string query for bids entities associated with exclusion ROI(s) (subject & session is assumed) |
| `--truncate-query` | `participant.connectivity.query_truncate` | string query for bids entities associated with ROI(s) in which streamlines should be truncated if entered (subject & session is assumed) |

> [!NOTE]
> Either atlas or ROIs should be provided. The workflow will throw an error if both
> are provided.

<!-- TODO: add an example (can go under advanced) -->
