"""Shared InterSystems IRIS connection configuration."""

import os

import iris


def get_connection():
    """Return an IRIS DB-API connection configured from the environment."""
    host = os.getenv("IRIS_HOST", "localhost")
    port = os.getenv("IRIS_PORT", "1972")
    namespace = os.getenv("IRIS_NAMESPACE", "MAINTENANCE")
    username = os.getenv("IRIS_USERNAME", "_SYSTEM")
    password = os.getenv("IRIS_PASSWORD")

    if not password:
        raise RuntimeError("IRIS_PASSWORD environment variable is required")

    try:
        port_number = int(port)
    except ValueError as error:
        raise RuntimeError("IRIS_PORT must be an integer") from error

    connection_string = f"{host}:{port_number}/{namespace}"
    return iris.connect(connection_string, username, password)
