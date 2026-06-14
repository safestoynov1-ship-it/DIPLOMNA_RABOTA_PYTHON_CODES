import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd
import pymssql


# Данни за връзка с Azure SQL Database
DB_SERVER = "ships-diplomna-rabota.database.windows.net"
DB_USER = "dbadmin"
DB_PASSWORD = "@A12222112"
DB_NAME = "Ships"


# Инициализиране на Dash приложението
app = dash.Dash(__name__)
app.title = "Enterprise Система за Анализ на Корабни Данни"


# Зареждане на данните от релационната база и подготовка за визуализация
def get_fleet_data():
    conn = pymssql.connect(server=DB_SERVER, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    query = """
    SELECT 
        s.Ship_Type,
        r.Route_Type,
        r.Distance_Traveled_nm,
        v.Date,
        v.Maintenance_Status,
        pm.Speed_Over_Ground_knots,
        pm.Efficiency_nm_per_kWh,
        pm.Operational_Cost_USD,
        pm.Revenue_per_Voyage_USD
    FROM Voyages v
    JOIN Ships s ON v.ShipID = s.ShipID
    JOIN Routes r ON v.RouteID = r.RouteID
    JOIN PerformanceMetrics pm ON v.VoyageID = pm.VoyageID
    """

    cursor = conn.cursor()
    cursor.execute(query)

    columns = [column[0] for column in cursor.description]
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=columns)

    conn.close()

    # Изчисляване на чистата печалба и форматиране на датата
    df['Net_Profit_USD'] = df['Revenue_per_Voyage_USD'] - df['Operational_Cost_USD']
    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')

    # Конвертиране на числовите колони към float
    numeric_cols = [
        'Distance_Traveled_nm', 'Speed_Over_Ground_knots',
        'Efficiency_nm_per_kWh', 'Operational_Cost_USD',
        'Revenue_per_Voyage_USD', 'Net_Profit_USD'
    ]

    df[numeric_cols] = df[numeric_cols].astype(float)

    return df


# Първоначално зареждане на опциите за филтрите
try:
    init_df = get_fleet_data()
    ship_types = [{'label': i, 'value': i} for i in init_df['Ship_Type'].unique()]
    maintenance_statuses = [{'label': i, 'value': i} for i in init_df['Maintenance_Status'].unique()]
except Exception as e:
    print(f"Грешка при първоначално зареждане: {e}")
    ship_types, maintenance_statuses = [], []


