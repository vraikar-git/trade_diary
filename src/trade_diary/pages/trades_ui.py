from dash import Dash, html, dcc
import dash_ag_grid as dag
import dash_bootstrap_components as dbc


from datetime import  date
from src.trade_diary.db_interface import get_all_financial_years
from src.trade_diary.utility_functions import  extract_financial_year


db_update_store = dcc.Store(id='db-update', data=100)


display_col_def = [
    {'field': 'symbol', 'headerName': 'Symbol'},
    {'field': 'initial_entry_date', 'headerName': 'Trade Date', 
     "cellDataType":"dateString", 
     "filter": "agDateColumnFilter", 
     "filterParams": {
         "buttons":['apply','cancel','clear'],
         "closeOnApply": True,
         "filterOptions" : ['lessThan', 'greaterThan', 'inRange','equals'],
         "maxNumConditions":1,
         "defaultOption":"greaterThan"
         }
     },
    {'field': 'avg_entry_price', 'headerName': 'Avg Entry Price'},
    {'field': 'total_quantity', 'headerName': 'Quantity'},
    {'field': 'total_open_position', 'headerName': 'Open Position'},
    {'field': 'total_risk_percentage', 'headerName': 'Total Risk %'},
    {'field': 'status', 'headerName': 'Status',
      'cellStyle': {
          'styleConditions': [
            {"condition": "params.value === 'Open'", "style": {"color": "#3437e2", "textAlign": "center", "fontWeight": "bold"}},
            {"condition": "params.value === 'Closed'", "style": {"color": "#e72c2c", "textAlign": "center", "fontWeight": "bold"}}
            ]
                    }
                    
    },
    {'field': 'setup', 'headerName': 'Setup'},
    {'field': 'num_entries', 'headerName': 'Number of Entries', 'hide': True},
    {'field': 'num_exits', 'headerName': 'Number of Exits', 'hide': True},
    {'field': 'total_charges', 'headerName': 'Total Charges', 'hide': True},
    {'field': 'total_buy_amount', 'headerName': 'Investment', 'hide': True},
    {'field': 'last_exit_date', 'headerName': 'Last Exit Date', 'hide': True},
    ]

defaultColDef = {"flex" : 1, "headerClass": 'center-aligned-header', "sortable": False }

fy_years = get_all_financial_years()
if not fy_years:
    fy_years = [extract_financial_year(datetime.today())]

side_bar_buttons = dbc.ButtonGroup(
    [
        dbc.Button("Add Position", id='add-position', size='md', n_clicks=0),
        dbc.Button("Exit Position", id='exit-position',  size='md'),
        dbc.Button("Pyramid",  id='pyramid',size='md'),
        dbc.Button("Delete Position", id='delete-position', size='md'),
        dbc.Button("Clear Selection", id='clear-selection', size='md'),
        html.Hr(),
        dcc.Dropdown(id='display_year',
                      value=fy_years[0], options=[{'label': str(y), 'value': y} for y in fy_years], 
                      clearable=False),
        html.Hr(),
        dcc.Checklist(
            [ 
                {
                "label" : html.Span("Show Only Open", style={"font-size": '1rem', "padding-left": 8}),
                "value": "open",
                },
            ],
            value = ['open'],
            id='show-open',
            labelStyle={"display": "flex", "align-items": "left"},
        )
        
    ],
    className="d-grid gap-2",
    vertical=True
)


side_bar = html.Div(
    [
        dbc.Container(side_bar_buttons)
        
    ],
)

entry_row = dbc.Row(
    [
    dbc.Col([
        dbc.Label('Symbol'),
        dbc.Input(
            id='symbol',
            type='text',
            placeholder='Symbol',
            debounce=True,
            required=True
        )
    ]
    ),
    dbc.Col([
        dbc.Label('Entry Price'),
        dbc.Input(
            id='entry-price',
            type='number',
            placeholder='Enter entry price',
            value=0.0,
            debounce=True,
            required=True
        )
    ]
    ),
    dbc.Col([
        dbc.Label('Quantity'),
        dbc.Input(
            id='entry-quantity',
            type='number',
            placeholder='Enter quantity',
            value=0.0,
            debounce=True,
            required=True
        )]
    ),
    dbc.Col([
        dbc.Label('Stop Loss'),
        dbc.Input(
            id='stop-loss',
            type='number',
            placeholder='Enter SL',
            value=0.0,
            debounce=True,
            required=True
        )]
    ),
    dbc.Col([
        dbc.Label('Risk %'),
        dbc.Input(
            id='risk-percentage',
            type='number',
            placeholder='Enter Risk %',
            value=0.0,
            debounce=True,
            required=True
        )]
    ),
    dbc.Col([
        dbc.Label('Entry Date'),
        dcc.DatePickerSingle(
            date=date.today(),
            id='entry-date',
            display_format = 'YYYY-MM-DD',
            style = {'border-radius': '0.375rem'}
            
        )]
    ),
    dbc.Col([
        dbc.Label('Setup'),
        dbc.Input(
            id='setup',
            type='text',
            placeholder='setup',
            debounce=True,
        )]
    ),
    dbc.Col([
        dbc.Label('Entry Type'),
        dbc.Input(
            id='entry-type',
            type='text',
            placeholder='Entry Type',
            debounce=True,
        )]
    ),
    ]
)

