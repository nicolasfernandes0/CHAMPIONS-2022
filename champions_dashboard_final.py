import streamlit as st
import pandas as pd
import json
import http.client

# Configuração básica
st.set_page_config(
    page_title="UEFA Champions League Dashboard",
    page_icon="⚽",
    layout="wide"
)

# API Configuration
API_KEY = "a6dc4855d9832ff4404f314aa3045bd1"
API_HOST = "v3.football.api-sports.io"

# Função para buscar dados
@st.cache_data(persist=True)
def get_data():
    try:
        conn = http.client.HTTPSConnection(API_HOST)
        headers = {'x-apisports-key': API_KEY}
        conn.request("GET", "/fixtures?league=2&season=2022", headers=headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        return data
    except:
        return None

# Título
st.title("⚽ UEFA Champions League 2022/23")
st.markdown("---")

# Botão para carregar dados
if 'data' not in st.session_state:
    st.session_state.data = None

if st.button("📥 Carregar Dados", type="primary"):
    with st.spinner("Buscando dados..."):
        st.session_state.data = get_data()
        if st.session_state.data:
            st.success("Dados carregados!")
        else:
            st.error("Erro ao carregar dados")

# Se temos dados, mostrar dashboard
if st.session_state.data and 'response' in st.session_state.data:
    data = st.session_state.data
    
    # Processar dados
    matches = []
    for match in data['response']:
        matches.append({
            'Data': match['fixture']['date'][:10],
            'Hora': match['fixture']['date'][11:16],
            'Rodada': match['league']['round'],
            'Casa': match['teams']['home']['name'],
            'Visitante': match['teams']['away']['name'],
            'Gols Casa': match['goals']['home'],
            'Gols Visitante': match['goals']['away'],
            'Vencedor': match['teams']['home']['name'] if match['teams']['home']['winner'] 
                     else match['teams']['away']['name'] if match['teams']['away']['winner'] 
                     else 'Empate',
            'Estádio': match['fixture']['venue']['name'] if match['fixture']['venue'] else 'N/A'
        })
    
    df = pd.DataFrame(matches)
    
    # Métricas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Partidas", len(df))
    with col2:
        total_goals = df['Gols Casa'].sum() + df['Gols Visitante'].sum()
        st.metric("Total de Gols", total_goals)
    with col3:
        avg_goals = total_goals / len(df) if len(df) > 0 else 0
        st.metric("Média de Gols", f"{avg_goals:.2f}")
    
    st.markdown("---")
    
    # Filtros
    st.sidebar.header("🔍 Filtros")
    
    # Filtro por time
    all_teams = sorted(set(df['Casa'].unique()) | set(df['Visitante'].unique()))
    selected_team = st.sidebar.selectbox("Selecionar Time", ["Todos"] + all_teams)
    
    # Filtro por rodada
    all_rounds = sorted(df['Rodada'].unique())
    selected_rounds = st.sidebar.multiselect("Rodadas", all_rounds, default=all_rounds[:3])
    
    # Aplicar filtros
    filtered_df = df.copy()
    if selected_team != "Todos":
        filtered_df = filtered_df[(filtered_df['Casa'] == selected_team) | (filtered_df['Visitante'] == selected_team)]
    if selected_rounds:
        filtered_df = filtered_df[filtered_df['Rodada'].isin(selected_rounds)]
    
    # Estatísticas básicas
    st.header("📊 Estatísticas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Resultados")
        results = filtered_df['Vencedor'].value_counts()
        st.write(f"Vitórias da Casa: {len(filtered_df[filtered_df['Vencedor'] == filtered_df['Casa']])}")
        st.write(f"Vitórias do Visitante: {len(filtered_df[filtered_df['Vencedor'] == filtered_df['Visitante']])}")
        st.write(f"Empates: {len(filtered_df[filtered_df['Vencedor'] == 'Empate'])}")
    
    with col2:
        st.subheader("Partidas por Rodada")
        matches_per_round = filtered_df['Rodada'].value_counts()
        for round_name, count in matches_per_round.head(10).items():
            st.write(f"{round_name}: {count} partidas")
    
    # Tabela de partidas
    st.header("📅 Partidas")
    
    # Ordenar
    sort_option = st.selectbox("Ordenar por:", ["Data", "Rodada", "Mais Gols"])
    if sort_option == "Data":
        display_df = filtered_df.sort_values(['Data', 'Hora'], ascending=[False, False])
    elif sort_option == "Rodada":
        display_df = filtered_df.sort_values('Rodada')
    else:  # Mais Gols
        display_df = filtered_df.copy()
        display_df['Total Gols'] = display_df['Gols Casa'] + display_df['Gols Visitante']
        display_df = display_df.sort_values('Total Gols', ascending=False)
    
    st.dataframe(display_df, use_container_width=True, height=400)
    
    # Times participantes
    st.header("🏆 Times Participantes")
    st.write(f"Total de times: {len(all_teams)}")
    
    # Mostrar times em colunas
    cols = st.columns(4)
    for idx, team in enumerate(sorted(all_teams)):
        col_idx = idx % 4
        with cols[col_idx]:
            st.write(f"• {team}")

else:
    # Tela inicial
    st.info("""
    ## Bem-vindo ao Dashboard da UEFA Champions League!
    
    Clique em **"Carregar Dados"** para buscar as informações da temporada 2022/23.
    
    Este dashboard mostrará:
    - Todas as partidas da temporada
    - Estatísticas gerais
    - Times participantes
    - Resultados e classificações
    """)

# Rodapé
st.markdown("---")
st.markdown("*Dashboard criado com Streamlit • Dados via API-Football*")
