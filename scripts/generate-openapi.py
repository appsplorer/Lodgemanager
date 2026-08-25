#!/usr/bin/env python3
"""Generate the OpenAPI surface directly from Django URL and method declarations."""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
MUTATING = {"post", "put", "patch", "delete"}
ANONYMOUS_EXACT = {
    "/api/health/", "/api/ready/", "/api/csrf/", "/api/auth/login",
    "/api/auth/invitation", "/api/auth/password-reset/request",
    "/api/auth/password-reset/confirm",
}
NON_TENANT_PREFIXES = (
    "/api/auth/", "/api/mfa/", "/api/me", "/api/workspace/", "/api/csrf/",
    "/api/health/", "/api/ready/", "/api/public/", "/api/webhooks/",
    "/api/platform/", "/api/experiments/",
)
CONVERTER_SCHEMA = {
    "uuid": {"type": "string", "format": "uuid"},
    "int": {"type": "integer"},
    "slug": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
    "str": {"type": "string"},
}


def view_methods() -> dict[str, list[str]]:
    tree = ast.parse((ROOT / "backend/platform_core/views.py").read_text(encoding="utf-8"))
    result: dict[str, list[str]] = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        selected = ["get"]
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and getattr(decorator.func, "id", "") == "require_http_methods":
                selected = [str(value).lower() for value in ast.literal_eval(decorator.args[0])]
        result[node.name] = selected
    return result


def routes() -> list[tuple[str, str, dict[str, str]]]:
    source = (ROOT / "backend/lodgeflow/urls.py").read_text(encoding="utf-8")
    result = []
    for raw_path, view in re.findall(r"path\('([^']+)'\s*,\s*v\.([A-Za-z_][A-Za-z0-9_]*)", source):
        if not raw_path.startswith("api/"):
            continue
        converters: dict[str, str] = {}

        def replace(match: re.Match[str]) -> str:
            converter = match.group(1) or "str"
            name = match.group(2)
            converters[name] = converter
            return "{" + name + "}"

        normalized = "/" + re.sub(r"<(?:(\w+):)?([A-Za-z_][A-Za-z0-9_]*)>", replace, raw_path)
        result.append((normalized, view, converters))
    return result


def anonymous(path: str) -> bool:
    return path in ANONYMOUS_EXACT or path.startswith(("/api/public/", "/api/webhooks/", "/api/experiments/"))


def tenant_scoped(path: str) -> bool:
    return not path.startswith(NON_TENANT_PREFIXES)


def success_responses(method: str, path: str) -> dict[str, object]:
    codes = {"get": ("200",), "post": ("200", "201", "202"), "put": ("200",), "patch": ("200",), "delete": ("200", "204")}[method]
    binary = any(token in path for token in ("/download", ".pdf", "/receipt", "/generate/", "/exports/"))
    responses: dict[str, object] = {}
    for code in codes:
        row: dict[str, object] = {"description": "Successful response" if code != "204" else "Successful response with no body"}
        if code != "204":
            row["content"] = {"application/octet-stream" if binary else "application/json": {"schema": {"type": "string", "format": "binary"} if binary else {"type": "object", "additionalProperties": True}}}
        responses[code] = row
    return responses


def operation(path: str, view: str, converters: dict[str, str], method: str) -> dict[str, object]:
    path_hash = hashlib.sha256(path.encode()).hexdigest()[:8]
    parameters = [
        {"name": name, "in": "path", "required": True, "schema": CONVERTER_SCHEMA.get(converter, {"type": "string"})}
        for name, converter in converters.items()
    ]
    if tenant_scoped(path):
        parameters.append({"$ref": "#/components/parameters/LodgeHeader"})
    if method in MUTATING and not anonymous(path):
        parameters.append({"$ref": "#/components/parameters/CsrfHeader"})
    responses = success_responses(method, path)
    for code, name in (("400", "BadRequest"), ("401", "Unauthorized"), ("403", "Forbidden"), ("404", "NotFound"), ("409", "Conflict"), ("429", "RateLimited")):
        responses[code] = {"$ref": f"#/components/responses/{name}"}
    if method in MUTATING:
        for code, name in (("413", "PayloadTooLarge"), ("415", "UnsupportedMediaType"), ("422", "UnprocessableEntity")):
            responses[code] = {"$ref": f"#/components/responses/{name}"}
    result: dict[str, object] = {
        "operationId": f"{view}_{method}_{path_hash}",
        "summary": f"{method.upper()} {path}",
        "description": f"Runtime contract for `platform_core.views.{view}`.",
        "tags": ["Platform" if path.startswith("/api/platform/") else "Public" if anonymous(path) else path.split("/")[2].replace("-", " ").title()],
        "parameters": parameters,
        "responses": responses,
        "x-runtime-view": view,
    }
    if anonymous(path):
        result["security"] = []
    if method in {"post", "put", "patch"}:
        schema = {"type": "object", "additionalProperties": True}
        result["requestBody"] = {"required": False, "content": {"application/json": {"schema": schema}, "multipart/form-data": {"schema": schema}}}
    return result


def document() -> dict[str, object]:
    methods = view_methods()
    paths: dict[str, object] = {}
    for path, view, converters in routes():
        paths[path] = {method: operation(path, view, converters, method) for method in methods[view]}
    error_schema = {"type": "object", "additionalProperties": True, "required": ["error"], "properties": {"error": {"type": "string"}, "detail": {}, "fields": {"type": "object", "additionalProperties": True}, "reauthenticate": {"type": "boolean"}}}
    response = lambda description: {"description": description, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}}
    return {
        "openapi": "3.1.0",
        "info": {"title": "LodgeFlow API", "version": "1.0.0", "description": "Generated from the deployed Django URL/method surface. Session authentication, CSRF and server-validated X-Lodge-ID tenant selection apply as documented per operation."},
        "servers": [{"url": "https://{host}", "variables": {"host": {"default": "lodge.example.org"}}}],
        "paths": dict(sorted(paths.items())),
        "components": {
            "securitySchemes": {"sessionCookie": {"type": "apiKey", "in": "cookie", "name": "sessionid"}},
            "parameters": {
                "LodgeHeader": {"name": "X-Lodge-ID", "in": "header", "required": True, "description": "Tenant UUID selected from the authenticated user’s active memberships; never trusted without membership validation.", "schema": {"type": "string", "format": "uuid"}},
                "CsrfHeader": {"name": "X-CSRFToken", "in": "header", "required": True, "description": "Django CSRF token required for authenticated unsafe methods.", "schema": {"type": "string"}},
            },
            "schemas": {"Error": error_schema},
            "responses": {
                "BadRequest": response("Validation, parsing or workflow error"),
                "Unauthorized": response("Authentication is required or no longer valid"),
                "Forbidden": response("Identity lacks tenant/platform permission or CSRF/step-up evidence"),
                "NotFound": response("Object not found or deliberately hidden to prevent existence disclosure"),
                "Conflict": response("State, idempotency, duplicate or lifecycle conflict"),
                "RateLimited": response("Request rate exceeded the bounded policy"),
                "PayloadTooLarge": response("Payload exceeds the configured safe size"),
                "UnsupportedMediaType": response("MIME type, signature or extension is unsupported"),
                "UnprocessableEntity": response("Payload is structurally valid but rejected by a security/workflow rule"),
            },
        },
        "security": [{"sessionCookie": []}],
    }


def main() -> int:
    output = ROOT / "docs/openapi.yaml"
    output.write_text(yaml.safe_dump(document(), sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")
    print(f"Wrote {output} with {len(document()['paths'])} runtime paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
