import logging
from pathlib import Path

import polars as pl
import pytest

from nhp_dwiproc.app import io
from nhp_dwiproc.app.analysis_levels import index
from nhp_dwiproc.config import GlobalOptsConfig, QueryConfig
from nhp_dwiproc.config.connectivity import ConnectomeConfig, TractMapConfig
from nhp_dwiproc.config.preprocess import UndistortionConfig


class TestLoadTable:
    """Tests associated with loading participant table."""

    def test_load_no_index(self, ds_dir: Path, caplog: pytest.LogCaptureFixture):
        if (index_path := (ds_dir / ".index.parquet")).exists():
            index_path.unlink()

        logger = logging.getLogger(__name__)
        with caplog.at_level(logging.INFO):
            table = io.load_participant_table(
                input_dir=ds_dir, cfg=GlobalOptsConfig(), logger=logger
            )
        assert isinstance(table, pl.DataFrame)
        assert "Indexing dataset temporarily" in caplog.text

    def test_load_index_exists(
        self,
        ds_dir: Path,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ):
        # Generate index
        index_fpath = ds_dir / ".index.parquet"
        if index_fpath.exists():
            index_fpath.unlink()
        index(input_dir=ds_dir, global_opts=GlobalOptsConfig(work_dir=tmp_path))

        logger = logging.getLogger(__name__)
        with caplog.at_level(logging.INFO):
            table = io.load_participant_table(
                input_dir=ds_dir,
                cfg=GlobalOptsConfig(index_path=index_fpath),
                logger=logger,
            )
        assert isinstance(table, pl.DataFrame)
        assert "index found" in caplog.text
        index_fpath.unlink()


class TestValidGroupBy:
    """Tests associated with testing grouping of keys."""

    def test_all_valid_keys(self):
        df = pl.DataFrame(
            {
                "sub": ["sub-01", "sub-02", "sub-03"],
                "ses": ["ses-01", "ses-01", "ses-02"],
                "task": ["rest", "rest", "memory"],
            }
        )
        keys = ["sub", "ses", "task"]
        result = io.valid_groupby(df, keys)
        assert result == ["sub", "ses", "task"]

    def test_missing_columns(self):
        df = pl.DataFrame({"sub": ["sub-01", "sub-02"], "ses": ["ses-01", "ses-02"]})
        keys = ["sub", "ses", "run", "task"]
        result = io.valid_groupby(df, keys)
        assert result == keys[:2]

    def test_columns_with_all_nulls(self):
        df = pl.DataFrame(
            {
                "sub": ["sub-01", "sub-02", "sub-03"],
                "ses": [None, None, None],
                "task": ["rest", "memory", "rest"],
            }
        )
        keys = ["sub", "ses", "task"]
        result = io.valid_groupby(df, keys)
        assert result == ["sub", "task"]

    def test_columns_with_partial_nulls(self):
        df = pl.DataFrame(
            {
                "sub": ["sub-01", "sub-02", "sub-03"],
                "ses": ["ses-01", None, "ses-02"],
                "task": ["rest", "memory", "rest"],
            }
        )
        keys = ["sub", "ses", "task"]
        result = io.valid_groupby(df, keys)
        assert result == ["sub", "ses", "task"]

    def test_empty_keys_list(self):
        df = pl.DataFrame({"sub": ["sub-01", "sub-02"], "ses": ["ses-01", "ses-02"]})
        keys = []
        result = io.valid_groupby(df, keys)
        assert result == []

    def test_empty_dataframe(self):
        df = pl.DataFrame({"sub": [], "ses": []})
        keys = ["sub", "ses"]
        result = io.valid_groupby(df, keys)
        assert result == []

    def test_preserves_key_order(self):
        df = pl.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]})
        keys = ["c", "a", "b"]
        result = io.valid_groupby(df, keys)
        assert result == ["c", "a", "b"]

    def test_mixed_valid_invalid_nulls(self):
        df = pl.DataFrame(
            {
                "sub": ["sub-01", "sub-02", "sub-03"],
                "ses": ["ses-01", None, "ses-02"],
                "run": [None, None, None],
                "task": ["rest", "memory", "rest"],
            }
        )
        keys = ["sub", "ses", "run", "task", "acquisition"]
        result = io.valid_groupby(df, keys)
        assert result == ["sub", "ses", "task"]


