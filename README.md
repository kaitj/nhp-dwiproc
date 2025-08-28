<h1> NHP Diffusion Processing (nhp-dwiproc) </h1>

![Python3](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![stability-stable](https://img.shields.io/badge/stability-experimental-orange.svg)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/kaitj/nhp-dwiproc/blob/main/LICENSE)
[![Documentation](https://img.shields.io/badge/documentation-8CA1AF?logo=readthedocs&logoColor=fff)](https://kaitj.github.io/nhp-dwiproc)

`nhp-dwiproc` is a BIDS application, leveraging features of [NiWrap] to perform 
processing of diffusion MRI data across non-human primate (NHP) and human datasets. The 
application aims to provide robust and reproducible workflows for different processing
stages (e.g. preprocessing, tractography, etc.) across various acquisition protocols.

> [!Important]
> Indexes generated with `v0.1.x` are incompatible with `v0.2.x+`, as well as latest 
> development versions.

<!-- Generalized workflow figure to be included here -->

## Tools

The following tools are used throughout the workflows.

| Tool | Version |
| :-: | :-: |
| [Python] | 3.11+ |
| [ANTs] | 2.5.3 |
| [c3d] | 1.1.0 |
| [FSL] | 6.0.4 |
| [Greedy] | 1.0.1 |
| [Mrtrix3] | 3.0.4 |
| [Mrtrix3Tissue] | 5.2.8 |

> [!Note]
> * Tools only need to be installed if running on local machine without the use of 
> containers 
> * If running with Singularity / Apptainer, containers need to be downloaded / pulled
> * [Mrtrix3Tissue] is only required if processing single-shell data.

## Installation

You can install the latest stable version of `nhp-dwiproc` using `pip`:

```sh
pip install git+https://github.com/HumanBrainED/nhp-dwiproc
```

## Usage

To get started, try the following command:

```sh
nhp_dwiproc --help
```

## Documentation

For detailed application information, including advanced usage, please visit the
[documentation page].

## Contributing

Contributions to `nhp-dwiproc` are welcome! Please refer to [Contributions] page for
information on how to contribute, report issues, or submit pull requests.

## License

`nhp-dwiproc` is distributed under the MIT license. See the [LICENSE] file for details.

## Support

If you encounter any issues or have questions, please open an issue on the
[issue tracker]

<!-- Links -->
[Contributions]: https://github.com/kaitj/nhp-dwiproc/blob/main/CONTRIBUTING.md
[LICENSE]: https://github.com/kaitj/nhp-dwiproc/blob/main/LICENSE
[Niwrap]: https://styx-api.github.io
[documentation page]: https://kaitj.github.io/nhp-dwiproc
[issue tracker]: https://github.com/kaitj/nhp-dwiproc/issues
<!-- Software dependency links -->
[Python]: https://www.python.org/
[ANTs]:   https://github.com/ANTsX/ANTs
[c3d]:    http://www.itksnap.org/pmwiki/pmwiki.php?n=Convert3D.Convert3D
[FSL]:    https://fsl.fmrib.ox.ac.uk/fsl/docs/#/
[Greedy]: https://sites.google.com/view/greedyreg/about
[Mrtrix3]: https://www.mrtrix.org/
[Mrtrix3Tissue]: https://3tissue.github.io/
