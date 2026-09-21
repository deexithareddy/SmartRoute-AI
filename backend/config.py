"""
SmartRoute AI - Centralized Security & Environment Configuration

Manages environment variables, CORS origins, payload size limits,
security flags, and debug settings safely.
"""

import os
from typing import List
from dotenv import load_dotenv

# Load backend/.env first, then root .env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
load_dotenv()

# Read environment variables with secure defaults
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()
DEBUG = os.getenv("DEBUG", "false").strip().lower() in ("true", "1", "yes")

# CORS Origin Configuration
raw_cors = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
)
CORS_ORIGINS: List[str] = [origin.strip() for origin in raw_cors.split(",") if origin.strip()]

# If in development mode and CORS is wildcard or empty, allow development origins
if ENVIRONMENT == "development" and "*" in CORS_ORIGINS:
    CORS_ORIGINS = ["*"]

# Maximum allowed request body size in bytes (Default: 1MB = 1048576 bytes)
MAX_REQUEST_SIZE_BYTES = int(os.getenv("MAX_REQUEST_SIZE_BYTES", "1048576"))

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./smartroute.db")

# External Service Endpoints
OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "http://router.project-osrm.org")
NOMINATIM_BASE_URL = os.getenv("NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org")

# Geoapify Routing & Geocoding Configuration
_raw_geoapify_key = os.getenv("GEOAPIFY_API_KEY", "").strip()
if (_raw_geoapify_key.startswith('"') and _raw_geoapify_key.endswith('"')) or (
    _raw_geoapify_key.startswith("'") and _raw_geoapify_key.endswith("'")
):
    GEOAPIFY_API_KEY = _raw_geoapify_key[1:-1].strip()
else:
    GEOAPIFY_API_KEY = _raw_geoapify_key

GEOAPIFY_ROUTING_URL = os.getenv("GEOAPIFY_ROUTING_URL", "https://api.geoapify.com/v1/routing")
GEOAPIFY_GEOCODING_URL = os.getenv("GEOAPIFY_GEOCODING_URL", "https://api.geoapify.com/v1/geocode/search")

# HERE Routing API v8 Configuration
_raw_here_key = os.getenv("HERE_API_KEY", "").strip()
if (_raw_here_key.startswith('"') and _raw_here_key.endswith('"')) or (
    _raw_here_key.startswith("'") and _raw_here_key.endswith("'")
):
    HERE_API_KEY: str = _raw_here_key[1:-1].strip()
else:
    HERE_API_KEY = _raw_here_key

HERE_ROUTING_URL = os.getenv("HERE_ROUTING_URL", "https://router.hereapi.com/v8/routes")

# Fault Injection Control: Enabled ONLY in development mode or explicit flag
ALLOW_DEV_FAULT_INJECTION = os.getenv(
    "ALLOW_DEV_FAULT_INJECTION",
    "true" if ENVIRONMENT == "development" else "false",
).strip().lower() in ("true", "1", "yes")


class SecurityConfig:
    """Security helper properties for runtime verification."""

    @classmethod
    def is_production(cls) -> bool:
        return ENVIRONMENT == "production"

    @classmethod
    def is_development(cls) -> bool:
        return ENVIRONMENT == "development"

    @classmethod
    def is_fault_injection_allowed(cls) -> bool:
        """Fault injection is strictly prohibited in production mode."""
        return cls.is_development() and ALLOW_DEV_FAULT_INJECTION
