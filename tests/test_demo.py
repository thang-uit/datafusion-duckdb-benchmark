"""Kiểm tra tích hợp bằng dữ liệu nhỏ, không sinh hoặc chạy lại TPC-H SF=10."""

# Gọi kiểm thử bằng unittest có sẵn, không thêm phụ thuộc test.
import unittest
# Tạo checkout giả và tệp tạm, tự dọn khi kết thúc.
import tempfile
# Đường dẫn tài nguyên của kho hiện tại.
from pathlib import Path
# Nạp script có dấu gạch nối trong tên bằng đường dẫn tệp.
import importlib.util
# Cho phép import tiện ích nằm cạnh notebook.
import sys
# Tạo giá trị tiền chính xác như cột decimal trong TPC-H.
from decimal import Decimal
# Ngày giao hàng phục vụ điều kiện Q6.
from datetime import date

# Dữ liệu Arrow nhỏ được cả hai bộ máy đọc cùng nhau.
import pyarrow as pa
# Lưu nguồn Parquet giống đường dữ liệu thật của demo.
import pyarrow.parquet as pq
# Phiên nhúng DataFusion với một phân vùng.
from datafusion import SessionContext, SessionConfig
# Kết nối DuckDB trong bộ nhớ, không đụng my-db.duckdb.
import duckdb

# Xác định kho từ chính tệp test, không phụ thuộc thư mục Terminal.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tpch"))
# Các tiện ích được test thông qua EXPLAIN và SELECT thật trên dữ liệu nhỏ.
from plan_comparison import compare_plans
from q6_walkthrough import profile_duckdb_q6, q6_diagnostics, q6_control_result

# Nạp đúng bộ chuẩn bị Docker được setup.sh gọi.
spec = importlib.util.spec_from_file_location("prepare_tpch", ROOT / "common/prepare-tpch-source.py")
prepare_tpch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare_tpch)


class DockerSourceTests(unittest.TestCase):
    """Bản vá không được mất chỉnh sửa khác hoặc ghi đè khi cấu trúc nguồn không đúng."""

    def test_patch_is_repeatable_and_preserves_other_edits(self):
        # Chỉ tạo checkout giả, không sửa checkout DataFusion đang dùng.
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder) / "benchmarks/bench.sh"
            script.parent.mkdir()
            script.write_text("# custom edit\n" + (prepare_tpch.OLD_IMAGE + "\n") * 2)
            # Lần đầu đổi đúng hai tham chiếu, lần sau phải giữ nguyên tệp.
            prepare_tpch.prepare(folder)
            updated = script.read_text()
            prepare_tpch.prepare(folder)
            self.assertEqual(script.read_text(), updated)
            self.assertTrue(updated.startswith("# custom edit\n"))
            self.assertEqual(updated.count(prepare_tpch.NEW_IMAGE), 2)

    def test_incompatible_source_is_not_written(self):
        # Tệp khác cấu trúc đã biết phải báo lỗi và giữ nguyên nội dung.
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder) / "benchmarks/bench.sh"
            script.parent.mkdir()
            script.write_text("unexpected source\n")
            with self.assertRaises(ValueError):
                prepare_tpch.prepare(folder)
            self.assertEqual(script.read_text(), "unexpected source\n")


