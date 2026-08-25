from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
HTTP_METHODS = {'get', 'post', 'put', 'patch', 'delete', 'head', 'options'}


def runtime_routes() -> dict[str, tuple[str, set[str]]]:
    url_source = (ROOT / 'backend/lodgeflow/urls.py').read_text(encoding='utf-8')
    view_tree = ast.parse((ROOT / 'backend/platform_core/views.py').read_text(encoding='utf-8'))
    methods: dict[str, set[str]] = {}
    for node in view_tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        selected = {'get'}
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and getattr(decorator.func, 'id', '') == 'require_http_methods':
                selected = {str(value).lower() for value in ast.literal_eval(decorator.args[0])}
        methods[node.name] = selected
    result: dict[str, tuple[str, set[str]]] = {}
    for raw_path, view in re.findall(r"path\('([^']+)'\s*,\s*v\.([A-Za-z_][A-Za-z0-9_]*)", url_source):
        if not raw_path.startswith('api/'):
            continue
        normalized = '/' + re.sub(r'<(?:[a-z]+:)?([A-Za-z_][A-Za-z0-9_]*)>', r'{\1}', raw_path)
        result[normalized] = (view, methods[view])
    return result


class OpenApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = yaml.safe_load((ROOT / 'docs/openapi.yaml').read_text(encoding='utf-8'))
        cls.paths = cls.document.get('paths') or {}

    def test_api_001_every_runtime_route_and_method_is_documented(self):
        runtime = runtime_routes()
        self.assertEqual(set(runtime), set(self.paths), f'missing={sorted(set(runtime)-set(self.paths))}; stale={sorted(set(self.paths)-set(runtime))}')
        for path, (_view, expected_methods) in runtime.items():
            actual_methods = set(self.paths[path]) & HTTP_METHODS
            self.assertEqual(actual_methods, expected_methods, path)

    def test_api_001_uses_openapi_placeholders_with_declared_parameters(self):
        for path, item in self.paths.items():
            self.assertNotRegex(path, r'<[^>]+>')
            expected = set(re.findall(r'{([^}]+)}', path))
            for method, operation in item.items():
                if method not in HTTP_METHODS:
                    continue
                declared = {row.get('name') for row in operation.get('parameters', []) if isinstance(row, dict) and row.get('in') == 'path'}
                self.assertEqual(expected, declared, f'{method.upper()} {path}')

    def test_api_001_operations_have_unique_ids_and_shared_error_contracts(self):
        operation_ids = []
        for path, item in self.paths.items():
            for method, operation in item.items():
                if method not in HTTP_METHODS:
                    continue
                operation_ids.append(operation.get('operationId'))
                responses = operation.get('responses') or {}
                self.assertTrue(any(str(code).startswith('2') for code in responses), f'{method.upper()} {path}')
                for code in ('400', '401', '403', '404', '409', '429'):
                    self.assertIn(code, responses, f'{method.upper()} {path}')
                    self.assertIn('$ref', responses[code], f'{method.upper()} {path} {code}')
        self.assertNotIn(None, operation_ids)
        self.assertEqual(len(operation_ids), len(set(operation_ids)))
        components = self.document.get('components') or {}
        self.assertIn('sessionCookie', components.get('securitySchemes', {}))
        self.assertIn('Error', components.get('schemas', {}))


if __name__ == '__main__':
    unittest.main()
