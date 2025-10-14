from dash import (
    Dash,
    callback_context,
    html,
    dcc,
    callback,
    Output,
    Input,
    State,
    no_update,
    set_props,
)
import dash

from src.trade_diary.validate import *
from src.trade_diary.db_interface import *
from src.trade_diary.utility_functions import (
    add_additional_columns,
    extract_financial_year,
)
from datetime import date
import pandas as pd

from src.trade_diary.pages.trades_ui import *


dash.register_page(__name__, path="/")


layout = dbc.Row(
    [
        dbc.Col(side_bar, className="sidebar_style"),
        dbc.Col(trade_book),
        # extras
        db_update_store,
        dcc.ConfirmDialog(
            id="error-dialog",
            message="",
            displayed=False,
        ),
        info_dialog,
        entry_dialog,
        exit_dialog,
        pyramid_dialog,
        del_dialog,
    ]
)


@callback(
    Output("trades-table", "getRowsResponse"),
    Input("db-update", "data"),
    Input("trades-table", "getRowsRequest"),
    Input("display_year", "value"),
    Input("show-open", "value"),
)
def refresh_trades_table(data, request, financial_year, show_open):
    logging.debug(
        f"refresh_trades_table:Triggered with data={data}, financial_year={financial_year}, show_open={show_open},request={request}"
    )
    clear_all_fields()

    if len(show_open) > 0:
        show_trades = "open"
    else:
        show_trades = "all"

    ctx = callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    filters = {}
    if data == 100 or trigger_id == "display_year" or request:
        if request and request["filterModel"]:
            initial_date_filter = request["filterModel"]["initial_entry_date"]

            sdate = datetime.strptime(
                initial_date_filter["dateFrom"], "%Y-%m-%d %H:%M:%S"
            ).date()
            edate = (
                datetime.strptime(
                    initial_date_filter["dateTo"], "%Y-%m-%d %H:%M:%S"
                ).date()
                if initial_date_filter["dateTo"]
                else None
            )

            filters["initial_entry_date"] = (initial_date_filter["type"], sdate, edate)

        trades = get_all_trades_and_entries(
            show_trades, financial_year=financial_year, filter_conditions=filters
        )

        if trades is None or trades.empty:
            logging.error(
                "refresh_trades_table:No trades found or error fetching trades."
            )
            dummy = [{x["field"]: None for x in display_col_def}]
            return {"rowData": dummy, "rowCount": 1}

        trades = add_additional_columns(trades)

        return {"rowData": trades.to_dict("records"), "rowCount": len(trades)}
    else:
        return no_update


@callback(Output("display_year", "options"), Input("db-update", "data"))
def update_display_year_options(data):
    if data != 100:
        return no_update

    fy_years = get_all_financial_years()
    if not fy_years:
        fy_years = [extract_financial_year(date.today())]
    return [{"label": str(y), "value": y} for y in fy_years]


@callback(
    Output("trade-book-header", "children"),
    Input("display_year", "value"),
)
def update_trade_book_header(financial_year):
    logging.debug(f"Updating Trade Book Header for Financial Year: {financial_year}")
    return f"Trades For FY {financial_year}"


@callback(
    Output("trade-details", "children"),
    Input("trades-table", "selectedRows"),
    prevent_initial_call=True,
)
def on_selection(selectedRows):
    logging.debug(f"on_selection:Selected Rows: {selectedRows}")
    if selectedRows:
        set_props("trade-details", {"style": {"display": "block"}})

        details = get_trades_details_component(selectedRows)
        accordian_children = []

        entries = get_entries(selectedRows[0]["trade_id"])

        if entries:
            entry_tabl = get_entry_details_table(entries)
            entry_acc = dbc.AccordionItem(entry_tabl, title="Entries")
            accordian_children.append(entry_acc)

        exits = get_exits(selectedRows[0]["trade_id"])

        if exits:
            exit_tabl = get_exit_details_table(exits)
            exit_acc = dbc.AccordionItem(exit_tabl, title="Exits")
            accordian_children.append(exit_acc)

        card_body_children = [details]
        if accordian_children:
            accordian = dbc.Accordion(
                accordian_children, start_collapsed=True, flush=True
            )
            card_body_children.append(accordian)

        card = dbc.Card(
            [
                dbc.CardHeader("Trade Details", style={"textAlign": "center"}),
                dbc.CardBody(card_body_children, style={"padding": "20px"}),
            ]
        )
        return card


