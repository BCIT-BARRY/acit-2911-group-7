from __future__ import annotations

from functools import wraps

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from sqlalchemy import func

from . import oauth
from .extensions import db
from .models import Portfolio, StockPosition, User
from .services import FinnhubClient


bp = Blueprint("tracker", __name__)


def _oauth_client():
    return oauth.create_client(current_app.config["OAUTH_PROVIDER_NAME"])


def _oauth_ready() -> bool:
    return bool(current_app.config["OAUTH_CLIENT_ID"] and current_app.config["OAUTH_CLIENT_SECRET"])


def _current_user() -> User | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if _current_user() is None:
            return redirect(url_for("tracker.login", next=request.full_path if request.query_string else request.path))
        return view(*args, **kwargs)

    return wrapped


def _money(value: float | None) -> str:
    amount = value or 0.0
    return f"${amount:,.2f}"


def _percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.2f}%"


def _client() -> FinnhubClient:
    return FinnhubClient(current_app.config["FINNHUB_API_KEY"])


def _owned_portfolio_or_redirect(portfolio_id: int):
    user = _current_user()
    if user is None:
        return None
    portfolio = db.session.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == user.id,
    ).first()
    if portfolio is None:
        flash("Portfolio not found.", "error")
        return None
    return portfolio


def _owned_position_or_redirect(position_id: int):
    user = _current_user()
    if user is None:
        return None
    position = db.session.query(StockPosition).join(Portfolio).filter(
        StockPosition.id == position_id,
        Portfolio.user_id == user.id,
    ).first()
    if position is None:
        flash("Position not found.", "error")
        return None
    return position


def _portfolio_context(portfolio: Portfolio) -> dict:
    client = _client()
    positions = list(portfolio.positions)
    position_rows: list[dict] = []

    invested_total = 0.0
    market_value_total = 0.0

    for position in positions:
        snapshot = client.build_snapshot(position.symbol)
        current_price = snapshot.current_price or 0.0
        market_value = current_price * position.quantity
        cost_basis = position.average_cost * position.quantity
        gain_loss = market_value - cost_basis

        invested_total += cost_basis
        market_value_total += market_value

        position_rows.append(
            {
                "position": position,
                "snapshot": snapshot,
                "current_price": current_price,
                "market_value": market_value,
                "cost_basis": cost_basis,
                "gain_loss": gain_loss,
                "gain_loss_percent": (gain_loss / cost_basis * 100.0) if cost_basis else None,
            }
        )

    cash_balance = portfolio.cash_balance or 0.0
    total_equity = cash_balance + market_value_total
    total_pnl = total_equity - (cash_balance + invested_total)

    return {
        "portfolio": portfolio,
        "position_rows": position_rows,
        "cash_balance": cash_balance,
        "invested_total": invested_total,
        "market_value_total": market_value_total,
        "total_equity": total_equity,
        "total_pnl": total_pnl,
        "total_positions": len(position_rows),
        "money": _money,
        "percent": _percent,
    }


@bp.app_context_processor
def inject_helpers() -> dict:
    return {
        "money": _money,
        "percent": _percent,
        "current_user": _current_user(),
        "oauth_ready": _oauth_ready(),
    }


@bp.route("/login")
def login():
    if _current_user() is not None:
        return redirect(url_for("tracker.index"))

    next_url = request.args.get("next")
    if next_url:
        session["login_next"] = next_url

    if not _oauth_ready():
        flash("OAuth is not configured. Set OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET.", "error")
        return render_template("login.html")

    redirect_uri = current_app.config["OAUTH_REDIRECT_URI"] or url_for("tracker.auth_callback", _external=True)
    return _oauth_client().authorize_redirect(redirect_uri)


