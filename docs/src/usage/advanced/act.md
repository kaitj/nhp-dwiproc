# Anatomically constrained tractography (ACT)

Performing anatomically constrained tractography (ACT) requires the use of anatomical
information (from segmentations, tissue maps, etc.) to improve tractography generation.
While generation of this additional information is not presently part of the workflow,
the advantages of ACT can sitll be used in the `reconstruction` stage of `nhp-dwiproc`
if the additional tissue segmentation is externally available.

> [!NOTE]
> The tissue segmentation image should be participant-specific and compatible with
> Mrtrix3's definition of a 5-tissue type image - a 4D image where volumes are:
>
> 1. cortical grey matter (GM)
> 2. subcortical grey matter (SGM)
> 3. white matter (WM)
> 4. cerebrospinal fluid (CSF)
> 5. pathological tissue (Path)

Below is an example script used to generate a tissue segmentation image from
GM and WM masks, using `Freesurfer` segmentations. This script performs
similar to calling Mrtrix3's `5ttgen freesufer` on human data.

```python
{{#include pysrc/act.py}}
```

[Full source](pysrc/act.py)

> [!NOTE]
>
> - The script above uses the same libraries / packages used in `nhp-dwiproc`
> - Script is simplified; additional steps may be necessary for actual use (e.g.
>   resampling)