@callback(
    Output("add-dialog", "is_open"),
    Input("add-position", "n_clicks"),
    prevent_initial_call=True,
)
def on_add_position(n_clicks):
    logging.debug(f"on_add_position: Add Position Clicked with {n_clicks}")
    if n_clicks:
        return True
    return no_update


@callback(
    Output("db-update", "data", allow_duplicate=True),
    [
        Input("add-submit", "n_clicks"),
    ],
    [
        State("symbol", "value"),
        State("entry-date", "date"),
        State("entry-price", "value"),
        State("entry-quantity", "value"),
        State("risk-percentage", "value"),
        State("setup", "value"),
        State("entry-type", "value"),
        State("stop-loss", "value"),
    ],
    prevent_initial_call=True,
)
def on_add_submit(
    n_clicks,
    symbol,
    entry_date,
    entry_price,
    entry_quantity,
    risk_percent,
    setup,
    entry_type,
    stop_loss,
):
    logging.debug(f"on_add_submit: Add Submit Clicked with symbol: {symbol}")
    if n_clicks:
        trade_id = add_position(
            symbol=symbol,
            entry_price=entry_price,
            entry_quantity=entry_quantity,
            entry_date=entry_date,
            risk_percentage=risk_percent,
            setup=setup,
            entry_type=entry_type,
            stop_loss=stop_loss,
        )
        set_props("add-dialog", {"is_open": False})
        if trade_id is None:
            return 0

        clear_entry_fields()
        clear_trade_details()
        return 100

    return 0


@callback(
    Output("exit-dialog", "is_open"),
    Input("exit-position", "n_clicks"),
    State("trades-table", "selectedRows"),
    prevent_initial_call=True,
)
def on_exit_position(n_clicks, selectedRows):
    logging.debug(f"Exit Position Clicked with {selectedRows} and {n_clicks}")
    if selectedRows and n_clicks:
        if selectedRows[0]["total_open_position"] > 0:
            set_props(
                "exit-quantity", {"value": selectedRows[0]["total_open_position"]}
            )
            return True
        else:
            set_props("info_dialog", {"is_open": True})
            set_props("info_dialog_text", {"children": "Cannot Exit Closed Trade"})
            return no_update
    return no_update


@callback(
    Output("db-update", "data", allow_duplicate=True),
    Input("exit-submit", "n_clicks"),
    State("exit-quantity", "value"),
    State("exit-price", "value"),
    State("exit-date", "date"),
    State("exit-type", "value"),
    State("trades-table", "selectedRows"),
    prevent_initial_call="initial_duplicate",
)
def on_exit_submit(
    n_clicks, exit_quantity, exit_price, exit_date, exit_type, selectedRows
):
    if selectedRows and n_clicks:
        exit_id = exit_position(
            trade_id=selectedRows[0]["trade_id"],
            total_open_position=selectedRows[0]["total_open_position"],
            exit_price=exit_price,
            exit_quantity=exit_quantity,
            exit_date=exit_date,
            exit_type=exit_type,
        )
        set_props("exit-dialog", {"is_open": False})
        if exit_id is None:
            return 0

        clear_exit_fields()
        clear_trade_details()
        return 100

    return 0


