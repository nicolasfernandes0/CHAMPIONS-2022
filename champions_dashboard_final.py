import streamlit as st
import pandas as pd
import numpy as np
import json
import http.client
from datetime import datetime
from typing import Dict, Optional
import altair as alt  # Alternativa leve para gráficos

# Configuração da página
st.set_page_config(
    page_title="UEFA Champions League 2022/23 Dashboard",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurações da API
API_KEY = "a6dc4855d9832ff4404f314aa3045bd1"
API_HOST = "v3.football.api-sports.io"
LEAGUE_ID = 2  # UEFA Champions League
SEASON = 2022

# Função para buscar dados da API
@st.cache_data(persist=True)
def fetch_all_data():
    """Busca todos os dados da API uma única vez"""
    try:
        conn = http.client.HTTPSConnection(API_HOST)
        headers = {'x-apisports-key': API_KEY}
        
        # Buscar todas as partidas da temporada
        endpoint = f"/fixtures?league={LEAGUE_ID}&season={SEASON}"
        conn.request("GET", endpoint, headers=headers)
        res = conn.getresponse()
        
        if res.status == 200:
            data = json.loads(res.read().decode("utf-8"))
            return data
        else:
            st.error(f"Erro na API: Status {res.status}")
            return None
            
    except Exception as e:
        st.error(f"Erro na conexão: {str(e)}")
        return None

# Função para processar os dados
def process_data(raw_data):
    """Processa os dados brutos da API"""
    if not raw_data or 'response' not in raw_data:
        return None
    
    matches = []
    teams = {}
    
    for match in raw_data['response']:
        try:
            # Informações básicas
            match_info = {
                'id': match['fixture']['id'],
                'date': match['fixture']['date'],
                'timestamp': match['fixture']['timestamp'],
                'status': match['fixture']['status']['short'],
                'round': match['league']['round'],
                'stage': match['league']['round'].split(' - ')[0] if ' - ' in match['league']['round'] else match['league']['round'],
                'venue': match['fixture']['venue']['name'] if match['fixture']['venue'] else 'Unknown',
                
                # Times
                'home_team': match['teams']['home']['name'],
                'away_team': match['teams']['away']['name'],
                
                # Placar
                'home_goals': match['goals']['home'],
                'away_goals': match['goals']['away'],
                'total_goals': match['goals']['home'] + match['goals']['away'],
                
                # Resultado
                'home_winner': match['teams']['home']['winner'],
                'away_winner': match['teams']['away']['winner'],
                'winner': match['teams']['home']['name'] if match['teams']['home']['winner'] 
                         else match['teams']['away']['name'] if match['teams']['away']['winner'] 
                         else 'Draw'
            }
            
            matches.append(match_info)
            
            # Atualizar estatísticas dos times
            for team_type in ['home', 'away']:
                team = match['teams'][team_type]
                if team['name'] not in teams:
                    teams[team['name']] = {
                        'games': 0, 'wins': 0, 'draws': 0, 'losses': 0,
                        'goals_for': 0, 'goals_against': 0
                    }
                
                teams[team['name']]['games'] += 1
                teams[team['name']]['goals_for'] += match['goals'][team_type]
                teams[team['name']]['goals_against'] += match['goals']['away' if team_type == 'home' else 'home']
                
                if team['winner']:
                    teams[team['name']]['wins'] += 1
                elif match['teams']['home']['winner'] is None and match['teams']['away']['winner'] is None:
                    teams[team['name']]['draws'] += 1
                else:
                    teams[team['name']]['losses'] += 1
                    
        except Exception:
            continue
    
    # Converter para DataFrame
    matches_df = pd.DataFrame(matches)
    if not matches_df.empty:
        matches_df['date'] = pd.to_datetime(matches_df['date'])
        matches_df['date_str'] = matches_df['date'].dt.strftime('%d/%m/%Y %H:%M')
        matches_df['month'] = matches_df['date'].dt.month_name()
    
    # Converter estatísticas dos times para DataFrame
    teams_stats = []
    for team_name, stats in teams.items():
        stats['team'] = team_name
        stats['goal_diff'] = stats['goals_for'] - stats['goals_against']
        stats['points'] = stats['wins'] * 3 + stats['draws']
        stats['win_rate'] = (stats['wins'] / stats['games'] * 100) if stats['games'] > 0 else 0
        teams_stats.append(stats)
    
    teams_df = pd.DataFrame(teams_stats)
    
    return {
        'matches': matches_df,
        'teams': teams_df
    }

# Título do Dashboard
st.title("⚽ UEFA Champions League 2022/23")
st.markdown("### Dashboard Completo da Temporada")
st.markdown("---")

# Inicializar estado da sessão
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
    st.session_state.processed_data = None

# Sidebar - Carregamento de dados
st.sidebar.header("⚙️ Configurações")

if not st.session_state.data_loaded:
    if st.sidebar.button("📥 Carregar Dados da API", type="primary", use_container_width=True):
        with st.spinner("🔄 Buscando dados da UEFA Champions League..."):
            raw_data = fetch_all_data()
            
            if raw_data:
                processed_data = process_data(raw_data)
                if processed_data:
                    st.session_state.processed_data = processed_data
                    st.session_state.data_loaded = True
                    st.success("✅ Dados carregados com sucesso!")
                    st.rerun()
                else:
                    st.error("❌ Erro ao processar os dados")
            else:
                st.error("❌ Falha ao carregar dados da API")
    
    # Tela inicial sem dados
    st.info("""
    ## 🏆 Bem-vindo ao Dashboard da UEFA Champions League 2022/23!
    
    **Para começar:**
    1. Clique em **"Carregar Dados da API"** na barra lateral
    2. Aguarde o carregamento (apenas uma vez)
    3. Explore as estatísticas da temporada completa
    
    **Dados incluídos:**
    - Todas as partidas da temporada 2022/23
    - Estatísticas por time
    - Análises e métricas detalhadas
    - Tabelas e gráficos interativos
    """)
    
    # Placeholder para visualizações
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 Métricas Principais")
        st.write("As métricas serão exibidas aqui após o carregamento")
    with col2:
        st.subheader("🏆 Classificação")
        st.write("A tabela de classificação aparecerá aqui")
    
    st.stop()

# Se chegou aqui, os dados estão carregados
processed_data = st.session_state.processed_data
matches_df = processed_data['matches']
teams_df = processed_data['teams']

# Informações na sidebar
st.sidebar.success("✅ Dados carregados")
st.sidebar.metric("Total de Partidas", len(matches_df))
st.sidebar.metric("Times Participantes", len(teams_df))
st.sidebar.metric("Total de Gols", matches_df['total_goals'].sum())

# Filtros na sidebar
st.sidebar.header("🔍 Filtros")

# Filtro por fase
phases = sorted(matches_df['stage'].unique())
selected_phases = st.sidebar.multiselect(
    "Fase da Competição",
    phases,
    default=phases[:5] if len(phases) > 5 else phases
)

# Filtro por resultado
result_filter = st.sidebar.selectbox(
    "Resultado",
    ["Todos", "Vitória Casa", "Vitória Fora", "Empate"]
)

# Aplicar filtros
filtered_matches = matches_df.copy()

if selected_phases:
    filtered_matches = filtered_matches[filtered_matches['stage'].isin(selected_phases)]

if result_filter == "Vitória Casa":
    filtered_matches = filtered_matches[filtered_matches['home_winner'] == True]
elif result_filter == "Vitória Fora":
    filtered_matches = filtered_matches[filtered_matches['away_winner'] == True]
elif result_filter == "Empate":
    filtered_matches = filtered_matches[filtered_matches['winner'] == 'Draw']

# Métricas principais
st.header("📊 Visão Geral da Temporada")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Partidas", len(filtered_matches))

with col2:
    st.metric("Total de Gols", filtered_matches['total_goals'].sum())

with col3:
    avg_goals = filtered_matches['total_goals'].mean()
    st.metric("Média Gols/Partida", f"{avg_goals:.2f}")

with col4:
    home_wins = len(filtered_matches[filtered_matches['home_winner'] == True])
    home_win_rate = (home_wins / len(filtered_matches) * 100) if len(filtered_matches) > 0 else 0
    st.metric("Vitórias em Casa", f"{home_wins} ({home_win_rate:.1f}%)")

st.markdown("---")

# Abas principais
tab1, tab2, tab3 = st.tabs(["📈 Estatísticas", "🏆 Times", "⚽ Partidas"])

with tab1:
    st.subheader("📈 Estatísticas da Temporada")
    
    # Distribuição de resultados
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Distribuição de Resultados")
        results = filtered_matches['winner'].value_counts()
        
        # Formatar resultados
        results_display = pd.DataFrame({
            'Resultado': results.index,
            'Quantidade': results.values,
            'Porcentagem': (results.values / len(filtered_matches) * 100).round(1)
        })
        
        # Renomear para melhor visualização
        def format_result(result):
            if result == 'Draw':
                return 'Empate'
            elif len(result.split()) > 1:
                return f"Vitória {result.split()[-1]}"
            else:
                return f"Vitória {result}"
        
        results_display['Resultado'] = results_display['Resultado'].apply(format_result)
        st.dataframe(results_display, use_container_width=True, hide_index=True)
    
    with col2:
        st.subheader("Gols por Fase")
        goals_by_stage = filtered_matches.groupby('stage').agg({
            'total_goals': 'sum',
            'id': 'count'
        }).rename(columns={'id': 'partidas'}).reset_index()
        
        goals_by_stage = goals_by_stage.sort_values('total_goals', ascending=False)
        st.dataframe(goals_by_stage, use_container_width=True, hide_index=True)
    
    # Histograma de gols (usando Altair)
    st.subheader("Distribuição de Gols por Partida")
    
    if not filtered_matches.empty:
        # Criar histograma com Altair
        hist_data = filtered_matches['total_goals'].value_counts().reset_index()
        hist_data.columns = ['Gols', 'Partidas']
        hist_data = hist_data.sort_values('Gols')
        
        chart = alt.Chart(hist_data).mark_bar().encode(
            x=alt.X('Gols:O', title='Total de Gols'),
            y=alt.Y('Partidas:Q', title='Número de Partidas'),
            tooltip=['Gols', 'Partidas']
        ).properties(
            height=300
        )
        
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Nenhuma partida encontrada com os filtros aplicados")

with tab2:
    st.subheader("🏆 Estatísticas por Time")
    
    # Ordenar times
    sort_option = st.selectbox(
        "Ordenar times por:",
        ["Pontos", "Vitórias", "Gols Pró", "Saldo de Gols", "Aproveitamento"]
    )
    
    if sort_option == "Pontos":
        sorted_teams = teams_df.sort_values('points', ascending=False)
    elif sort_option == "Vitórias":
        sorted_teams = teams_df.sort_values('wins', ascending=False)
    elif sort_option == "Gols Pró":
        sorted_teams = teams_df.sort_values('goals_for', ascending=False)
    elif sort_option == "Saldo de Gols":
        sorted_teams = teams_df.sort_values('goal_diff', ascending=False)
    else:  # Aproveitamento
        sorted_teams = teams_df.sort_values('win_rate', ascending=False)
    
    # Mostrar tabela de times
    display_columns = ['team', 'games', 'wins', 'draws', 'losses', 
                      'goals_for', 'goals_against', 'goal_diff', 'points', 'win_rate']
    
    display_df = sorted_teams[display_columns].copy()
    display_df.columns = ['Time', 'J', 'V', 'E', 'D', 'GP', 'GC', 'SG', 'Pts', 'Aproveitamento']
    display_df['Aproveitamento'] = display_df['Aproveitamento'].round(1).astype(str) + '%'
    
    # Aplicar estilo à tabela
def highlight_rows(row):
    # Cores mais suaves e modernas
    high_color = 'background-color: #e8f5e9'  # Verde muito claro
    low_color = 'background-color: #ffebee'   # Vermelho muito claro
    default = ''
    
    # Condições para destacar
    if row['Pts'] >= sorted_teams['points'].quantile(0.75):
        return [high_color] * len(row)
    elif row['Pts'] <= sorted_teams['points'].quantile(0.25):
        return [low_color] * len(row)
    return [default] * len(row)
    
    styled_df = display_df.head(20).style.apply(highlight_rows, axis=1)
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # Top 5 times em diferentes categorias
    st.subheader("🎯 Líderes em Categorias")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**Top 5 - Pontos**")
        top_points = sorted_teams[['team', 'points']].head(5)
        for idx, row in top_points.iterrows():
            st.write(f"{row['team']}: {row['points']} pts")
    
    with col2:
        st.write("**Top 5 - Gols Pró**")
        top_goals = teams_df.sort_values('goals_for', ascending=False)[['team', 'goals_for']].head(5)
        for idx, row in top_goals.iterrows():
            st.write(f"{row['team']}: {row['goals_for']} gols")
    
    with col3:
        st.write("**Top 5 - Aproveitamento**")
        top_win_rate = teams_df[teams_df['games'] >= 3].sort_values('win_rate', ascending=False)[['team', 'win_rate']].head(5)
        for idx, row in top_win_rate.iterrows():
            st.write(f"{row['team']}: {row['win_rate']:.1f}%")

with tab3:
    st.subheader("⚽ Partidas da Temporada")
    
    # Filtros adicionais para partidas
    col_search, col_sort = st.columns(2)
    
    with col_search:
        search_term = st.text_input("🔍 Buscar por time:", "")
    
    with col_sort:
        sort_by = st.selectbox(
            "Ordenar por:",
            ["Data (Mais Recente)", "Data (Mais Antigo)", "Mais Gols", "Menos Gols"]
        )
    
    # Aplicar filtro de busca
    if search_term:
        search_matches = filtered_matches[
            (filtered_matches['home_team'].str.contains(search_term, case=False)) |
            (filtered_matches['away_team'].str.contains(search_term, case=False))
        ]
    else:
        search_matches = filtered_matches
    
    # Aplicar ordenação
    if sort_by == "Data (Mais Recente)":
        sorted_matches = search_matches.sort_values('timestamp', ascending=False)
    elif sort_by == "Data (Mais Antigo)":
        sorted_matches = search_matches.sort_values('timestamp', ascending=True)
    elif sort_by == "Mais Gols":
        sorted_matches = search_matches.sort_values('total_goals', ascending=False)
    else:  # Menos Gols
        sorted_matches = search_matches.sort_values('total_goals', ascending=True)
    
    # Mostrar partidas
    matches_to_show = st.slider("Número de partidas para mostrar:", 5, 50, 20)
    
    for idx, match in sorted_matches.head(matches_to_show).iterrows():
        # Determinar estilo baseado no resultado
        if match['home_winner']:
            home_style = "color: green; font-weight: bold"
            away_style = "color: red"
        elif match['away_winner']:
            home_style = "color: red"
            away_style = "color: green; font-weight: bold"
        else:
            home_style = away_style = "color: orange"
        
        # Criar container para cada partida
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 3])
            
            with col1:
                st.markdown(f"<span style='{home_style}'>{match['home_team']}</span>", unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"**{match['home_goals']} - {match['away_goals']}**")
                st.caption(match['date_str'])
            
            with col3:
                st.markdown(f"<span style='{away_style}'>{match['away_team']}</span>", unsafe_allow_html=True)
            
            # Informações adicionais
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.caption(f"📋 {match['round']}")
            with col_info2:
                st.caption(f"🏟️ {match['venue']}")
            
            st.divider()