@bp.route("/auth/callback")
def auth_callback():
    if not _oauth_ready():
        flash("OAuth is not configured.", "error")
        return redirect(url_for("tracker.login"))

    token = _oauth_client().authorize_access_token()
    user_info = token.get("userinfo")
    if not user_info:
        user_info = _oauth_client().userinfo(token=token)

    provider = current_app.config["OAUTH_PROVIDER_NAME"]
    provider_sub = str(user_info.get("sub", "")).strip()
    email = user_info.get("email")
    name = user_info.get("name") or email or "Trader"

    if not provider_sub:
        flash("Unable to read user identity from OAuth provider.", "error")
        return redirect(url_for("tracker.login"))

    user = db.session.query(User).filter(User.provider_sub == provider_sub).first()
    if user is None:
        user = User(provider=provider, provider_sub=provider_sub, email=email, name=name)
        db.session.add(user)
    else:
        user.email = email
        user.name = name

    db.session.flush()
    user_id = user.id
    db.session.commit()
    session["user_id"] = user_id

    next_url = session.pop("login_next", None)
    return redirect(next_url or url_for("tracker.index"))


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("tracker.login"))


@bp.route("/")
@login_required
def index():
    user = _current_user()
    portfolios = db.session.query(Portfolio).filter(
        Portfolio.user_id == user.id
    ).order_by(Portfolio.created_at.desc()).all()
    selected_id = request.args.get("portfolio_id", type=int)
    selected_portfolio = (
        db.session.query(Portfolio).filter(
            Portfolio.id == selected_id,
            Portfolio.user_id == user.id,
        ).first()
        if selected_id is not None
        else portfolios[0]
        if portfolios
        else None
    )

    selected_context = _portfolio_context(selected_portfolio) if selected_portfolio else None

    overview_rows = []
    for portfolio in portfolios:
        holdings_value = db.session.query(
            func.coalesce(func.sum(StockPosition.quantity * StockPosition.average_cost), 0.0)
        ).filter(StockPosition.portfolio_id == portfolio.id).scalar()
        overview_rows.append(
            {
                "portfolio": portfolio,
                "positions": len(portfolio.positions),
                "cash_balance": portfolio.cash_balance,
                "book_value": holdings_value or 0.0,
            }
        )

    return render_template(
        "index.html",
        portfolios=overview_rows,
        selected_context=selected_context,
        selected_portfolio=selected_portfolio,
    )


@bp.route("/portfolios/new", methods=["GET", "POST"])
@login_required
def create_portfolio():
    user = _current_user()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        cash_balance = request.form.get("cash_balance", "0").strip() or 0

        if not name:
            flash("Portfolio name is required.", "error")
        else:
            portfolio = Portfolio(user_id=user.id, name=name, cash_balance=float(cash_balance))
            db.session.add(portfolio)
            db.session.commit()
            flash(f'Created portfolio "{portfolio.name}".', "success")
            return redirect(url_for("tracker.index", portfolio_id=portfolio.id))

    return render_template("portfolio_form.html", portfolio=None, form_action=url_for("tracker.create_portfolio"), title="Create portfolio")


@bp.route("/portfolios/<int:portfolio_id>/edit", methods=["GET", "POST"])
@login_required
def edit_portfolio(portfolio_id: int):
    portfolio = _owned_portfolio_or_redirect(portfolio_id)
    if portfolio is None:
        return redirect(url_for("tracker.index"))

    if request.method == "POST":
        portfolio.name = request.form.get("name", "").strip()
        portfolio.cash_balance = float(request.form.get("cash_balance", "0") or 0)
        if not portfolio.name:
            flash("Portfolio name is required.", "error")
        else:
            db.session.commit()
            flash(f'Updated portfolio "{portfolio.name}".', "success")
            return redirect(url_for("tracker.index", portfolio_id=portfolio.id))

    return render_template("portfolio_form.html", portfolio=portfolio, form_action=url_for("tracker.edit_portfolio", portfolio_id=portfolio.id), title="Edit portfolio")


@bp.post("/portfolios/<int:portfolio_id>/delete")
@login_required
def delete_portfolio(portfolio_id: int):
    portfolio = _owned_portfolio_or_redirect(portfolio_id)
    if portfolio is None:
        return redirect(url_for("tracker.index"))

    db.session.delete(portfolio)
    db.session.commit()
    flash(f'Deleted portfolio "{portfolio.name}".', "success")
    return redirect(url_for("tracker.index"))


