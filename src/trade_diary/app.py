import dash
from dash import Dash, dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc

app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], use_pages=True)


nav = dbc.Nav(
    [
        dbc.NavLink(
            "Trades",
            href="/",
            active="exact",
            style={"fontWeight": "bold", "fontSize": "1.2rem", "color": "#007bff"},
        ),
        dbc.NavLink(
            "Statistics",
            href="/stats",
            active="exact",
            style={"fontWeight": "bold", "fontSize": "1.2rem", "color": "#007bff"},
        ),
        dbc.NavLink(
            "Upload File",
            href="/upload",
            active="exact",
            style={"fontWeight": "bold", "fontSize": "1.2rem", "color": "#007bff"},
        ),
    ],
    className="navbar_custom",
)


app.layout = html.Div([nav, dash.page_container])


if __name__ == "__main__":
    app.run("0.0.0.0", debug=True)