# Seção de análises adicionais
st.markdown("---")
st.header("📊 Análises Adicionais")

col_anal1, col_anal2 = st.columns(2)

with col_anal1:
    st.subheader("Distribuição por Mês")
    if 'month' in filtered_matches.columns:
        monthly_stats = filtered_matches.groupby('month').agg({
            'id': 'count',
            'total_goals': 'sum'
        }).rename(columns={'id': 'partidas'}).reset_index()
        
        monthly_stats = monthly_stats.sort_values('partidas', ascending=False)
        st.dataframe(monthly_stats, use_container_width=True, hide_index=True)

with col_anal2:
    st.subheader("Partidas com Mais Gols")
    high_scoring = filtered_matches.nlargest(5, 'total_goals')[['home_team', 'away_team', 'home_goals', 'away_goals', 'total_goals', 'round']]
    
    for idx, match in high_scoring.iterrows():
        st.write(f"{match['home_team']} {match['home_goals']}-{match['away_goals']} {match['away_team']} ({match['total_goals']} gols) - {match['round']}")

# Exportar dados
st.sidebar.markdown("---")
st.sidebar.header("📥 Exportar Dados")

if st.sidebar.button("💾 Exportar para CSV", use_container_width=True):
    csv_data = matches_df.to_csv(index=False)
    
    st.sidebar.download_button(
        label="Baixar Partidas",
        data=csv_data,
        file_name="uefa_cl_matches_2022_23.csv",
        mime="text/csv"
    )

# Informações finais
st.sidebar.markdown("---")
st.sidebar.markdown("""
### ℹ️ Informações
- **Temporada:** 2022/23
- **Competição:** UEFA Champions League
- **Fonte:** API-Football
- **Carregamento:** Único
- **Atualização:** Manual
""")

# Rodapé
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>Dashboard desenvolvido com Streamlit • Dados via API-Football</p>
        <p>UEFA Champions League 2022/23 • Todos os direitos reservados</p>
    </div>
    """,
    unsafe_allow_html=True
)