# Основен layout на Dashboard приложението
app.layout = html.Div(style={
    'fontFamily': 'Segoe UI, Arial, sans-serif',
    'backgroundColor': '#f3f4f6',
    'padding': '30px',
    'margin': '0'
}, children=[

    html.Div([
        html.H1("ОБЛАЧНА ПЛАТФОРМА ЗА БИЗНЕС ИНТЕЛЕГЕНТНОСТ И СТАТИСТИЧЕСКИ АНАЛИЗ",
                style={
                    'textAlign': 'center',
                    'color': '#ffffff',
                    'margin': '0',
                    'padding': '20px 0',
                    'fontSize': '24px',
                    'letterSpacing': '1px'
                }),
    ], style={
        'backgroundColor': '#1e3a8a',
        'borderRadius': '12px',
        'marginBottom': '25px',
        'boxShadow': '0 4px 10px rgba(0,0,0,0.1)'
    }),

    html.Div(id='risk-alert-container', style={'marginBottom': '20px'}),

    # Контролен панел с филтри и KPI карти
    html.Div([

        html.Div([
            html.H5("Параметри на филтрация",
                    style={
                        'marginTop': '0',
                        'color': '#1e3a8a',
                        'borderBottom': '2px solid #f3f4f6',
                        'paddingBottom': '10px'
                    }),

            html.Label("Категория плавателен съд:",
                       style={'fontWeight': '600', 'color': '#4b5563', 'fontSize': '13px'}),

            dcc.Dropdown(
                id='ship-type-filter',
                options=ship_types,
                placeholder="Всички категории",
                multi=True,
                style={'marginBottom': '15px', 'marginTop': '5px'}
            ),

            html.Label("Статус на техническо обслужване:",
                       style={'fontWeight': '600', 'color': '#4b5563', 'fontSize': '13px'}),

            dcc.Dropdown(
                id='maintenance-filter',
                options=maintenance_statuses,
                placeholder="Всички статуси",
                multi=True,
                style={'marginTop': '5px'}
            ),

        ], style={
            'width': '25%',
            'display': 'inline-block',
            'backgroundColor': '#ffffff',
            'padding': '20px',
            'borderRadius': '12px',
            'boxShadow': '0 4px 6px rgba(0,0,0,0.05)',
            'verticalAlign': 'top',
            'marginRight': '2%'
        }),

        html.Div([

            html.Div([
                html.H6("РЕНТАБИЛНОСТ (ЧИСТА ПЕЧАЛБА)",
                        style={'margin': '0', 'color': '#6b7280', 'fontSize': '11px', 'letterSpacing': '1px'}),
                html.H2(id='kpi-profit',
                        style={'margin': '10px 0 0 0', 'color': '#10b981', 'fontWeight': 'bold', 'fontSize': '28px'})
            ], style={
                'width': '31%',
                'display': 'inline-block',
                'backgroundColor': '#ffffff',
                'padding': '20px',
                'borderRadius': '12px',
                'boxShadow': '0 4px 6px rgba(0,0,0,0.05)',
                'marginRight': '3.5%'
            }),

            html.Div([
                html.H6("УСРЕДНЕНА ЕФЕКТИВНОСТ",
                        style={'margin': '0', 'color': '#6b7280', 'fontSize': '11px', 'letterSpacing': '1px'}),
                html.H2(id='kpi-efficiency',
                        style={'margin': '10px 0 0 0', 'color': '#3b82f6', 'fontWeight': 'bold', 'fontSize': '28px'})
            ], style={
                'width': '31%',
                'display': 'inline-block',
                'backgroundColor': '#ffffff',
                'padding': '20px',
                'borderRadius': '12px',
                'boxShadow': '0 4px 6px rgba(0,0,0,0.05)',
                'marginRight': '3.5%'
            }),

            html.Div([
                html.H6("ИЗВЪНПЛАНОВИ РЕМОНТИ",
                        style={'margin': '0', 'color': '#6b7280', 'fontSize': '11px', 'letterSpacing': '1px'}),
                html.H2(id='kpi-maintenance',
                        style={'margin': '10px 0 0 0', 'color': '#ef4444', 'fontWeight': 'bold', 'fontSize': '28px'})
            ], style={
                'width': '31%',
                'display': 'inline-block',
                'backgroundColor': '#ffffff',
                'padding': '20px',
                'borderRadius': '12px',
                'boxShadow': '0 4px 6px rgba(0,0,0,0.05)'
            }),

        ], style={'width': '73%', 'display': 'inline-block', 'verticalAlign': 'top'})

    ], style={'marginBottom': '30px'}),

    # Графични визуализации
    html.Div([
        html.Div([dcc.Graph(id='efficiency-scatter-graph')],
                 style={'backgroundColor': '#fff', 'borderRadius': '12px', 'padding': '20px',
                        'boxShadow': '0 4px 6px rgba(0,0,0,0.05)', 'marginBottom': '25px'}),

        html.Div([dcc.Graph(id='financial-bar-graph')],
                 style={'backgroundColor': '#fff', 'borderRadius': '12px', 'padding': '20px',
                        'boxShadow': '0 4px 6px rgba(0,0,0,0.05)', 'marginBottom': '25px'}),

        html.Div([dcc.Graph(id='route-performance-graph')],
                 style={'backgroundColor': '#fff', 'borderRadius': '12px', 'padding': '20px',
                        'boxShadow': '0 4px 6px rgba(0,0,0,0.05)', 'marginBottom': '30px'}),
    ]),

    # Таблична визуализация и експорт на данни
    html.Div([
        html.Div([
            html.H5("Релационен масив от данни (Operational Data Store)",
                    style={'display': 'inline-block', 'margin': '0', 'color': '#1e3a8a', 'fontWeight': '600'}),

            html.Button("Експортиране в Excel / CSV", id="btn_csv", style={
                'float': 'right',
                'backgroundColor': '#10b981',
                'color': '#fff',
                'border': 'none',
                'padding': '8px 15px',
                'borderRadius': '6px',
                'cursor': 'pointer',
                'fontWeight': '600',
                'fontSize': '13px'
            }),

            dcc.Download(id="download-dataframe-csv"),

        ], style={'marginBottom': '15px'}),

        dash_table.DataTable(
            id='data-table',
            columns=[{"name": i.replace('_', ' '), "id": i} for i in init_df.columns if i != 'Net_Profit_USD'],
            page_size=10,
            style_table={'overflowX': 'auto', 'borderRadius': '8px'},
            style_header={'backgroundColor': '#1e3a8a', 'color': 'white',
                          'fontWeight': 'bold', 'textAlign': 'center', 'fontSize': '14px'},
            style_cell={'padding': '12px', 'textAlign': 'center', 'fontSize': '13px',
                        'border': '1px solid #e5e7eb', 'color': '#374151'},
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#f9fafb'}
            ]
        )

    ], style={
        'backgroundColor': '#fff',
        'borderRadius': '12px',
        'padding': '25px',
        'boxShadow': '0 4px 6px rgba(0,0,0,0.05)'
    })

])


