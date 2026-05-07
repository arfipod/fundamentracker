from config import get_cors_allowed_origins, parse_cors_allowed_origins


def test_parse_cors_allowed_origins_from_comma_separated_list():
    assert parse_cors_allowed_origins(
        "https://app.example.com, http://localhost:5173,https://admin.example.com "
    ) == [
        "https://app.example.com",
        "http://localhost:5173",
        "https://admin.example.com",
    ]


def test_parse_cors_allowed_origins_ignores_empty_entries():
    assert parse_cors_allowed_origins("https://app.example.com, ,") == [
        "https://app.example.com"
    ]


def test_development_environment_allows_vite_localhost_by_default():
    assert get_cors_allowed_origins(
        cors_allowed_origins="",
        app_environment="development",
    ) == ["http://localhost:5173"]


def test_production_environment_has_no_default_wildcard_or_localhost():
    assert get_cors_allowed_origins(
        cors_allowed_origins="",
        app_environment="production",
    ) == []


def test_wildcard_is_removed_unless_explicitly_allowed():
    assert get_cors_allowed_origins(
        cors_allowed_origins="https://app.example.com,*",
        allow_wildcard_cors="false",
        app_environment="production",
    ) == ["https://app.example.com"]


def test_wildcard_is_allowed_when_explicitly_enabled():
    assert get_cors_allowed_origins(
        cors_allowed_origins="https://app.example.com,*",
        allow_wildcard_cors="true",
        app_environment="production",
    ) == ["https://app.example.com", "*"]