entry_dialog = dbc.Modal(
    [
        dbc.ModalHeader("Add Position"),
        dbc.ModalBody(entry_row),
        dbc.ModalFooter(dbc.Button("Submit", id="add-submit", className="ml-auto")),
    ],
    id="add-dialog",
    centered=True, size='xl',
)


exit_row = dbc.Row(
    [

    dbc.Col([
        dbc.Label('Exit Price'),
        dbc.Input(
            id='exit-price',
            type='number',
            placeholder='Enter exit price',
            value=0.0,
            debounce=True,
            required=True
        )
    ]
    ),
    dbc.Col([
        dbc.Label('Quantity'),
        dbc.Input(
            id='exit-quantity',
            type='number',
            placeholder='Enter quantity',
            value=0.0,
            debounce=True,
            required=True
        )]
    ),
    dbc.Col([
        dbc.Label('Exit Date'),
        dcc.DatePickerSingle(
            date=date.today(),
            id='exit-date',
            display_format = 'YYYY-MM-DD',
            style = {'border-radius': '0.375rem'}
            
        )]
    ),
    dbc.Col([
        dbc.Label('Exit Type'),
        dbc.Input(
            id='exit-type',
            type='text',
            placeholder='Exit Type',
            debounce=True,
        )]
    ),
    ]
) 

exit_dialog = dbc.Modal(
    [
        dbc.ModalHeader("Exit Position"),
        dbc.ModalBody(exit_row),
        dbc.ModalFooter(dbc.Button("Submit", id="exit-submit", className="ml-auto")),
    ],
    id="exit-dialog",
    centered=True, size='lg')


pyramid_row = dbc.Row(
    [
    dbc.Col([
        dbc.Label('Entry Price'),
        dbc.Input(
            id='entry-price-pyramid',
            type='number',
            placeholder='Enter entry price',
            value=0.0,
            debounce=True,
            required=True
        )
    ]
    ),
    dbc.Col([
        dbc.Label('Quantity'),
        dbc.Input(
            id='entry-quantity-pyramid',
            type='number',
            placeholder='Enter quantity',
            value=0.0,
            debounce=True,
            required=True
        )]
    ),
    dbc.Col([
        dbc.Label('Stop Loss'),
        dbc.Input(
            id='stop-loss-pyramid',
            type='number',
            placeholder='Enter SL',
            value=0.0,
            debounce=True,
            required=True
        )]
    ),
    dbc.Col([
        dbc.Label('Risk %'),
        dbc.Input(
            id='risk-percentage-pyramid',
            type='number',
            placeholder='Enter Risk %',
            value=0.0,
            debounce=True,
            required=True
        )]
    ),
    dbc.Col([
        dbc.Label('Entry Date'),
        dcc.DatePickerSingle(
            date=date.today(),
            id='entry-date-pyramid',
            display_format = 'YYYY-MM-DD',
            style = {'border-radius': '0.375rem'}
            
        )]
    ),

    dbc.Col([
        dbc.Label('Entry Type'),
        dbc.Input(
            id='entry-type-pyramid',
            type='text',
            placeholder='Entry Type',
            debounce=True,
        )]
    ),
    ]
)


pyramid_dialog = dbc.Modal(
    [
        dbc.ModalHeader("Pyramid Position"),
        dbc.ModalBody(pyramid_row),
        dbc.ModalFooter(dbc.Button("Submit", id="pyramid-submit", className="ml-auto")),
    ],
    id="pyramid-dialog",
    
    centered=True, size='xl')



trade_details = html.Div(
    id='trade-details',
    className='trade-details-style',
    style={'display': 'None'},
)


trades_table = dag.AgGrid(
    id='trades-table',
    columnDefs=display_col_def,
    defaultColDef={
        **defaultColDef,
        "cellStyle": {"textAlign": "center", "justifyContent": "center", "display": "flex", "alignItems": "center"},
    },
    rowModelType='infinite',
    getRowId='params.data.trade_id',
    className="ag-theme-quartz",
    columnSize="responsiveSizeToFit",
    dashGridOptions={
        'rowSelection': 'single',
        'rowBuffer' : 0,
        "animateRows": False,
        # "cacheBlockSize": 12,
        "infiniteInitialRowCount": 1,
        # "pagination": True,
        # "paginationAutoPageSize": True,
    },
)


