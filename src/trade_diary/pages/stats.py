import logging
import numpy as np
import pandas as pd
from functools import reduce

import dash
from dash import Dash, html, dcc, callback, Output, Input, no_update, set_props
import dash_bootstrap_components as dbc

from datetime import datetime
from src.trade_diary.db_interface import (
    get_all_financial_years,
    get_all_entries,
    get_all_exits,
    get_all_trades,
)


dash.register_page(__name__)


def get_display_data(financial_year):
    entries = get_all_entries(financial_year=financial_year)
    if entries.empty:
        logging.debug("get_display_data: No entries found")
        return None

    entries["entry_date"] = pd.to_datetime(entries["entry_date"], format="%Y-%m-%d")
    entries["entry_amount"] = entries["entry_price"] * entries["quantity"]
    entries["risked_amount"] = entries["quantity"] * (
        entries["entry_price"] - entries["stop_loss"]
    )

    entries_agg = (
        entries.groupby("trade_id")
        .agg(
            {
                "entry_id": "count",
                "entry_date": "min",
                "entry_amount": "sum",
                "quantity": "sum",
                "remaining_quantity": "sum",
                "risk_percentage": "sum",
                "exit_amount": "sum",
                "charges": "sum",
                "risked_amount": "sum",
            }
        )
        .reset_index()
    )

    entries_agg["gross_pl"] = (
        entries_agg["exit_amount"] - entries_agg["entry_amount"]
    ).round(2)
    entries_agg["net_pl"] = (entries_agg["gross_pl"] - entries_agg["charges"]).round(2)
    entries_agg["net_pl_percentage"] = (
        (entries_agg["net_pl"] / entries_agg["entry_amount"]) * 100
    ).round(2)
    entries_agg["gross_R"] = (
        entries_agg["net_pl"] / entries_agg["risked_amount"]
    ).round(2)
    entries_agg["net_R"] = (
        entries_agg["risk_percentage"] * entries_agg["gross_R"]
    ).round(2)
    entries_agg["win"] = entries_agg["net_pl"].apply(lambda x: 1 if x > 0 else 0)

    exits = get_all_exits(financial_year=financial_year)
    exits["exit_date"] = pd.to_datetime(exits["exit_date"], format="%Y-%m-%d")
    exits_agg = (
        exits.groupby("trade_id")
        .agg(exit_count=("exit_id", "count"), exit_date=("exit_date", "max"))
        .reset_index()
    )

    trades = get_all_trades(financial_year=financial_year)
    trades["initial_entry_date"] = pd.to_datetime(
        trades["initial_entry_date"], format="%Y-%m-%d"
    )
    trades["i_entry_date"] = trades["initial_entry_date"].dt.date
    trade_month = trades["initial_entry_date"].dt.month
    conditions = [
        (trade_month >= 1) & (trade_month <= 3),
        (trade_month >= 4) & (trade_month <= 6),
        (trade_month >= 7) & (trade_month <= 9),
        (trade_month >= 10) & (trade_month <= 12),
    ]
    qtr_vals = ["Q4", "Q1", "Q2", "Q3"]
    trades["qtr"] = np.select(conditions, qtr_vals, "N/A")
    trades["qtr"] = (
        trades["initial_entry_date"].dt.year.astype(str) + "-" + trades["qtr"]
    )
    trades["setup"] = trades["setup"].fillna("N/A").str.upper()

    trades = reduce(
        lambda left, right: pd.merge(left, right, on="trade_id", how="inner"),
        [trades, entries_agg, exits_agg],
    )
    trades["no_of_days"] = (
        trades["exit_date"] - trades["initial_entry_date"]
    ).dt.days.fillna(0)
    trades["no_of_days_win"] = np.where(
        trades["win"] == 1, trades["no_of_days"], np.nan
    )
    trades["no_of_days_loss"] = np.where(
        trades["win"] == 0, trades["no_of_days"], np.nan
    )

    trades_disp_cols = [
        "symbol",
        "i_entry_date",
        "setup",
        "financial_year",
        "qtr",
        "risk_percentage",
        "charges",
        "gross_pl",
        "net_pl",
        "net_pl_percentage",
        "gross_R",
        "net_R",
        "win",
        "no_of_days",
        "no_of_days_win",
        "no_of_days_loss",
    ]
    renamed_cols = {
        "symbol": "Symbol",
        "i_entry_date": "Initial Entry Date",
        "setup": "Setup",
        "financial_year": "Financial Year",
        "qtr": "Quarter",
        "risk_percentage": "Risk %",
        "charges": "Charges",
        "gross_pl": "Gross P&L",
        "net_pl": "Net P&L",
        "net_pl_percentage": "Net P&L %",
        "gross_R": "Gross R",
        "net_R": "Net R",
        "win": "Win",
        "no_of_days": "No. of Days",
        "no_of_days_win": "No. of Days (Win)",
        "no_of_days_loss": "No. of Days (Loss)",
    }
    trades_display = (
        trades[trades_disp_cols]
        .sort_values(by="i_entry_date")
        .rename(columns=renamed_cols)
    )

    groupers = {
        "Month-Year": trades["initial_entry_date"].dt.strftime("%B-%Y"),
        "Quarter": trades["qtr"].rename("initial_entry_date"),
        "FY": "financial_year",
        "Set-Up": "setup",
    }
    display_dfs = {}
    for name, grouper in groupers.items():
        display_df = (
            trades.groupby(grouper)
            .agg(
                **{
                    "sdate": ("initial_entry_date", "min"),
                    "Total Trades": ("initial_entry_date", "count"),
                    "Wins": ("win", "sum"),
                    "Losses": ("win", lambda x: x.count() - x.sum()),
                    "Gross R": ("gross_R", "sum"),
                    "Net R": ("net_R", "sum"),
                    "Win %": ("win", lambda x: x.mean() * 100),
                    "Win Avg": ("net_pl_percentage", lambda x: x[x > 0].mean()),
                    "Loss Avg": ("net_pl_percentage", lambda x: x[x <= 0].mean()),
                    "Max Win": ("net_pl_percentage", lambda x: x[x > 0].max()),
                    "Max Loss": ("net_pl_percentage", lambda x: x[x <= 0].min()),
                    "Max R": ("net_R", "max"),
                    "Min R": ("net_R", "min"),
                    "Avg Win Days": ("no_of_days_win", "mean"),
                    "Avg Loss Days": ("no_of_days_loss", "mean"),
                }
            )
            .reset_index()
            .sort_values(by="sdate")
            .assign(
                RR=lambda df: (df["Win Avg"] / df["Loss Avg"]),
                AWLR=lambda df: (
                    (df["Win %"] * df["Win Avg"])
                    / ((100 - df["Win %"]) * df["Loss Avg"])
                ),
            )
        )
        for col in display_df.select_dtypes(include=[float]).columns:
            display_df[col] = display_df[col].round(2)

        display_df["Win %"] = np.ceil(display_df["Win %"]).fillna(0).astype("int")
        display_df["Avg Win Days"] = (
            np.ceil(display_df["Avg Win Days"]).fillna(0).astype("int")
        )
        display_df["Avg Loss Days"] = (
            np.ceil(display_df["Avg Loss Days"]).fillna(0).astype("int")
        )
        display_dfs[name] = display_df.drop("sdate", axis=1).rename(
            columns={"initial_entry_date": name}
        )

    display_dfs["trades"] = trades_display
    return display_dfs


