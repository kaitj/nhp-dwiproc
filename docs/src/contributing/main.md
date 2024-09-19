# Contributing

## Dependencies

`nhp-dwiproc` relies on a number of internal and external depedencies in order to build a generalizable and reproducible
workflow. Python package dependencies are managed with `uv`. You can find installation instructions on their
[website](https://astral.sh/uv). There are also a number of external dependencies outside of python, including
neuroimaging tools like `ANTs`, `mrtrix`, `c3d`, and others listed in the [introduction](../index.md).

## Setting up the development environment

Clone the repository and install the python dependencies using `uv`:

```bash
git clone https://github.com/HumanBrainED/nhp-dwiproc nhp-dwiproc
cd nhp-dwiproc
uv venv --python python3.11 nhp-dwiproc-venv
source activate nhp-dwiproc-venv/bin/activate
uv pip install -e .
```

</br>

Install external dependencies or make use of `styx`'s container runners (see [Runners](../runners/main.md) for details).

You can then run `nhp-dwiproc` with the following command:

```bash
uv run nhp_dwiproc
```

## Code formatting

`nhp-dwiproc` uses `pre-commit`, as well as a Github action workflow to check for and address formatting issues.
These use the following:

* `ruff` - formatting and linting
* `mypy` - type checking
* `language-formatters-pre-commit-hooks` - pretty format YAML and TOML files
* `pre-commit-hooks` - fix string casing, format JSON files

To install the `pre-commit` configuration, run the following:

```bash
uv run pre-commit install
```

## Adding features / fixing bugs

To contribute a change to the code base, checkout a new branch from the main branch and then make your changes.

```bash
git checkout -b feature/your-feature-naame main
```

## Pull requests

Once you have made your changes and are ready to contribute, follow the steps to submit a pull request:

1. Push your changes back.

```bash
git push origin feature/your-feature-name
```

2. Create a pull request to merge your branch into the main branch. Provide a clear description of your changes in the
pull request message.

### Guidelines

* Write clear and concise commit messages.
* Test your changes thoroughly before submitting a pull request
* If the pull request adds functionality, the documentation should also be updated.

> [!IMPORTANT]
> Contributed code will be **licensed under the same [license](LICENSE) as the rest of
> the repository**. If you did not write the code yourself, you must ensure the existing
> license is compatible and include the license information in the contributed files,
> or obtain permission from the original author to relicense the contributed code.

It is okay to submit work-in-progress and seek feedback - you will likely be asked to make additional changes or asked
clarification questions.

### Review process

All pull requests will undergo a review process before being accepted. Reviewers may
provide feedback or request changes to ensure the quality of the codebase.
