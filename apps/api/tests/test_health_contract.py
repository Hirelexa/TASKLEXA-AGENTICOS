import ast
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class HealthContractTests(unittest.TestCase):
    def test_health_routes_exist(self) -> None:
        main_file = ROOT / "src" / "tasklexa_api" / "main.py"
        tree = ast.parse(main_file.read_text())
        route_paths = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                for decorator in node.decorator_list:
                    if (
                        isinstance(decorator, ast.Call)
                        and isinstance(decorator.func, ast.Attribute)
                        and decorator.func.attr == "get"
                        and decorator.args
                        and isinstance(decorator.args[0], ast.Constant)
                    ):
                        route_paths.append(decorator.args[0].value)

        self.assertIn("/health", route_paths)
        self.assertIn("/health/integrations", route_paths)

    def test_integration_status_labels_are_visible_contract(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT / "src"))
        from tasklexa_api.schemas.health import IntegrationStatus

        labels = set(IntegrationStatus.__args__)
        self.assertTrue(labels)

        # Provider-specific status logic lives in health.py plus each
        # integrations/*/*.py adapter module (e.g. MOCK/UNVERIFIED for
        # Similarweb live only in integrations/similarweb/tool.py, not
        # health.py) - so every label must appear somewhere across all of
        # them, not necessarily in any single file.
        source_files = [ROOT / "src" / "tasklexa_api" / "health.py"]
        source_files.extend((ROOT / "src" / "tasklexa_api" / "integrations").rglob("*.py"))
        combined_source = "\n".join(path.read_text() for path in source_files)

        missing = [label for label in labels if label not in combined_source]
        self.assertEqual(missing, [], f"status labels never referenced in integration code: {missing}")


if __name__ == "__main__":
    unittest.main()