@bp.route("/portfolios/<int:portfolio_id>/trade", methods=["GET", "POST"])
@login_required
def trade_position(portfolio_id: int):
    portfolio = _owned_portfolio_or_redirect(portfolio_id)
    if portfolio is None:
        return redirect(url_for("tracker.index"))

    if request.method == "POST":
        action = request.form.get("action", "buy").strip().lower()
        symbol = request.form.get("symbol", "").strip().upper()
        quantity = float(request.form.get("quantity", "0") or 0)
        trade_price = float(request.form.get("trade_price", "0") or 0)
        notes = request.form.get("notes", "").strip()

        if action not in {"buy", "sell"}:
            flash("Invalid trade action.", "error")
        elif not symbol:
            flash("Stock symbol is required.", "error")
        elif quantity <= 0:
            flash("Quantity must be greater than zero.", "error")
        elif trade_price <= 0:
            flash("Trade price must be greater than zero.", "error")
        else:
            snapshot = _client().build_snapshot(symbol)
            symbol = snapshot.symbol
            company_name = snapshot.company_name
            position = db.session.query(StockPosition).filter(
                StockPosition.portfolio_id == portfolio.id,
                StockPosition.symbol == symbol,
            ).first()

            trade_total = quantity * trade_price

            if action == "buy":
                if portfolio.cash_balance < trade_total:
                    flash("Not enough paper cash for this buy order.", "error")
                else:
                    portfolio.cash_balance -= trade_total

                    if position is None:
                        position = StockPosition(
                            portfolio_id=portfolio.id,
                            symbol=symbol,
                            company_name=company_name,
                            quantity=quantity,
                            average_cost=trade_price,
                            notes=notes or None,
                        )
                        db.session.add(position)
                    else:
                        total_shares = position.quantity + quantity
                        position.average_cost = (
                            (position.average_cost * position.quantity) + trade_total
                        ) / total_shares
                        position.quantity = total_shares
                        position.company_name = company_name
                        if notes:
                            position.notes = notes

                    db.session.commit()
                    flash(f"Bought {quantity:.4f} {symbol} for { _money(trade_total) }.", "success")
                    return redirect(url_for("tracker.index", portfolio_id=portfolio.id))

            if action == "sell":
                if position is None or position.quantity <= 0:
                    flash("No existing position found to sell.", "error")
                elif quantity > position.quantity:
                    flash("Cannot sell more shares than you currently hold.", "error")
                else:
                    portfolio.cash_balance += trade_total
                    remaining = position.quantity - quantity
                    if remaining <= 0:
                        db.session.delete(position)
                    else:
                        position.quantity = remaining
                        if notes:
                            position.notes = notes
                    db.session.commit()
                    flash(f"Sold {quantity:.4f} {symbol} for { _money(trade_total) }.", "success")
                    return redirect(url_for("tracker.index", portfolio_id=portfolio.id))

    return render_template(
        "trade_form.html",
        portfolio=portfolio,
        title="Buy or sell",
        form_action=url_for("tracker.trade_position", portfolio_id=portfolio.id),
    )


@bp.route("/positions/<int:position_id>/edit", methods=["GET", "POST"])
@login_required
def edit_position(position_id: int):
    position = _owned_position_or_redirect(position_id)
    if position is None:
        return redirect(url_for("tracker.index"))

    portfolio = position.portfolio

    if request.method == "POST":
        notes = request.form.get("notes", "").strip()
        position.notes = notes or None
        db.session.commit()
        flash(f"Updated notes for {position.symbol}.", "success")
        return redirect(url_for("tracker.index", portfolio_id=portfolio.id))

    return render_template(
        "position_form.html",
        portfolio=portfolio,
        position=position,
        title="Edit position",
        form_action=url_for("tracker.edit_position", position_id=position.id),
    )


@bp.post("/positions/<int:position_id>/delete")
@login_required
def delete_position(position_id: int):
    position = _owned_position_or_redirect(position_id)
    if position is None:
        return redirect(url_for("tracker.index"))

    portfolio_id = position.portfolio_id
    symbol = position.symbol
    db.session.delete(position)
    db.session.commit()
    flash(f'Deleted {symbol}.', "success")
    return redirect(url_for("tracker.index", portfolio_id=portfolio_id))