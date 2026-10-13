from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.main import create_app


def make_client() -> TestClient:
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return TestClient(create_app(test_engine))


def test_customer_crud_flow() -> None:
    with make_client() as client:
        customer = {
            "customer_number": "C-100",
            "customer_name": "Northwind",
            "customer_type": "Business",
            "customer_category": "Wholesale",
        }

        created = client.post("/api/customers", json=customer)
        assert created.status_code == 201
        assert created.json() == customer

        assert client.get("/api/customers").json() == [customer]
        assert client.get("/api/customers/C-100").json() == customer

        updated_fields = {
            "customer_name": "Northwind Updated",
            "customer_type": "Partner",
            "customer_category": "Retail",
        }
        updated = client.put("/api/customers/C-100", json=updated_fields)
        assert updated.status_code == 200
        assert updated.json() == {
            "customer_number": "C-100",
            **updated_fields,
        }

        assert client.delete("/api/customers/C-100").status_code == 204
        assert client.get("/api/customers/C-100").status_code == 404


def test_duplicate_customer_number_returns_conflict() -> None:
    with make_client() as client:
        customer = {
            "customer_number": "C-100",
            "customer_name": "Northwind",
            "customer_type": "Business",
            "customer_category": "Wholesale",
        }
        assert client.post("/api/customers", json=customer).status_code == 201
        duplicate = client.post("/api/customers", json=customer)
        assert duplicate.status_code == 409


def test_invalid_customer_is_rejected() -> None:
    with make_client() as client:
        response = client.post(
            "/api/customers",
            json={
                "customer_number": "",
                "customer_name": "Northwind",
                "customer_type": "Business",
                "customer_category": "Wholesale",
            },
        )
        assert response.status_code == 422


def test_customer_list_page_is_served() -> None:
    with make_client() as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert "Customer feed" in response.text
        assert '<tr class="grid-actions">' in response.text
        assert '<a class="button-link" href="/export">Download customer data CSV</a>' in response.text


def test_static_assets_are_served_for_both_pages() -> None:
    with make_client() as client:
        customer_page = client.get("/")
        import_page = client.get("/import")

        assert "/static/css/site.css" in customer_page.text
        assert "/static/css/customers.css" in customer_page.text
        assert "/static/js/customers.js" in customer_page.text
        assert "/static/css/site.css" in import_page.text
        assert "/static/css/import.css" in import_page.text
        assert "/static/js/import.js" in import_page.text

        for asset in (
            "/static/css/site.css",
            "/static/css/customers.css",
            "/static/css/import.css",
            "/static/js/customers.js",
            "/static/js/import.js",
        ):
            response = client.get(asset)
            assert response.status_code == 200, asset
            assert response.content


def test_csv_import_creates_updates_and_deletes_rows_independently() -> None:
    with make_client() as client:
        client.post(
            "/api/customers",
            json={
                "customer_number": "C-200",
                "customer_name": "Old Name",
                "customer_type": "Business",
                "customer_category": "Retail",
            },
        )
        csv_data = (
            "Action,Customer Number,Customer Name,Customer Type,Customer Category\n"
            "Create,C-201,New Customer,Business,Wholesale\n"
            "Create,C-201,Duplicate,Business,Retail\n"
            "Update,C-200,Updated Name,Partner,Wholesale\n"
            "Delete,C-999,,,\n"
            "Delete,C-200,,,\n"
        )
        response = client.post(
            "/api/customers/import",
            files={"file": ("customers.csv", csv_data, "text/csv")},
        )

        assert response.status_code == 200
        result = response.json()
        assert result["total_rows"] == 5
        assert result["succeeded"] == 3
        assert result["failed"] == 2
        assert [row["status"] for row in result["results"]] == [
            "success",
            "error",
            "success",
            "error",
            "success",
        ]
        assert client.get("/api/customers/C-201").json()["customer_name"] == "New Customer"
        assert client.get("/api/customers/C-200").status_code == 404


def test_csv_import_rejects_unexpected_headers() -> None:
    with make_client() as client:
        response = client.post(
            "/api/customers/import",
            files={
                "file": (
                    "customers.csv",
                    "Customer Number,Customer Name\nC-300,Name\n",
                    "text/csv",
                )
            },
        )
        assert response.status_code == 400


def test_customer_csv_export_can_be_imported_into_an_empty_database() -> None:
    customer = {
        "customer_number": "C-400",
        "customer_name": 'Northwind, "West"',
        "customer_type": "Business",
        "customer_category": "Wholesale",
    }
    with make_client() as source_client:
        assert source_client.post("/api/customers", json=customer).status_code == 201
        exported = source_client.get("/export")
        legacy_export = source_client.get("/api/customers/export")

    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    assert exported.headers["content-disposition"] == 'attachment; filename="customers.csv"'
    assert legacy_export.content == exported.content

    with make_client() as destination_client:
        imported = destination_client.post(
            "/api/customers/import",
            files={"file": ("customers.csv", exported.content, "text/csv")},
        )
        assert imported.status_code == 200
        assert imported.json()["succeeded"] == 1
        assert imported.json()["failed"] == 0
        assert destination_client.get("/api/customers").json() == [customer]


def test_csv_import_page_is_served() -> None:
    with make_client() as client:
        response = client.get("/import")
        assert response.status_code == 200
        assert "Import customers" in response.text
