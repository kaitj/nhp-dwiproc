<!-- prettier ignore -->
<div align="center">
<h1> NHP Diffusion Processing</br>(nhp-dwiproc) </h1>

![Python3](https://img.shields.io/badge/python->=3.11-blue.svg)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![stability-stable](https://img.shields.io/badge/stability-experimental-orange.svg)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/HumanBrainED/blob/main/LICENSE)
[![Documentation](https://img.shields.io/badge/documentation-8CA1AF?logo=readthedocs&logoColor=fff)](#)

</div>

`nhp-dwiproc` is an application, leveraging features of [NiWrap] and [Styx] to
perform processing of non-human primate (NHP) diffusion datasets. The application
aims to provide flexible, reproducible workflows for various stages of processing
(e.g. preprocessing, tractography, etc) across various acquisition protocols.

<!-- Generalized workflow figure to be included here -->

## Requirements

You will need the following pre-requisites:

| Tool | Version |
| :-: | :-: |
| [Python] | 3.11+ |
| [ANTs] | 2.5.3 |
| [c3d] | 1.1.0 |
| [FSL] | 6.0.5 |
| [Greedy] | 1.0.1 |
| [Mrtrix3] | 3.0.4 |
| [Mrtrix3Tissue] | 5.2.8 |

> [!Note]
> [Mrtrix3Tissue] is only required if processing single-shell data.

## Installation

You can install `nhp-dwiproc` using `pip`:

```shell
pip install git+https://github.com/HumanBrainED/nhp-dwiproc
```

For additional details, please consult the [documentation].

## Usage

To get started, try using the boilerplate command:

```shell
nhp_dwiproc <bids_directory> <output_directory> <processing_stage>
```

To see all arguments, run:

```shell
nhp_dwiproc --help
```

## Documentation

For detailed application information, including advanced usage, please visit our
[documentation]

## Contributing

Contributions to `nhp-dwiproc` are welcome! Please refer to [Contributions] page for information on how to contribute, report issues, or submit pull requests.

## License

`nhp-dwiproc` is distributed under the MIT license. See the [LICENSE] file for details.

## Support

If you encounter any issues or have questions, pleasee open an issue on the
[issue tracker]

<!-- Links -->
[Contributions]: https://github.com/HumanBrainED/nhp-dwiproc/blob/main/CONTRIBUTING.md
[LICENSE]: https://github.com/HumanBrainED/nhp-dwiproc/blob/main/LICENSE
[Niwrap]: https://github.com/childmindresearch/niwrap
[Styx]:https://github.com/childmindresearch/styx
[documentation]: #
[issue tracker]: https://github.com/HumanBrainED/nhp-dwiproc/issues/new/choose
<!-- Software dependency links -->
[Python]: https://www.python.org/
[ANTs]:   https://github.com/ANTsX/ANTs
[c3d]:    http://www.itksnap.org/pmwiki/pmwiki.php?n=Convert3D.Convert3D
[FSL]:    https://fsl.fmrib.ox.ac.uk/fsl/docs/#/
[Greedy]: https://sites.google.com/view/greedyreg/about
[Mrtrix3]: https://www.mrtrix.org/
[Mrtrix3Tissue]: https://3tissue.github.io/
