# Connectivity level

`connectivity` level is intended to generate structural connectivity matrices, providing
information about the connectivity between pairs of regions from a parcellation.

## Level-specific optional arguments
| Argument | Config Key | Description |
| :- | :- | :- |
| `--atlas <atlas>` | `participant.connectivity.atlas` | volumetric atlas name (assumed to be processed) for connectivity matrix |
| `--radius <radius>` | `participant.connectivity.radius` | distance (in mm) to map to nearest parcel (default: 2.00) |