@callback(
    Output("pyramid-dialog", "is_open"),
    Input("pyramid", "n_clicks"),
    State("trades-table", "selectedRows"),
    prevent_initial_call=True,
)
def on_pyramid(n_clicks, selectedRows):
    logging.debug(
        f"on_pyramid: Pyramid Position Clicked with {selectedRows} and {n_clicks}"
    )
    if selectedRows and n_clicks:
        if selectedRows[0]["total_open_position"] > 0:
            return True
        else:
            set_props("info_dialog", {"is_open": True})
            set_props(
                "info_dialog_text", {"children": "Cannot Pyramid on Closed Trade"}
            )
            return no_update
    return no_update


@callback(
    Output("db-update", "data", allow_duplicate=True),
    Input("pyramid-submit", "n_clicks"),
    State("entry-quantity-pyramid", "value"),
    State("entry-price-pyramid", "value"),
    State("entry-date-pyramid", "date"),
    State("risk-percentage-pyramid", "value"),
    State("stop-loss-pyramid", "value"),
    State("trades-table", "selectedRows"),
    prevent_initial_call=True,
)
def on_pyramid_submit(
    n_clicks,
    entry_quantity,
    entry_price,
    entry_date,
    risk_percentage,
    stop_loss,
    selectedRows,
):
    logging.debug(
        f"on_pyramid_submit: Pyramid Submit Clicked with {selectedRows} and {n_clicks}"
    )
    if selectedRows and n_clicks:
        entry_id = pyramid_position(
            trade_id=selectedRows[0]["trade_id"],
            entry_price=entry_price,
            entry_quantity=entry_quantity,
            entry_date=entry_date,
            risk_percentage=risk_percentage,
            stop_loss=stop_loss,
        )
        set_props("pyramid-dialog", {"is_open": False})
        if entry_id is None:
            return 0

        clear_pyramid_fields()
        clear_trade_details()
        return 100

    return 0


@callback(
    Output("del_dialog", "is_open", allow_duplicate=True),
    Output("del-confirm", "children", allow_duplicate=True),
    Input("delete-position", "n_clicks"),
    State("trades-table", "selectedRows"),
    prevent_initial_call=True,
)
def on_delete_position(n_clicks, selectedRows):
    logging.debug(f"Delete Position Clicked with {selectedRows} and {n_clicks}")
    if selectedRows and n_clicks:
        return True, f"Are you sure you want to delete selected Trade ?"
    return False, no_update


@callback(
    Output("db-update", "data", allow_duplicate=True),
    Output("del_dialog", "is_open", allow_duplicate=True),
    Output("del-confirm", "children", allow_duplicate=True),
    Input("del-confirm-close", "n_clicks"),
    State("trades-table", "selectedRows"),
    prevent_initial_call=True,
)
def on_delete_confirm(n_clicks, selectedRows):
    logging.debug(f"Delete Confirm Clicked with {selectedRows} and {n_clicks}")
    if selectedRows and n_clicks:
        if delete_trade(int(selectedRows[0]["trade_id"])):
            clear_trade_details()
            refresh_fy_dropdown()
            logging.debug(f"Deleted Trade {selectedRows[0]['trade_id']}")
            return 100, False, no_update
        else:
            return 0, False, "Error Deleting Trade"

    return 0, False, no_update


@callback(Output("info_dialog", "is_open"), Input("info_dialog_close", "n_clicks"))
def close_info_dialog(n_clicks):
    return False


@callback(Input("clear-selection", "n_clicks"))
def on_clear_selection(n_clicks):
    clear_all_fields()


def clear_all_fields():
    clear_entry_fields()
    clear_exit_fields()
    clear_pyramid_fields()
    clear_trade_details()


def clear_entry_fields():
    set_props("symbol", {"value": ""})
    set_props("entry-date", {"value": date.today()})
    set_props("entry-price", {"value": 0})
    set_props("entry-quantity", {"value": 0})
    set_props("setup", {"value": ""})
    set_props("entry-type", {"value": ""})
    set_props("stop-loss", {"value": 0})
    set_props("risk-percentage", {"value": 0})


def clear_exit_fields():
    set_props("exit-quantity", {"value": 0})
    set_props("exit-price", {"value": 0})
    set_props("exit-date", {"value": date.today()})
    set_props("exit-type", {"value": ""})


