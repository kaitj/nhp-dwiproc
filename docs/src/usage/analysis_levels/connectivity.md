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
an associated surface can be found, tracts passing through the cortical ribbon are
mapped to the surface.

> [!NOTE]
> - Tracts are only mapped if an inflated surface can be found!
> - Non-lateralized tracts need to manually mapped as there is no associated `hemi`
> entity.



| Argument | Config Key | Description |
| :- | :- | :- |
| `--vox-mm` | `participant.connectivity.vox_mm` | isotropic voxel size (in mm) or space-separated listed of voxel sizes to map tracts to |
| `--tract-query` | `participant.connectivity.query_tract` | string query for bids entities associated with tract (subject & session is assumed); associated ROIs should be part of dataset descriptions that contain 'include', 'exclude', 'stop' keywords for respective ROIs. |
| `--surf-query` | `participant.connectivity.query_surf` | string query for bids entities associated with surfaces to perform ribbon constrained mapping of streamlines to (subject & session is assumed); surface type (e.g. white, pial, etc.) will be automatically identified |

> [!NOTE]
> Either atlas or ROIs should be provided. The workflow will throw an error if both
> are provided.

An surface mapping example can be found [here](../advanced/tract.md), under the advanced pages.