def centre_table_contents(table_var):
    table_var.children[0].children[0].style = {"textAlign": "left"}
    for row in table_var.children[1].children:
        row.children[0].style = {"textAlign": "left"}


summary_year = dbc.Row(
    [
        html.H5(
            "Yearly",
            style={
                "textAlign": "center",
                "marginTop": "20px",
                "fontWeight": "500",
                "fontSize": "1.3rem",
            },
        ),
        html.Hr(),
        html.Div(id="summary-tab-yearly", className="table-responsive"),
    ],
)


summary_qtr = dbc.Row(
    [
        html.H5(
            "Quarterly",
            style={
                "textAlign": "center",
                "marginTop": "20px",
                "display": "block",
                "fontWeight": "500",
                "fontSize": "1.3rem",
            },
        ),
        html.Hr(),
        html.Div(id="summary-tab-quarterly", className="table-responsive"),
    ],
)


summary_month = dbc.Row(
    [
        html.H5(
            "Monthly",
            style={
                "textAlign": "center",
                "marginTop": "20px",
                "display": "block",
                "fontWeight": "500",
                "fontSize": "1.3rem",
            },
        ),
        html.Hr(),
        html.Div(id="summary-tab-monthly", className="table-responsive"),
    ],
)

summary_setup = dbc.Row(
    [
        html.H5(
            "Set-Up",
            style={
                "textAlign": "center",
                "marginTop": "20px",
                "display": "block",
                "fontWeight": "500",
                "fontSize": "1.3rem",
            },
        ),
        html.Hr(),
        html.Div(id="summary-tab-setup", className="table-responsive"),
    ],
)

summary_trades = dbc.Row(
    [
        html.H5(
            "Trades",
            style={
                "textAlign": "center",
                "marginTop": "20px",
                "display": "block",
                "fontWeight": "500",
                "fontSize": "1.3rem",
            },
        ),
        html.Hr(),
        html.Div("trsting", id="summary-tab-trades", className="table-responsive"),
    ],
    id="summary-trades-row",
    style={"display": "None"},
)