def clear_pyramid_fields():
    set_props("entry-quantity-pyramid", {"value": 0})
    set_props("entry-price-pyramid", {"value": 0})
    set_props("entry-date-pyramid", {"value": date.today()})
    set_props("entry-type-pyramid", {"value": ""})
    set_props("risk-percentage-pyramid", {"value": 0})


def clear_trade_details():
    set_props("trade-details", {"style": {"display": "none"}})
    set_props("trades-table", {"selectedRows": []})


def refresh_fy_dropdown():
    fy_years = get_all_financial_years()
    if not fy_years:
        fy_years = [extract_financial_year(date.today())]
        options = [{"label": str(y), "value": y} for y in fy_years]
        set_props("display_year", {"options": options})
        set_props("display_year", {"value": fy_years[0]})


def add_position(
    symbol,
    entry_price,
    entry_quantity,
    entry_date,
    risk_percentage,
    setup,
    entry_type,
    stop_loss,
):
    error = validate_add_position(
        symbol=symbol,
        entry_price=entry_price,
        entry_quantity=entry_quantity,
        entry_date=entry_date,
        risk_percentage=risk_percentage,
        setup=setup,
        entry_type=entry_type,
        stop_loss=stop_loss,
    )

    if error:
        error_msg = "\n".join(error)
        set_props("info_dialog", {"is_open": True})
        set_props("info_dialog_text", {"children": error_msg})
        return None

    edate = datetime.fromisoformat(entry_date).date()
    trade_id = insert_trade(
        symbol=symbol,
        entry_price=entry_price,
        quantity=entry_quantity,
        entry_date=edate,
        risk_percentage=risk_percentage,
        setup=setup,
        entry_type=entry_type,
        stop_loss=stop_loss,
    )

    if trade_id is None:
        set_props("info_dialog", {"is_open": True})
        set_props("info_dialog_text", {"children": "Error Inserting Trade"})
        return None

    return trade_id


def exit_position(
    trade_id, total_open_position, exit_price, exit_quantity, exit_date, exit_type
):
    error = validate_exit_position(
        total_open_position, exit_price, exit_quantity, exit_date
    )

    if error:
        error_msg = "\n".join(error)
        set_props("info_dialog", {"is_open": True})
        set_props("info_dialog_text", {"children": error_msg})
        return None

    edate = datetime.fromisoformat(exit_date).date()
    exit_id = insert_exit(
        trade_id=trade_id,
        exit_price=exit_price,
        quantity=exit_quantity,
        exit_date=edate,
        exit_type=exit_type,
    )

    if exit_id is not None:
        logging.debug(f"Exit Position Successful for Trade {trade_id}")
        return exit_id
    else:
        logging.error(f"Exit Position Failed for Trade {trade_id}")
        set_props("info_dialog", {"is_open": True})
        set_props("info_dialog_text", {"children": "Error Exiting Position"})
        return None


def pyramid_position(
    trade_id, entry_price, entry_quantity, entry_date, risk_percentage, stop_loss
):
    error = validate_pyramid_position(
        entry_price, entry_quantity, entry_date, risk_percentage, stop_loss
    )

    if error:
        error_msg = "\n".join(error)
        set_props("info_dialog", {"is_open": True})
        set_props("info_dialog_text", {"children": error_msg})
        return None

    edate = datetime.fromisoformat(entry_date).date()
    entry_id = insert_entry(
        trade_id=trade_id,
        entry_price=entry_price,
        quantity=entry_quantity,
        entry_date=edate,
        entry_type="Pyramid",
        risk_percentage=risk_percentage,
        stop_loss=stop_loss,
    )

    if entry_id is not None:
        logging.debug(f"Pyramid Position Successful for Trade {trade_id}")
        return entry_id
    else:
        logging.error(f"Pyramid Position Failed for Trade {trade_id}")
        set_props("info_dialog", {"is_open": True})
        set_props("info_dialog_text", {"children": "Error Inserting Pyramid Position"})
        return None
