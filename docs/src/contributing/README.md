# Contributing

## Dependencies

`nhp-dwiproc` relies on a number of internal and external dependencies in order to
engineer a robust and reproducible workflow. Python package dependencies are managed
with [`uv`](https://astral.sh/uv). There are also a number of external neuroimaging tool
dependencies, including `ANTs`, `mrtrix`, `c3d`, and others listed in the
[introduction](../index.md).

## Setting up the development environment

Clone the repository and install the python dependencies using `uv`:

<!-- langtabs-start -->

```bash
git clone https://github.com/humanbrained/nhp-dwiproc nhp-dwiproc
cd nhp-dwiproc
uv sync
```

<!-- langtabs-end -->

Install external dependencies or make use of one of the container runners (see
[Runners](../runners/) for details).

You can then run `nhp-dwiproc` with the following command:

<!-- langtabs-start -->

```bash
uv run nhp_dwiproc
```

<!-- langtabs-end -->

## Code formatting

`nhp-dwiproc` uses `pre-commit` and Github action workflows to ensure a consistent
codebase. The following packages are used for linting and formatting:

- `ruff` - formatting and linting
- `mypy` - type checking
- `language-formatters-pre-commit-hooks` - pretty format YAML and TOML files
- `pre-commit-hooks` - fix string casing, format JSON files

To install the `pre-commit` configuration, run the following:

<!-- langtabs-start -->

```bash
uv run pre-commit install
```

<!-- langtabs-end -->

## Adding features / fixing bugs

To contribute a change to the code base, checkout a new branch from the main branch and
then make your changes.

<!-- langtabs-start -->

```bash
git checkout -b feature/your-feature-name main
```

<!-- langtabs-end -->

## Pull requests

Once you have made your changes and are ready to contribute, follow the steps to
submit a pull request:

1. Push your changes back.

<!-- langtabs-start -->

```bash
git push origin feature/your-feature-name
```

<!-- langtabs-end -->

2. Create a pull request to merge your branch into the main branch. Provide a clear
   description of your changes in the pull request message.

### Guidelines

- Write clear and concise commit messages.
- Test your changes thoroughly before submitting a pull request
- If the pull request adds functionality, the documentation should also be updated.

> [!IMPORTANT]
> Contributed code will be licensed under the same [license](LICENSE) as the rest of
> the repository. If you did not write the code yourself, you must ensure the existing
> license is compatible and include the license information in the contributed files,
> or obtain permission from the original author to relicense the contributed code.

It is okay to submit work-in-progress and seek feedback - you will likely be asked to
make additional changes or asked clarification questions.

### Review process

All pull requests will undergo a review process before being accepted. Reviewers may
provide feedback or request changes to ensure the quality of the codebase.
