import pytest
from app import app
from models import get_portfolios_for_user

class TestConfirm:
    def test_redirects_to_portfolio_after_confirm(self, logged_in_client):
        response = logged_in_client.post("/create_portfolio", data={
            "portfolio-name": "portfolio1",
            "cash-amount": "100000",
        })
        assert response.status_code == 302
        assert "/portfolio" in response.location

class TestAddPortfolio:
    def test_duplicate_portfolio_name_shows_error(self, logged_in_client, test_user):
        logged_in_client.post("/create_portfolio", data={"portfolio-name": "Portfolio1", "cash-amount": "100000"})

        response = logged_in_client.post("/create_portfolio", data={"portfolio-name": "Portfolio1", "cash-amount": "50000"})

        assert response.status_code == 200
        assert b"Portfolio name already exists" in response.data

        portfolios = get_portfolios_for_user(test_user["id"])
        assert len([p for p in portfolios if p.name == "Portfolio1"]) == 1

class TestPageLoading:
    def test_home_page_loads(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert b"Welcome" in response.data

    def test_portfolio_page_loads(self, logged_in_client):
        response = logged_in_client.get("/portfolio/id")
        assert response.status_code == 200
        assert b"Portfolio" in response.data