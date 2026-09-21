"""Products are returned newest-first for client-side pagination."""


def test_products_are_sorted_newest_first(client):
    created_ids = []
    codes = ["TSCHK-SORT-01", "TSCHK-SORT-02", "TSCHK-SORT-03"]
    try:
        for index, code in enumerate(codes, start=1):
            response = client.post(
                "/products",
                json={"name": f"sort-product-{index}", "code": code, "stock": 1, "unit_price": index},
            )
            if response.status_code == 409:
                existing = next(product for product in client.get("/products").json() if product["code"] == code)
                client.delete(f"/products/{existing['id']}")
                response = client.post(
                    "/products",
                    json={"name": f"sort-product-{index}", "code": code, "stock": 1, "unit_price": index},
                )
            assert response.status_code == 201, response.text
            created_ids.append(response.json()["id"])

        products = client.get("/products").json()
        positions = [next(index for index, product in enumerate(products) if product["id"] == product_id) for product_id in created_ids]
        assert positions == sorted(positions, reverse=True)
    finally:
        for product_id in created_ids:
            client.delete(f"/products/{product_id}")
