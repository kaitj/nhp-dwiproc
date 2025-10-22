# Surface mapping of tracts

Individual tracts can be extracted and mapped to a surface. To help facilitate this
process, additional string query arguments can be used. Tracts are extracted with the
aid of inclusion and exclusion regions of interests (ROIs). Below is an example
command used to extract a single tract and perform surface mapping.

```bash
nhp_dwiproc <bids_dir> <output_dir> connectivity \
  --participant-query "sub=='example'" \
  --tract-query "hemi=='L' & label=='tract'" \
  --surf-query "hemi=='L'
```

> [!NOTE] > `hemi` and `label` are associated with the entities, while the tract
> extracted in the previous example is "tract" of the left hemisphere.