class TestQuery:
    """Tests for query function."""

    def test_single_equality_condition(self):
        df = pl.DataFrame(
            {
                "subject": ["sub-01", "sub-02", "sub-03"],
                "task": ["rest", "memory", "rest"],
            }
        )
        result = io.query(df, "task == 'rest'")
        assert result.height == 2
        assert result["subject"].to_list() == ["sub-01", "sub-03"]

    def test_and_operator(self):
        df = pl.DataFrame(
            {
                "subject": ["sub-01", "sub-02", "sub-03"],
                "session": ["ses-01", "ses-01", "ses-02"],
                "task": ["rest", "memory", "rest"],
            }
        )
        result = io.query(df, "session == 'ses-01' & task == 'rest'")
        assert result.height == 1
        assert result["subject"].to_list() == ["sub-01"]

    def test_or_operator(self):
        df = pl.DataFrame(
            {
                "subject": ["sub-01", "sub-02", "sub-03"],
                "task": ["rest", "memory", "nback"],
            }
        )
        result = io.query(df, "task == 'rest' | task == 'memory'")
        assert result.height == 2
        assert result["subject"].to_list() == ["sub-01", "sub-02"]

    def test_combined_and_or_operators(self):
        df = pl.DataFrame(
            {
                "subject": ["sub-01", "sub-02", "sub-03", "sub-04"],
                "session": ["ses-01", "ses-01", "ses-02", "ses-02"],
                "task": ["rest", "memory", "rest", "memory"],
            }
        )
        result = io.query(
            df,
            "(session == 'ses-01' & task == 'rest') | "
            "(session == 'ses-02' & task == 'memory')",
        )
        assert result.height == 2
        assert result["subject"].to_list() == ["sub-01", "sub-04"]

    def test_numeric_comparison(self):
        df = pl.DataFrame({"subject": ["sub-01", "sub-02", "sub-03"], "run": [1, 2, 3]})
        result = io.query(df, "run > 1")
        assert result.height == 2
        assert result["run"].to_list() == [2, 3]

    def test_numeric_equality(self):
        df = pl.DataFrame({"subject": ["sub-01", "sub-02", "sub-03"], "run": [1, 2, 1]})
        result = io.query(df, "run == 1")
        assert result.height == 2
        assert result["subject"].to_list() == ["sub-01", "sub-03"]

    def test_empty_result(self):
        df = pl.DataFrame({"subject": ["sub-01", "sub-02"], "task": ["rest", "memory"]})
        result = io.query(df, "task == 'nback'")
        assert result.height == 0
        assert result.columns == ["subject", "task"]

    def test_all_rows_match(self):
        df = pl.DataFrame(
            {
                "subject": ["sub-01", "sub-02", "sub-03"],
                "session": ["ses-01", "ses-01", "ses-01"],
            }
        )
        result = io.query(df, "session == 'ses-01'")
        assert result.height == 3
        assert result.equals(df)

    def test_multiple_equality_conversions(self):
        df = pl.DataFrame({"a": [1, 2, 3], "b": [1, 2, 3], "c": [1, 2, 3]})
        result = io.query(df, "a == 1 & b == 1 & c == 1")
        assert result.height == 1
        assert result["a"].to_list() == [1]

    def test_not_equal_operator(self):
        df = pl.DataFrame(
            {
                "subject": ["sub-01", "sub-02", "sub-03"],
                "task": ["rest", "memory", "rest"],
            }
        )
        result = io.query(df, "task != 'rest'")
        assert result.height == 1
        assert result["subject"].to_list() == ["sub-02"]

    def test_less_than_or_equal(self):
        df = pl.DataFrame({"subject": ["sub-01", "sub-02", "sub-03"], "run": [1, 2, 3]})
        result = io.query(df, "run <= 2")
        assert result.height == 2
        assert result["run"].to_list() == [1, 2]

    def test_greater_than_or_equal(self):
        df = pl.DataFrame({"subject": ["sub-01", "sub-02", "sub-03"], "run": [1, 2, 3]})
        result = io.query(df, "run >= 2")
        assert result.height == 2
        assert result["run"].to_list() == [2, 3]

    def test_complex_nested_conditions(self):
        df = pl.DataFrame(
            {
                "subject": ["sub-01", "sub-02", "sub-03", "sub-04", "sub-05"],
                "session": ["ses-01", "ses-01", "ses-02", "ses-02", "ses-03"],
                "task": ["rest", "memory", "rest", "memory", "rest"],
                "run": [1, 1, 2, 2, 3],
            }
        )
        result = io.query(
            df,
            "(session == 'ses-01' | session == 'ses-02') & task == 'rest' & run <= 2",
        )
        assert result.height == 2
        assert result["subject"].to_list() == ["sub-01", "sub-03"]

    def test_string_with_special_chars(self):
        df = pl.DataFrame(
            {
                "subject": ["sub-01", "sub-02"],
                "file": ["task-rest_bold.nii.gz", "task-memory_bold.nii.gz"],
            }
        )
        result = io.query(df, "file == 'task-rest_bold.nii.gz'")
        assert result.height == 1
        assert result["subject"].to_list() == ["sub-01"]

    def test_preserves_all_columns(self):
        df = pl.DataFrame(
            {
                "subject": ["sub-01", "sub-02"],
                "session": ["ses-01", "ses-02"],
                "task": ["rest", "memory"],
                "run": [1, 2],
            }
        )
        result = io.query(df, "task == 'rest'")
        assert result.columns == ["subject", "session", "task", "run"]


