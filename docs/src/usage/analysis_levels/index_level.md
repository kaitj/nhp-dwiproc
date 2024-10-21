# Index

`index` level processing is a simple workflow intended to index the input directory for
`bids2table`.

    dataset_root
    ├── bids
    │   ├── sub-001
    │   ├── sub-002
    │   │   ├── anat
    │   │   └── dwi
    └── derivatives
        ├── custom_masks
        │   ├── sub-001
        │   └── sub-002
        └── nhp-dwiproc

> [!TIP]
>
> - Run the `index` level whenever  new inputs are available (e.g. acquired new data or in-between
> processing stages to index newly created files)
> - Run in the directory containing both your input and output directory; for example,
> given the following directory structure, the index level would be preferably run at the
> `dataset_root` of the input

## Level-specific optional arguments

| Argument      | Config Key        | Description                                           |
|:--------------|:------------------|:------------------------------------------------------|
| `--overwrite` | `index.overwrite` | overwrite previously created index - default: `False` |
