# Contributing to nhp-dwiproc

Pull requests are always welcome, and we appreciate any help you give. Note that a code
of conduct applies to all spaces managed by the `nhp-dwiproc` project, including
issues and pull requests. Please see the [Code of Conduct](CODE_OF_CONDUCT.md) for
details.

## Contributing to code

### Setting up your development environment

Python package dependencies are managed by [uv](https://docs.astral.sh/uv/).

1. Clone the repository to your local machine:

   ```bash
   git clone https://github.com/kaitj/nhp-dwiproc
   ```

1. Create a new environment to install the library with dependencies, for example
using `uv`:

   ```bash
   uv venv --python python3.11 nhp-dwiproc-venv
   source activate nhp-dwiproc-venv/bin/activate
   ```

   Install `nhp-dwiproc` using the following command in the projects main directory.

   ```bash
   uv pip install -e .
   ```

   Also don't forget to setup the `pre-commit` hook, which ensures code style:

   ```bash
   uv run pre-commit install
   ```

1. Checkout a new branch for your changes from the main branch.
   ```bash
   git checkout -b feature/your-feature-name main
   ```

1. Make your changes.

### Submitting a pull request

Once you have made your changes and are ready to contribute, follow these steps to submit
a pull request:

1. Push your changes back:

   ```bash
   git push origin feature/your-feature-name
   ```

2. Create a pull request to merge your branch into the main branch. Provide a clear
description of your changes in the pull request message.

#### Pull request guidelines

* Write clear and concise commit messages
* Test your changes thoroughly before submitting a pull request
* If the pull request adds functionality, the documentation should also be updated.
Improving documentation helps users better understand how to use `nhp-dwiproc`.

#### Notes:
* Contributed code will be **licensed under the same [license](LICENSE) as the rest of
the repository**. If you did not write the code yourself, you must ensure the existing
license is compatible and include the license information in the contributed files,
or obtain permission from the original author to relicense the contributed code.
* It is okay to submit work in progress and seek feedback - you'll likely be asked to
make additional changes or asked clarification questions.

### Review process

All pull requests will undergo a review process before being accepted. Reviewers may
provide feedback or request changes to ensure the quality of the codebase.
