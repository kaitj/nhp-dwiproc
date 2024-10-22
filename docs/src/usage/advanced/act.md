# Anatomically constrained tractography (ACT)

Performing anatomically constrained tractography (ACT) makes use of anatomical
information (from segmentations, tissue maps, etc.) to improve tractography generation.
This often requires additional tissue segmentation images. However, current workflow
implementations generate these images using parameters optimized for humans and are not
suitable for non-human primate datasets. While the tissue generation will be added as
part of the preprocessing workflow in the future, the advantages of ACT can already
be used in the `tractography` analysis-level of `nhp-dwiproc` if a tissue segmentation
image is already available.

> [!NOTE]
>
> - The tissue segmentation image should be compatible with Mrtrix3's definition of a
> 5-tissue type image - 4D image where volumes are:
>   1. cortical grey matter (GM)
>   2. subcortical grey matter (SGM)
>   3. white matter (WM)
>   4. cerebrospinal fluid (CSF)
>   5. pathological tissue (Path)
>
> - Image should be specific to the participant being processed

Below is an example script used to generate a tissue segmentation image from
GM and WM masks, plus `Freesurfer` segmentations. This script performs
similarly to calling Mrtrix3's `5ttgen freesufer`.

```python
{{#include pysrc/act.py}}
```

[Full source](pysrc/act.py)

> [!NOTE]
>
> - The script above uses the same libraries / packages used in `nhp-dwiproc`
> - Script is simplified; additional steps may be necessary for actual use (e.g.
> resampling)