# Callback за обновяване на KPI картите, графиките, таблицата и risk alert съобщението
@app.callback(
    [Output('kpi-profit', 'children'),
     Output('kpi-efficiency', 'children'),
     Output('kpi-maintenance', 'children'),
     Output('efficiency-scatter-graph', 'figure'),
     Output('financial-bar-graph', 'figure'),
     Output('route-performance-graph', 'figure'),
     Output('data-table', 'data'),
     Output('risk-alert-container', 'children')],
    [Input('ship-type-filter', 'value'),
     Input('maintenance-filter', 'value')]
)
def update_dashboard(selected_types, selected_maintenances):
    empty_fig = px.scatter(title="Няма налични данни")

    try:
        df = get_fleet_data()
    except Exception as e:
        print(f"Грешка при базата данни: {e}")
        return "$0.00", "0.00 nm/kWh", "0 инцидента", empty_fig, empty_fig, empty_fig, [], None

    # Филтриране на данните според избраните параметри
    if selected_types:
        df = df[df['Ship_Type'].isin(selected_types)]

    if selected_maintenances:
        df = df[df['Maintenance_Status'].isin(selected_maintenances)]

    if df.empty:
        return "$0.00", "0.00 nm/kWh", "0 инцидента", empty_fig, empty_fig, empty_fig, [], None

    # Изчисляване на основните KPI стойности
    total_profit = df['Net_Profit_USD'].sum()
    avg_efficiency = df['Efficiency_nm_per_kWh'].mean()
    unscheduled_repairs = len(df[df['Maintenance_Status'] == 'Unscheduled'])

    kpi_profit_text = f"${total_profit:,.2f}"
    kpi_efficiency_text = f"{avg_efficiency:.2f} nm/kWh"
    kpi_maintenance_text = f"{unscheduled_repairs} инцидента"

    # Проверка за висок оперативен риск
    alert_box = None
    if unscheduled_repairs > 2:
        alert_box = html.Div([
            html.Strong("АЛЕРТ ЗА ОПЕРАТИВЕН РИСК: "),
            f"Засечен е висок брой извънпланови ремонти ({unscheduled_repairs}). Препоръчва се спешна инспекция."
        ], style={
            'backgroundColor': '#ffeeef',
            'color': '#ef4444',
            'border': '1px solid #fca5a5',
            'padding': '15px',
            'borderRadius': '8px',
            'fontWeight': '500',
            'fontSize': '14px'
        })

    # Графика 1: зависимост между скорост и енергийна ефективност
    try:
        fig_efficiency = px.scatter(
            df,
            x="Speed_Over_Ground_knots",
            y="Efficiency_nm_per_kWh",
            color="Ship_Type",
            hover_data=['Route_Type', 'Maintenance_Status'],
            trendline="ols",
            title="Математическо Моделиране на Енергийната Ефективност (Регресионен модел на Пиърсън)",
            labels={
                "Speed_Over_Ground_knots": "Скорост (Възли)",
                "Efficiency_nm_per_kWh": "Ефективност (nm/kWh)"
            }
        )

        fig_efficiency.update_layout(
            xaxis=dict(tickformat=".2f"),
            yaxis=dict(tickformat=".2f"),
            margin=dict(l=20, r=20, t=40, b=20)
        )

    except Exception:
        fig_efficiency = empty_fig

    # Графика 2: сравнение между оперативни разходи и приходи
    try:
        financial_df = df.groupby('Ship_Type')[['Operational_Cost_USD', 'Revenue_per_Voyage_USD']].sum().reset_index()

        financial_df['Operational_Cost_USD'] = financial_df['Operational_Cost_USD'] / 1_000_000
        financial_df['Revenue_per_Voyage_USD'] = financial_df['Revenue_per_Voyage_USD'] / 1_000_000

        financial_melted = pd.melt(
            financial_df,
            id_vars=['Ship_Type'],
            value_vars=['Operational_Cost_USD', 'Revenue_per_Voyage_USD']
        )

        financial_melted['variable'] = financial_melted['variable'].map({
            'Operational_Cost_USD': 'Оперативни разходи',
            'Revenue_per_Voyage_USD': 'Брутни приходи'
        })

        fig_financial = px.bar(
            financial_melted,
            x="Ship_Type",
            y="value",
            color="variable",
            barmode="group",
            title="Икономически баланс: Общи приходи спрямо Оперативни разходи по категории",
            labels={
                "Ship_Type": "Категория",
                "value": "Сума (USD)",
                "variable": "Финансов Показател"
            },
            color_discrete_map={
                'Оперативни разходи': '#ef4444',
                'Брутни приходи': '#3b82f6'
            }
        )

        fig_financial.update_layout(
            yaxis=dict(tickformat=".2f", ticksuffix="M"),
            margin=dict(l=20, r=20, t=40, b=20)
        )

        fig_financial.update_traces(
            hovertemplate="Категория: %{x}<br>Сума: %{y:.2f}M USD"
        )

    except Exception:
        fig_financial = empty_fig

    # Графика 3: чиста печалба по логистични маршрути
    try:
        route_df = df.groupby('Route_Type')['Net_Profit_USD'].sum().reset_index().sort_values(
            by='Net_Profit_USD',
            ascending=False
        )

        route_df['Net_Profit_USD'] = route_df['Net_Profit_USD'] / 1_000_000

        fig_route = px.bar(
            route_df,
            x="Route_Type",
            y="Net_Profit_USD",
            color="Route_Type",
            title="Анализ на Маршрутите: Реализирана Чиста Печалба по Логистични Линии",
            labels={
                "Route_Type": "Логистичен Маршрут",
                "Net_Profit_USD": "Чиста Печалба (USD)"
            }
        )

        fig_route.update_layout(
            yaxis=dict(tickformat=".2f", ticksuffix="M"),
            margin=dict(l=20, r=20, t=40, b=20)
        )

        fig_route.update_traces(
            hovertemplate="Маршрут: %{x}<br>Чиста Печалба: %{y:.2f}M USD"
        )

    except Exception:
        fig_route = empty_fig

    # Подготовка на данните за табличната визуализация
    table_df = df.copy()

    for col in [
        'Distance_Traveled_nm',
        'Speed_Over_Ground_knots',
        'Efficiency_nm_per_kWh',
        'Operational_Cost_USD',
        'Revenue_per_Voyage_USD'
    ]:
        table_df[col] = table_df[col].round(2)

    return (
        kpi_profit_text,
        kpi_efficiency_text,
        kpi_maintenance_text,
        fig_efficiency,
        fig_financial,
        fig_route,
        table_df.to_dict('records'),
        alert_box
    )


# Callback за експорт на филтрираните данни в CSV файл
@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("btn_csv", "n_clicks"),
    [State('ship-type-filter', 'value'),
     State('maintenance-filter', 'value')],
    prevent_initial_call=True
)
def generate_csv(n_clicks, selected_types, selected_maintenances):
    if n_clicks is None:
        return dash.no_update

    df = get_fleet_data()

    if selected_types:
        df = df[df['Ship_Type'].isin(selected_types)]

    if selected_maintenances:
        df = df[df['Maintenance_Status'].isin(selected_maintenances)]

    return dcc.send_data_frame(
        df.to_csv,
        "Fleet_Operational_Analytics.csv",
        index=False
    )


# Обект за стартиране на приложението в production среда
server = app.server


# Локално стартиране на приложението
if __name__ == '__main__':
    app.run(debug=True)
