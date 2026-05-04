# acit-2911-group-7

Flask paper trading portfolio tracker backed by SQLite and Finnhub.

## Features

- Create, edit, and delete portfolios.
- Add, edit, and delete stock positions inside each portfolio.
- Pull live quote and profile data from Finnhub.
- Persist portfolios and positions in a local SQLite database.

## Run with UV

```bash
uv sync
uv run serve
```

The app stores data in `instance/portfolio.db`.

## Environment

- `FINNHUB_API_KEY` defaults to the Finnhub key supplied for this project.
- `SECRET_KEY` can be overridden for a custom Flask secret.
- `OAUTH_CLIENT_ID` and `OAUTH_CLIENT_SECRET` are required for login.
- `OAUTH_PROVIDER_NAME` defaults to `google`.
- `OAUTH_SERVER_METADATA_URL` defaults to Google OpenID configuration.
- `OAUTH_SCOPE` defaults to `openid email profile`.
- `OAUTH_REDIRECT_URI` defaults to `http://127.0.0.1:5000/auth/callback` and must exactly match the URI registered in Google Cloud Console.

## Notes

- This is a paper trading tracker only; it does not place real orders.