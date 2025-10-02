import logging
import numpy as np
import pandas as pd
import difflib
import base64
import io

import dash
from dash import Dash, html, dcc, callback, Output, Input, no_update, State, set_props
import dash_bootstrap_components as dbc

from datetime import datetime
from src.trade_diary.db_interface import delete_trade, insert_trade, insert_exit


dash.register_page(__name__)


date_formats = {
    "YYYY-MM-DD": "%Y-%m-%d",
    "DD-MM-YYYY": "%d-%m-%Y",
    "DD/MM/YYYY": "%d/%m/%Y",
    "YYYY/MM/DD": "%Y/%m/%d",
    "MM-DD-YYYY": "%m-%d-%Y",
    "MM/DD/YYYY": "%m/%d/%Y",
}

layout = dbc.Container(
    html.Div(
        [
            dcc.Dropdown(
                id="date-format",
                value="YYYY-MM-DD",
                options=[{"label": k, "value": v} for k, v in date_formats.items()],
                clearable=False,
                placeholder="Select Date Format",
                style={"margin": "10px", "marginTop": "120px"},
            ),
            dcc.Upload(
                id="upload-data",
                children=html.Div(["Drag and Drop or ", html.A("Select Files")]),
                style={
                    "height": "60px",
                    "lineHeight": "60px",
                    "borderWidth": "1px",
                    "borderStyle": "dashed",
                    "borderRadius": "5px",
                    "textAlign": "center",
                    "margin": "10px",
                },
                multiple=False,
            ),
            html.Div(
                id="output-data-upload",
                style={
                    "textAlign": "center",
                    "color": "red",
                    "fontSize": "1.4em",
                    "marginTop": "40px",
                    "fontWeight": "bold",
                },
            ),
        ]
    ),
)


def get_mappings(df_columns):
    cols = df_columns
    to_match_names = [
        ("symbol", ["symbol", "stock", "name", "scrip"]),
        ("setup", ["setup", "strategy"]),
        ("entry_date", ["buy date", "purchase date", "entry date"]),
        ("entry_price", ["entry price", "buy price"]),
        ("entry_type", ["entry type", "buy type", "entry"]),
        (
            "quantity",
            ["quantity", "qty", "no of shares", "entry quantity", "entry qty"],
        ),
        ("risk_percentage", ["risk percentage", "risk", "risk %"]),
        ("stop_loss", ["stop loss", "sl"]),
        ("exit_date", ["sell date", "exit date"]),
        ("exit_price", ["exit price", "sell price"]),
        # ('exit_quantity' , ['exit quantity','sell quantity']),
    ]
    not_necessary_fields = ['entry_type']
    fields_to_col_mapping = []
    for key, possible_names in to_match_names:
        for possible_name in possible_names:
            match = difflib.get_close_matches(possible_name, cols, n=1, cutoff=0.9)
            if match:
                fields_to_col_mapping.append((key, match[0]))
                break

    matched = [x[0] for x in fields_to_col_mapping]
    not_matched_fields = [x[0] for x in to_match_names if x[0] not in matched]
    not_matched_fields = set(not_matched_fields).difference(set(not_necessary_fields))
    return fields_to_col_mapping, not_matched_fields


