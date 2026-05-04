from __future__ import annotations

from datetime import datetime

from .extensions import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(40), nullable=False)
    provider_sub = db.Column(db.String(255), nullable=False, unique=True, index=True)
    email = db.Column(db.String(255), nullable=True, index=True)
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    portfolios = db.relationship(
        "Portfolio",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    cash_balance = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    positions = db.relationship(
        "StockPosition",
        back_populates="portfolio",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    user = db.relationship("User", back_populates="portfolios")


class StockPosition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey("portfolio.id"), nullable=False)
    symbol = db.Column(db.String(16), nullable=False, index=True)
    company_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    average_cost = db.Column(db.Float, nullable=False)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    portfolio = db.relationship("Portfolio", back_populates="positions")