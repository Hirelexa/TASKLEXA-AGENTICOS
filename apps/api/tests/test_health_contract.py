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
        health_file = ROOT / "src" / "tasklexa_api" / "health.py"
        source = health_file.read_text()

        for label in ("LIVE", "MOCK", "NOT_CONFIGURED", "FAILED"):
            self.assertIn(label, source)


if __name__ == "__main__":
    unittest.main()