@callback(
    Output("output-data-upload", "children"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
    State("date-format", "value"),
    prevent_initial_call=True,
)
def upload_file(contents, file_name, date_format):
    if contents is None:
        return no_update, 0
    try:
        logging.info(f"Uploading file: {file_name}")
        content_type, content_data = contents.split(",")
        content_data = base64.b64decode(content_data)
    except Exception as e:
        logging.error(f"Error decoding file: {e}")
        return f"Error decoding file: {e}"
    try:
        if "csv" in file_name:
            df = pd.read_csv(io.StringIO(content_data.decode("utf-8")))
        elif "xls" in file_name or "xlsx" in file_name:
            df = pd.read_excel(io.BytesIO(content_data))
        else:
            return "File type not supported"
    except Exception as e:
        logging.error(f"Error processing file: {e}")
        return f"Error processing file: {e}"

    df = df.rename(columns=lambda x: x.lower())
    fields_to_col_mapping, not_matched_fields = get_mappings(df.columns.tolist())


    if not_matched_fields:
        return f"Unmatched fields: {', '.join(not_matched_fields)}"
    logging.info(f"Fields to Column Mapping: {fields_to_col_mapping}")

    req_cols = [x[0] for x in fields_to_col_mapping]
    df = df.rename(columns={d[1]: d[0] for d in fields_to_col_mapping})[req_cols]

    trades_fields = ["symbol", "setup"]
    entry_fields = [
        "entry_date",
        "entry_price",
        "quantity",
        "risk_percentage",
        "stop_loss",
    ]
    exit_fields = ["exit_date", "exit_price", "exit_quantity"]
    oth_fields = ["entry_type"]

    nan_error = ""
    for col in trades_fields + entry_fields:
        if df[col].isna().sum() > 0:
            nan_error += f"Column {col} contains NaN values\n"
    if nan_error:
        return nan_error

    for col in df.filter(like="date", axis=1):
        try:
            df[col] = pd.to_datetime(df[col], format=date_format)
        except Exception as e:
            logging.error(f"Error converting date columns {col} : {e}")
            return f"Error converting date columns {col} : {e}"

    for col in df.filter(like="price|quantity", axis=1):
        try:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        except Exception as e:
            logging.error(f"Error converting price columns {col} : {e}")
            return f"Error converting price columns {col} : {e}"

    inserted_trades, not_inserted_trades = [], []
    # print(df)
    df_cols = trades_fields + entry_fields

    agg_dict =  {
                "entry_price": "max",
                "quantity": "sum",
                "risk_percentage": lambda x: x.max() * 100,
                "stop_loss": "max",
                "setup": "first"
            }
    
    if "entry_type" in df.columns:
        df_cols += oth_fields
        agg_dict["entry_type"] = "first"

    df_agg_trades = (
        df[df_cols]
        .groupby(["symbol", "entry_date"])
        .agg(agg_dict)
        .reset_index()
    )

    logging.info(f"Processing {len(df_agg_trades)} rows")
    # print(df_agg_trades)

    for index, row in df_agg_trades.iterrows():
        try:
            trade_id = insert_trade(
                symbol=row["symbol"],
                setup=row["setup"],
                entry_date=row["entry_date"],
                entry_price=float(row["entry_price"]),
                quantity=int(row["quantity"]),
                risk_percentage=float(row["risk_percentage"]),
                stop_loss=float(row["stop_loss"]),
                entry_type=row.get("entry_type", None),
            )
            inserted_trades.append((trade_id, index, row["symbol"], row["entry_date"]))
            logging.info(
                f"Inserted trade: {trade_id} {index} {row['symbol']} {row['entry_date']}"
            )
        except Exception as e:
            logging.error(
                f"Error inserting trade {row['symbol']} {row['entry_date']}: {e}"
            )
            not_inserted_trades.append(
                (index, row["symbol"], row["entry_date"], str(e))
            )

    if not_inserted_trades:
        logging.error(f"Error inserting trades: {not_inserted_trades}")
        for trade_id, _, _, _ in inserted_trades:
            delete_trade(trade_id)
        return f"Error inserting Following trades:\n {not_inserted_trades}"

    trades = pd.DataFrame(
        inserted_trades, columns=["trade_id", "index", "symbol", "entry_date"]
    )

    df_trades = trades.merge(df, on=["symbol", "entry_date"], how="inner").query(
        "exit_date.notnull()"
    )

    if df_trades.empty:
        logging.warning("No Closed trade found.")
        return f"File uploaded successfully! {len(inserted_trades)} trades inserted."

    df_exits_agg = (
        df_trades.groupby(["trade_id", "exit_date"])
        .agg(
            {
                "exit_price": "first",
                "quantity": "sum",
            }
        )
        .reset_index()
    )

    failed_exits = []
    for index, row in df_exits_agg.iterrows():
        try:
            result = insert_exit(
                trade_id=row["trade_id"],
                exit_price=row["exit_price"],
                quantity=row["quantity"],
                exit_date=row["exit_date"],
                exit_type=None,
            )
            if not result:
                failed_exits.append(row["trade_id"])
        except Exception as e:
            logging.error(f"Error inserting exit for trade {row['trade_id']}: {e}")
            failed_exits.append(row["trade_id"])
    if failed_exits:
        logging.error(f"Failed to insert exits for trades: {failed_exits}")
        for trade_id, _, _, _ in inserted_trades:
            delete_trade(trade_id)
        return f"Error inserting Exit details for trades:\n {failed_exits}"
    return f"File uploaded successfully! {len(inserted_trades)} trades inserted."
