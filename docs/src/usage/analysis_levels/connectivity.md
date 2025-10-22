# Connectivity level

`connectivity` level is intended to generate useful output files that may be directly or
indirectly useful for analysis, such as structural connectivity matrices (providing
information about the connectivity between pairs of regions from a parcellation), or
identify individual tracts using regions of interest.

## Level-specific optional arguments

### Query

Query options for preprocessing:

| Argument              | Config Key                       | Description                                                |
| :-------------------- | :------------------------------- | :--------------------------------------------------------- |
| `--participant-query` | `connectivity.query.participant` | string query for 'subject' and 'session' - default: `None` |

### Method

Method of analysis (dictates what output(s) are generated):

| Argument   | Config Key            | Description                                                                                    |
| :--------- | :-------------------- | :--------------------------------------------------------------------------------------------- |
| `--method` | `connectivity.method` | type of connectivity analysis to perform; one of `connectome`, `tract` - default: `connectome` |

#### Connectome

Options associated with `connectome` method:

| Argument            | Config Key                 | Description                                                             |
| :------------------ | :------------------------- | :---------------------------------------------------------------------- |
| `--atlas <atlas>`   | `connectivity.opts.atlas`  | volumetric atlas name (assumed to be processed) for connectivity matrix |
| `--radius <radius>` | `connectivity.opts.radius` | distance (in mm) to map to nearest parcel (default: 2.00)               |

If you wish to query individual tracts using inclusion / exclusion ROIs, you may also
do so. By default, only a tract-density map is generated from these. Additionally, if
associated surface(s) can be found, tracts passing through the cortical ribbon are
mapped to the surface.

> [!NOTE]
>
> - Tracts are only mapped if an inflated surface can be found!
> - Non-lateralized tracts need to manually mapped as there is no associated `hemi`
>   entity.

| Argument        | Config Key                 | Description                                                                                                                                                                                                            |
| :-------------- | :------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--vox-mm`      | `connectivity.vox_mm`      | isotropic voxel size (in mm) or space-separated listed of voxel sizes to map tracts to                                                                                                                                 |
| `--tract-query` | `connectivity.tract_query` | string query for bids entities associated with tract (subject & session is assumed); associated ROIs should be part of dataset descriptions that contain 'include', 'exclude', 'stop' keywords for respective ROIs.    |
| `--surf-query`  | `connectivity.surf_query`  | string query for bids entities associated with surfaces to perform ribbon constrained mapping of streamlines to (subject & session is assumed); surface type (e.g. white, pial, etc.) will be automatically identified |

> [!NOTE]
> Either atlas or ROIs should be provided. The workflow will throw an error if both
> are provided.

An surface mapping example can be found [here](../advanced/tract.md), under the
advanced pages.
