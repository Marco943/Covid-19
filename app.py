import pandas as pd
import numpy as np
import glob
import json
from dash import dcc, html, Dash, callback_context
from dash.dependencies import Output, Input
import plotly.graph_objects as go
import plotly.express as px
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
import locale
import pdb
import dash_mantine_components as dmc

# =============== Dados de Covid-19 ================= #
df = pd.concat([pd.read_csv(file, sep=';') for file in glob.glob('data/*.csv')]).drop(columns=['codRegiaoSaude', 'nomeRegiaoSaude', 'interior/metropolitana']).reset_index(drop=True)
df_estados = df[(df['regiao'] != 'Brasil') & (df['municipio'].isna()) & (df['codmun'].isna())].drop(columns=['municipio', 'regiao', 'codmun', 'coduf'])
df_estados['data'] = pd.to_datetime(df_estados['data'], format='%Y-%m-%d')

df_brasil = df[df['regiao'] == 'Brasil']
df_brasil['data'] = pd.to_datetime(df_brasil['data'], format='%Y-%m-%d')

# =============== Dados de GeoJSON =================== #
with open('data/Brasil_UF_geojson.json', 'r') as f:
    uf_json = json.load(f)

# ======================= App ======================== #
locale.setlocale(locale.LC_ALL, '')
app = Dash(__name__, external_stylesheets=[dbc.themes.ZEPHYR])
server = app.server
load_figure_template('zephyr')

# =================== Layout ========================= #
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Img(id='logo', src=app.get_asset_url('logo_escura.svg'), height=50),
                html.H5('Dashboard de Covid-19'),
                dbc.Button('BRASIL', color='primary', id='botao-estado', size='lg')
            ], style={'padding': 20, 'background-color': '#F6F6F6', 'border-radius': 10, 'margin': 10}),
            html.Div([
                html.P('Informe a data na qual deseja obter informações:'),
                dmc.DatePicker(
                    id='calendario',
                    minDate=df_estados['data'].min(), maxDate=df_estados['data'].max(),
                    value='2022-09-01', locale='pt-br', inputFormat='DD/MM/YYYY', clearable=False
                )
            ], style={'padding': 20, 'background-color': '#F6F6F6', 'border-radius': 10, 'margin': 10}),
            dbc.Row(id='cartoes', children=[
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Span('Casos recuperados'),
                            html.H3(id='casos-recuperados-text'),
                            html.Span('Em acompanhamento'),
                            html.H3(id='casos-acompanhamento-text')
                        ])
                    ])
                ], md=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Span('Casos confirmados'),
                            html.H3(id='casos-confirmados-text'),
                            html.Span('Novos casos na data'),
                            html.H3(id='casos-data-text')
                        ])
                    ])
                ], md=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Span('Óbitos totais'),
                            html.H3(id='obitos-text'),
                            html.Span('Novos óbitos na data'),
                            html.H3(id='obitos-data-text')
                        ])
                    ])
                ], md=4)
            ], style={'margin': 10}),
            html.Div([
                html.P('Selecione o tipo de dado que deseja visualizar'),
                dcc.Dropdown(
                    options = [{'label': i, 'value': j} for i, j in {'Novos casos': 'casosNovos', 'Casos Acumulados': 'casosAcumulado', 'Novos óbitos': 'obitosNovos', 'Óbitos Acumulados': 'obitosAcumulado'}.items()],
                    value='casosAcumulado', clearable=False,
                    id='metrica', 
                )                
            ], style={'padding': 20, 'background-color': '#F6F6F6', 'border-radius': 10, 'margin': 10}),
            html.Div([
                dcc.Loading(id='loading-1', type='default', children=[
                    dcc.Graph(id='historico', style={'height': 300}, config={'locale':'pt-br', 'displaylogo': False})
                ])
            ])
        ], width=5),
        dbc.Col([
            dcc.Loading(id='loading-2', type='default', children=[
                dcc.Graph(id='mapa', style={'height': '100vh'}, config={'locale':'pt-br', 'displaylogo': False})
            ]),
        ], width=7)
    ], className='g-0')
], fluid=True)