class TestGetInputs:
    """Tests for grabbing inputs function."""

    @pytest.fixture
    def table(self, ds_dir: Path) -> pl.DataFrame:
        return io.load_participant_table(
            input_dir=ds_dir,
            cfg=GlobalOptsConfig(threads=1, index_path=ds_dir / ".index.parquet"),
        )

    def test_no_stage_opts(self, table: pl.DataFrame):
        result = io.get_inputs(
            df=table,
            row={"sub": "01", "ses": "01"},
            query_opts=QueryConfig(),
            stage_opts=None,
            stage="analysis",
        )
        assert isinstance(result, dict)
        # DWI
        for key in ["nii", "bval", "bvec", "mask"]:
            assert (val := result.get("dwi", {}).get(key)) is not None and Path(
                val
            ).exists()
        assert (val := result.get("dwi", {}).get("json")) is not None and isinstance(
            val, dict
        )
        # T1w
        assert (val := result.get("t1w", {}).get("nii")) is not None and Path(
            val
        ).exists()

    def test_mask_query(self, table: pl.DataFrame):
        result = io.get_inputs(
            df=table,
            row={"sub": "01", "ses": "01"},
            query_opts=QueryConfig(mask="space=='T1w'"),
            stage_opts=None,
            stage="analysis",
        )
        assert result.get("dwi", {}).get("mask") is None

    def test_preprocess_invalid_stage_opts(self, table: pl.DataFrame):
        with pytest.raises(TypeError, match="Expected UndistortionConfig"):
            io.get_inputs(
                df=table,
                row={"sub": "01", "ses": "01"},
                query_opts=QueryConfig(),
                stage_opts=None,
                stage="preprocess",
            )

    def test_preprocess_mask_stage(self, table: pl.DataFrame):
        result = io.get_inputs(
            df=table,
            row={"sub": "01", "ses": "01"},
            query_opts=QueryConfig(mask="desc=='T1w' & suffix=='mask'"),
            stage_opts=UndistortionConfig(),
            stage="preprocess",
        )
        assert (val := result.get("dwi", {}).get("mask")) is not None and Path(
            val
        ).exists()

    def test_preprocess_fieldmap_opt_stage(self, table: pl.DataFrame):
        result = io.get_inputs(
            df=table,
            row={"sub": "01", "ses": "01"},
            query_opts=QueryConfig(),
            stage_opts=UndistortionConfig(method="fieldmap"),
            stage="preprocess",
        )
        for key in ["nii", "bval", "bvec"]:
            assert (val := result.get("fmap", {}).get(key)) is not None and Path(
                val
            ).exists()
        assert (val := result.get("fmap", {}).get("json")) is not None and val == {}

    def test_preprocess_fugue_opt_stage(self, table: pl.DataFrame):
        result = io.get_inputs(
            df=table,
            row={"sub": "01", "ses": "01"},
            query_opts=QueryConfig(),
            stage_opts=UndistortionConfig(method="fugue"),
            stage="preprocess",
        )
        assert (val := result.get("fmap", {}).get("nii")) is not None and Path(
            val
        ).exists()
        assert (val := result.get("fmap", {}).get("json")) is not None and val == {}
        assert all(result.get("fmap", {}).get(key) is None for key in ["bval", "bvec"])

    def test_reconstruction_stage(self, table: pl.DataFrame):
        result = io.get_inputs(
            df=table,
            row={"sub": "01", "ses": "01"},
            query_opts=QueryConfig(),
            stage_opts=None,
            stage="reconstruction",
        )
        assert (val := result.get("dwi", {}).get("5tt")) is not None and Path(
            val
        ).exists()

    def test_connectivity_stage_invalid_config(self, table: pl.DataFrame):
        with pytest.raises(
            TypeError, match="Expected ConnectomeConfig or TractMapConfig"
        ):
            io.get_inputs(
                df=table,
                row={"sub": "01", "ses": None},
                query_opts=QueryConfig(),
                stage_opts=QueryConfig(),  # type: ignore[arg-type]
                stage="connectivity",
            )

    def test_connectivity_stage_connectome_config(self, table: pl.DataFrame):
        result = io.get_inputs(
            df=table,
            row={"sub": "01", "ses": "01"},
            query_opts=QueryConfig(),
            stage_opts=ConnectomeConfig(atlas="test"),
            stage="connectivity",
        )
        # Atlas
        assert (val := result.get("dwi", {}).get("atlas")) is not None and Path(
            val
        ).exists()
        # Tractography
        assert result.get("dwi", {}).get("tractography") is not None
        for key in ["tck_fpath", "tck_weights_fpath"]:
            assert (val := result["dwi"]["tractography"][key]) is not None and Path(
                val
            ).exists()

    def test_connectivity_stage_no_opts(self, table: pl.DataFrame):
        result = io.get_inputs(
            df=table,
            row={"sub": "01", "ses": "01"},
            query_opts=QueryConfig(),
            stage_opts=ConnectomeConfig(),
            stage="connectivity",
        )
        assert result.get("dwi", {}).get("atlas") is None
        assert result.get("dwi", {}).get("tractography") is not None
        for key in ["tck_fpath", "tck_weights_fpath"]:
            assert (val := result["dwi"]["tractography"][key]) is not None and Path(
                val
            ).exists()

    def test_connectivity_stage_tractmap_config(self, table: pl.DataFrame):
        result = io.get_inputs(
            df=table,
            row={"sub": "01", "ses": "01"},
            query_opts=QueryConfig(),
            stage_opts=TractMapConfig(
                tract_query="label=='ILF'",
                surface_query="hemi=='L'",
            ),
            stage="connectivity",
        )
        assert all(
            result.get("anat", {}).get(key) is not None for key in ["rois", "surfs"]
        )
        # ROI
        for roi_type in ["inclusion_fpaths", "exclusion_fpaths", "truncate_fpaths"]:
            roi_paths = result["anat"]["rois"][roi_type]
            assert roi_paths is not None
            assert len(roi_paths) > 0
            assert all(Path(p).exists() for p in roi_paths)
        # Surface
        for surf_type in ["pial", "white", "inflated"]:
            surf_paths = result["anat"]["surfs"][surf_type]
            if surf_paths is not None:
                assert all(Path(p).exists() for p in surf_paths)