fy_years = get_all_financial_years()

if fy_years:
    fy_years.append("All")
else:
    fy_years = ["All"]
drop_down_options = [{"label": str(y), "value": y} for y in fy_years]

side_bar = html.Div(
    [
        dbc.Container(
            [
                dcc.Dropdown(
                    id="display-year",
                    value=fy_years[0],
                    options=[{"label": str(y), "value": y} for y in fy_years],
                    clearable=False,
                ),
                html.Br(),
                dcc.Checklist(
                    [
                        {
                            "label": html.Span(
                                "Show Trades",
                                style={"font-size": "1.5rem", "padding-left": 10},
                            ),
                            "value": "yes",
                        }
                    ],
                    id="show-trades",
                    labelStyle={"display": "flex", "align-items": "left"},
                ),
            ]
        )
    ],
)

layout = dbc.Row(
    [
        dbc.Col(side_bar, className="sidebar_style"),
        dbc.Col(
            dbc.Container(
                [
                    html.H5(
                        "Summary",
                        id="summary-header",
                        style={
                            "textAlign": "center",
                            "marginTop": "50px",
                            "marginBottom": "20px",
                            "fontWeight": "800",
                            "fontSize": "1.5rem",
                            "letterSpacing": "1px",
                            "color": "#f13921",
                        },
                    ),
                    html.Br(),
                    summary_year,
                    summary_qtr,
                    summary_month,
                    summary_setup,
                    summary_trades,
                ],
                className="content_style",
            )
        ),
    ]
)


@callback(
    Output("summary-header", "children"),
    Output("summary-tab-yearly", "children"),
    Output("summary-tab-quarterly", "children"),
    Output("summary-tab-monthly", "children"),
    Output("summary-tab-setup", "children"),
    Output("summary-tab-trades", "children"),
    Output("display-year", "options"),
    Input("display-year", "value"),
    Input("show-trades", "value"),
)
def update_summary_header(input_value, show_trades):
    fy_years = get_all_financial_years()

    if fy_years:
        fy_years.append("All")
    else:
        fy_years = ["All"]

    drop_down_options = [{"label": str(y), "value": y} for y in fy_years]

    display_dfs = None
    if input_value == "All":
        display_dfs = get_display_data("all")
        header = "Summary - All Financial Years"
    elif input_value:
        display_dfs = get_display_data(input_value)
        header = f"Summary - Financial Year {input_value}"
    else:
        empty_df = "No Data"
        header = f"No Data"
        return (
            header,
            empty_df,
            empty_df,
            empty_df,
            empty_df,
            empty_df,
            drop_down_options,
        )

    if display_dfs is None:
        empty_df = "No Data"
        header = f"No Closed Trades for Fy - {input_value}"
        return (
            header,
            empty_df,
            empty_df,
            empty_df,
            empty_df,
            empty_df,
            drop_down_options,
        )

    summary_tab_yearly = dbc.Table.from_dataframe(
        display_dfs["FY"],
        striped=True,
        bordered=True,
        hover=True,
        style={"textAlign": "center"},
    )
    centre_table_contents(summary_tab_yearly)

    summary_tab_quarterly = dbc.Table.from_dataframe(
        display_dfs["Quarter"].sort_values(by="Quarter"),
        striped=True,
        bordered=True,
        hover=True,
        style={"textAlign": "center"},
    )
    centre_table_contents(summary_tab_quarterly)

    summary_tab_monthly = dbc.Table.from_dataframe(
        display_dfs["Month-Year"],
        striped=True,
        bordered=True,
        hover=True,
        style={"textAlign": "center"},
    )
    centre_table_contents(summary_tab_monthly)

    summary_tab_setup = dbc.Table.from_dataframe(
        display_dfs["Set-Up"],
        striped=True,
        bordered=True,
        hover=True,
        style={"textAlign": "center"},
    )
    centre_table_contents(summary_tab_setup)

    summary_trades = dbc.Table.from_dataframe(
        display_dfs["trades"],
        striped=True,
        bordered=True,
        hover=True,
        style={"textAlign": "center"},
    )
    centre_table_contents(summary_trades)

    if show_trades and "yes" in show_trades:
        set_props("summary-trades-row", {"style": {"display": "block"}})
    else:
        set_props("summary-trades-row", {"style": {"display": "none"}})

    return (
        header,
        summary_tab_yearly,
        summary_tab_quarterly,
        summary_tab_monthly,
        summary_tab_setup,
        summary_trades,
        drop_down_options,
    )
