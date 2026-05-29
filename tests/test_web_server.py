from __future__ import annotations

from aiohttp import web

from src.web.server import AtlasServer


def test_app_creation(sample_config: dict):
    server = AtlasServer(sample_config)

    assert isinstance(server.app, web.Application)
    assert server.status == "idle"


def test_route_registration(sample_config: dict):
    server = AtlasServer(sample_config)
    routes = {(route.method, route.resource.canonical) for route in server.app.router.routes()}

    assert ("GET", "/") in routes
    assert ("GET", "/api/atlas") in routes
    assert ("GET", "/api/atlas.json") in routes
    assert ("GET", "/ws") in routes


def test_static_file_serving_setup(sample_config: dict):
    server = AtlasServer(sample_config)
    resources = list(server.app.router.resources())

    assert any(resource.name == "static" for resource in resources)