class NotebookIntegrationTests(unittest.TestCase):
    """Kiểm tra cùng Q6 trên Arrow nhỏ, cấu hình và HTML đối chiếu thật."""

    def setUp(self):
        # Chỉ hai dòng đầu thỏa Q6. Dòng cuối có ngày ngoài 1994 nên bị loại.
        self.table = pa.table({
            "l_quantity": pa.array([10, 20, 30], type=pa.decimal128(15, 2)),
            "l_extendedprice": pa.array([Decimal("100"), Decimal("200"), Decimal("300")], type=pa.decimal128(15, 2)),
            "l_discount": pa.array([Decimal("0.06"), Decimal("0.05"), Decimal("0.06")], type=pa.decimal128(15, 2)),
            "l_shipdate": pa.array([date(1994, 2, 1), date(1994, 6, 1), date(1995, 1, 1)], type=pa.date32()),
        })
        # Dùng nguyên SQL Q6 của benchmark, không viết lại điều kiện để test.
        self.sql = (ROOT / "tpch/queries.sql").read_text().splitlines()[5]
        self.ctx = SessionContext(SessionConfig().with_target_partitions(1))
        # DuckDB 0.9.1 đọc cùng Parquet thay vì đi qua bộ quét Arrow khác benchmark.
        self.folder = tempfile.TemporaryDirectory()
        path = Path(self.folder.name) / "lineitem.parquet"
        pq.write_table(self.table, path)
        self.ctx.register_parquet("lineitem", str(path))
        self.con = duckdb.connect(":memory:")
        self.con.execute("SET threads=1")
        escaped = str(path).replace("'", "''")
        self.con.execute(f"CREATE VIEW lineitem AS SELECT * FROM read_parquet('{escaped}')")

    def tearDown(self):
        # Đóng kết nối cả khi một kiểm thử báo lỗi.
        self.con.close()
        self.folder.cleanup()

    def test_explain_comparison_restores_settings_and_order(self):
        # EXPLAIN all chỉ có hiệu lực tạm thời trong compare_plans.
        self.con.execute("SET explain_output='physical_only'")
        rendered = compare_plans(self.ctx, self.con, self.sql, "Q6").data
        setting = self.con.execute("SELECT current_setting('explain_output')").fetchone()[0]
        self.assertEqual(setting.lower(), "physical_only")
        self.assertLess(rendered.index("1. Kế hoạch logic ban đầu"), rendered.index("3. Kế hoạch vật lý cuối"))
        self.assertIn("data:image/png;base64,", rendered)

    def test_profile_and_manual_control_preserve_result(self):
        # Mỗi lời gọi profile thực thi đúng một SELECT và khôi phục profiling.
        df_value = self.ctx.sql(self.sql).collect()[0].column(0)[0].as_py()
        baseline = profile_duckdb_q6(self.con, self.sql)
        self.assertEqual(df_value, Decimal("16.00"))
        self.assertEqual(baseline["rows"][0][0], df_value)
        self.assertIsNone(self.con.execute("SELECT current_setting('enable_profiling')").fetchone()[0])
        # Tắt quy tắc chỉ đổi đường lọc, vẫn phải trả cùng kết quả.
        self.con.execute("SET disabled_optimizers='filter_pushdown'")
        trial = profile_duckdb_q6(self.con, self.sql)
        self.assertEqual(trial["rows"], baseline["rows"])
        self.assertEqual(trial["disabled_optimizers"], "filter_pushdown")
        self.assertIn("Q6 — kết quả đối chứng", q6_control_result(baseline, trial, df_value).data)
        # DataFusion ANALYZE là lượt riêng, truyền số liệu thật vào bảng chẩn đoán.
        rows = [row for batch in self.ctx.sql("EXPLAIN ANALYZE VERBOSE " + self.sql).collect() for row in batch.to_pylist()]
        self.assertIn("Q6 — phát hiện nơi tốn thời gian", q6_diagnostics(rows, baseline).data)

    def test_failed_query_restores_profiling(self):
        # Lỗi SELECT không được để kết nối ở chế độ profiling tạm.
        self.con.execute("SET explain_output='optimized_only'")
        with self.assertRaises(duckdb.Error):
            profile_duckdb_q6(self.con, "SELECT missing_column FROM lineitem")
        self.assertIsNone(self.con.execute("SELECT current_setting('enable_profiling')").fetchone()[0])
        self.assertEqual(self.con.execute("SELECT current_setting('explain_output')").fetchone()[0].lower(), "optimized_only")


if __name__ == "__main__":
    # Chạy riêng test này hoặc dùng unittest discover từ thư mục gốc.
    unittest.main()