# ==================== Callbacks ===================== #
@app.callback(
    Output('mapa', 'figure'),
    Output('historico','figure'),
    Output('casos-recuperados-text','children'),
    Output('casos-acompanhamento-text','children'),
    Output('casos-confirmados-text','children'),
    Output('casos-data-text','children'),
    Output('obitos-text','children'),
    Output('obitos-data-text','children'),
    Input('calendario', 'value'),
    Input('metrica', 'value'),
    Input('botao-estado', 'children')
)
def update(data, metrica, local):
    fig_mapa = px.choropleth(
        data_frame = df_estados[df_estados['data'] == data], locations='estado', color=metrica,
        geojson=uf_json, featureidkey='properties.UF_05',
        custom_data=['casosAcumulado','casosNovos','obitosNovos','obitosAcumulado','data'],
    )
    fig_mapa.update_traces(
        hovertemplate="""<b>%{location} (%{customdata[4]|%d/%m/%Y})</b><extra></extra>
                        <br>Casos Acumulados: %{customdata[0]:,.0f}
                        <br>Casos Novos: %{customdata[1]:,.0f}
                        <br>Óbitos Acumulados: %{customdata[3]:,.0f}
                        <br>Óbitos Novos: %{customdata[2]:,.0f}"""
    )
    fig_mapa.update_geos(fitbounds='geojson', projection_scale=4)
    fig_mapa.update_layout(
        autosize=True,
        showlegend=False,
        geo_scope='south america',
        separators=',.',
        coloraxis_colorbar_title_text = {'casosNovos': 'Casos Novos', 'casosAcumulado': 'Casos Acumulados', 'obitosNovos': 'Óbitos Novos', 'obitosAcumulado': 'Óbitos Acumulados'}.get(metrica)
    )

    if local == 'BRASIL':
        df_data_local = df_brasil.copy()
    else:
        df_data_local = df_estados[df_estados['estado'] == local]

    if 'Acumulado' in metrica:
        fig_historico = px.line(data_frame=df_data_local, x='data', y=metrica)
    else:
        fig_historico = px.bar(data_frame=df_data_local, x='data', y=metrica)

    if local == 'BRASIL':
        df_data_date = df_brasil[df_brasil['data'] == data]
    else:
        df_data_date = df_estados[(df_estados['data'] == data) & (df_estados['estado'] == local)]
    
    fig_historico.update_layout(
        yaxis_title={'casosNovos': 'Casos Novos', 'casosAcumulado': 'Casos Acumulados', 'obitosNovos': 'Óbitos Novos', 'obitosAcumulado': 'Óbitos Acumulados'}.get(metrica),
        xaxis_title='Data',
        separators=',.'
    )
    fig_historico.update_traces(
        hovertemplate = '%{x|%d/%m/%Y}<br><b>%{yaxis.title.text}</b>: %{y:,.0f}'
    )
    recuperados_novos = locale.format_string('%.0f', df_data_date['Recuperadosnovos'].fillna('-').values[0], grouping=True) if local == 'BRASIL' else '-'
    acompanhamento = locale.format_string('%.0f', df_data_date['emAcompanhamentoNovos'].fillna('-').values[0], grouping=True) if local == 'BRASIL' else '-'
    confirmados = locale.format_string('%.0f', df_data_date['casosAcumulado'].values[0], grouping=True)
    confirmados_novos = locale.format_string('%.0f', df_data_date['casosNovos'].values[0], grouping=True)
    obitos = locale.format_string('%.0f', df_data_date['obitosAcumulado'].values[0], grouping=True)
    obitos_novos = locale.format_string('%.0f', df_data_date['obitosNovos'].values[0], grouping=True)
    
    return fig_mapa, fig_historico, recuperados_novos, acompanhamento, confirmados, confirmados_novos, obitos, obitos_novos

@app.callback([
    Output('botao-estado', 'children'),
    Input('mapa', 'clickData'),
    Input('botao-estado', 'n_clicks')
])
def update_botao(click_data, n_clicks):
    changed_id = [p['prop_id'] for p in callback_context.triggered][0]
    if click_data is not None and changed_id != 'botao-estado.n_clicks':
        estado = click_data['points'][0]['location']
        return [f'{estado}']
    else:
        return ['BRASIL']

if __name__ == '__main__':
    app.run_server(debug=False)