trade_book = dbc.Container(
    [
        html.H5(id='trade-book-header', style={'textAlign': 'center',  'marginTop': '20px'}),
        html.Hr(),
        trades_table,
        trade_details,
    ],
    className='content_style'
)

info_dialog = dbc.Modal(
    [
        dbc.ModalBody(id="info_dialog_text"),
        dbc.ModalFooter(dbc.Button("Close", id="info_dialog_close", className="ml-auto")),
    ],
    id="info_dialog", centered=True)

del_dialog = dbc.Modal(
    [
        dbc.ModalHeader("Delete Trade"),
        dbc.ModalBody('Delete Confirmation !!!',id="del-confirm"),
        dbc.ModalFooter(dbc.Button("Confirm", id="del-confirm-close", className="ml-auto")),
    ],
    id="del_dialog", centered=True)



def get_trades_details_component(selectedRows):
     return dbc.Container(
         [
             dbc.Row(
                 [
                     dbc.Col(
                            [
                                html.Div("Symbol", className="text-muted small"),
                                html.Div(
                                    selectedRows[0]['symbol'],
                                    className="fw-bold text-primary",
                                    style={"fontSize": "1.1rem"}
                                ),
                            ],
                            width=4,
                            className="text-center"),
                    dbc.Col(
                        [
                            html.Div("No of Days Held", className="text-muted small"),
                            html.Div(
                                selectedRows[0]['days_held'],
                                className="fw-bold text-success",
                                style={"fontSize": "1.1rem"}
                            ),
                        ],
                        width=4,
                        className="text-center"
                    ),
                    dbc.Col(
                        [
                            html.Div("Investment", className="text-muted small"),
                            html.Div(
                                selectedRows[0]['total_buy_amount'],
                                className="fw-bold text-info",
                                style={"fontSize": "1.1rem"}
                            ),
                        ],
                        width=4,
                        className="text-center"
                    ),
                ],
                className="mb-3 justify-content-center align-items-center g-0"
                ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Div("No of Entries", className="text-muted small"),
                            html.Div(
                                selectedRows[0]['num_entries'],
                                className="fw-bold text-warning",
                                style={"fontSize": "1.1rem"}
                            ),
                        ],
                        width=4,
                        className="text-center"
                    ),
                    dbc.Col(
                        [
                            html.Div("No of Exits", className="text-muted small"),
                            html.Div(
                                selectedRows[0]['num_exits'],
                                className="fw-bold text-secondary",
                                style={"fontSize": "1.1rem"}
                            ),
                        ],
                        width=4,
                        className="text-center"
                    ),
                    dbc.Col(
                        [
                            html.Div("Total Charges", className="text-muted small"),
                            html.Div(
                                selectedRows[0]['total_charges'],
                                className="fw-bold text-danger",
                                style={"fontSize": "1.1rem"}
                            ),
                        ],
                        width=4,
                        className="text-center"
                    ),
                ],
                className="mb-2 justify-content-center align-items-center g-0"
            ),
        ],
        fluid=True,
        style={
            'marginBottom': '20px',
            'width': '100%',
            'background': '#f8f9fa',
            'borderRadius': '8px',
            'padding': '16px',
            'boxShadow': '0 2px 8px rgba(0,0,0,0.04)'
        }
    )

def get_entry_details_table(entries):
    theader = [html.Thead(
        html.Tr([
            html.Th("Entry Price"),
            html.Th("Quantity"),
            html.Th("Entry Date"),
            html.Th("Risk %"),
            html.Th("Stop Loss"),
            html.Th("Entry Type")
            ]
            )
        )]
    tbody = [
        html.Tbody([
            html.Tr([
                html.Td(e.entry_price),
                html.Td(e.quantity),
                html.Td(e.entry_date.strftime('%Y-%m-%d')),
                html.Td(e.risk_percentage),
                html.Td(e.stop_loss),
                html.Td(e.entry_type)
            ])
            for e in entries
        ])
    ]
    return dbc.Table(theader + tbody)

def get_exit_details_table(exits):
    theader = [
        html.Thead(
            html.Tr([
            html.Th("Exit Price"),
            html.Th("Quantity"),
            html.Th("Exit Date"),
            html.Th("Exit Type")
            ])
        )
    ]
    tbody = [
        html.Tbody([
            html.Tr([
            html.Td(e.exit_price),
            html.Td(e.quantity),
            html.Td(e.exit_date.strftime('%Y-%m-%d')),
            html.Td(e.exit_type)
            ])
            for e in exits
        ])
    ]
    return dbc.Table(theader + tbody)