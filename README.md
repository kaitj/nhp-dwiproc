# NHP Diffusion Processing

![Python3](https://img.shields.io/badge/python-3.11-blue.svg)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

<!--
![Python3](https://img.shields.io/badge/python->=3.8,_<3.13-blue.svg)
[![Tests](https://github.com/kaitj/PRIME-DE-DiffusionPreproc/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/kaitj/PRIME-DE-DiffusionPreproc/actions/workflows/test.yml?query=branch%3Amain)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/childmindresearch/template-python-repository/blob/main/LICENSE)
[![Documentation Status](https://readthedocs.org/projects/scattr/badge/?version=stable)](https://scattr.readthedocs.io/en/stable/?badge=stable)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.7636506.svg)](https://doi.org/10.5281/zenodo.7636506)
-->

_(Currently in active development)_

A BIDS app for performing diffusion processing on the NHP datasets (e.g. FOD reconstruction, tractography). Built to process diffusion data from PRIME-DE.

## Usage

Prepend the commands with the necessary arguments for Docker / Apptainer:

```bash
nhp_dwiproc <bids_dir> <output_dir> <index/participant>
```

_Run `nhp_dwiproc --help` to see all optional arguments._

## Notes

This workflow was written using [Niwrap](https://github.com/childmindresearch/niwrap) +
[Styx](https://github.com/childmindresearch/styx), which provide runners to use with containers (e.g. Docker, Singularity / Apptainer).

### Singularity

If using Singularity, please:

1. Download the necessary containers
2. Map their local paths to the necessary image config yaml file.

_See example yaml config
[here](https://github.com/kaitj/nhp-dwiproc/blob/main/src/nhp_dwiproc/app/resources/images.yaml)._
