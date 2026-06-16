from scripts import introspect_congress_db


def test_introspection_defaults_to_public_schema(monkeypatch):
    calls = []

    monkeypatch.setattr(
        introspect_congress_db,
        "assert_read_only",
        lambda conn: {
            "current_user": "congress_ro",
            "session_user": "congress_ro",
            "transaction_read_only": "on",
            "server_in_recovery": False,
        },
    )

    def fake_fetch_all(conn, query, params=()):
        calls.append((query, params))
        return []

    monkeypatch.setattr(introspect_congress_db, "fetch_all", fake_fetch_all)

    data = introspect_congress_db.introspect(object())

    assert data["included_schemas"] == ["public"]
    assert len(calls) == 5
    assert all("public" in repr(params) for _, params in calls)
    assert all("neon_auth" not in repr(params) for _, params in calls)
    assert any("dst_ns.nspname = ANY(%s)" in query for query, _ in calls)


def test_introspection_can_explicitly_include_additional_schemas(monkeypatch):
    calls = []

    monkeypatch.setattr(
        introspect_congress_db,
        "assert_read_only",
        lambda conn: {
            "current_user": "congress_ro",
            "session_user": "congress_ro",
            "transaction_read_only": "on",
            "server_in_recovery": False,
        },
    )

    def fake_fetch_all(conn, query, params=()):
        calls.append((query, params))
        return []

    monkeypatch.setattr(introspect_congress_db, "fetch_all", fake_fetch_all)

    data = introspect_congress_db.introspect(
        object(),
        included_schemas=("public", "analytics"),
    )

    assert data["included_schemas"] == ["public", "analytics"]
    assert all("analytics" in repr(params) for _, params in calls)
