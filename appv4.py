import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. Configuração da Página
st.set_page_config(
    page_title="Redutores - Análise de Consulta vs Projeto", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main {background-color: #FAFAFA;}
    h1, h2, h3 {color: #2C3E50; font-family: 'Arial', sans-serif;}
    .stMetric {background-color: #FFFFFF; padding: 15px; border-radius: 5px; border: 1px solid #EAEAEA;}
    </style>
    """, unsafe_allow_html=True)

st.title("Otimização da Estimativa de Vazão de óleo para Redutores")
st.write("Análise de desvios térmicos e de vazão entre as fases de proposta (consulta) e projeto.")

# 2. Função de Leitura (Ignora espaços extras nos nomes das abas)
@st.cache_data
def load_all_sheets(file):
    if file is not None:
        try:
            xls = pd.ExcelFile(file)
            sheet_map = {s.strip().lower(): s for s in xls.sheet_names}
            
            def get_sheet(match_name):
                for k, v in sheet_map.items():
                    if match_name in k:
                        return pd.read_excel(xls, sheet_name=v)
                return pd.DataFrame()
                
            df_dados = get_sheet('dados')
            df_var = get_sheet('varia')
            df_res = get_sheet('resumo')
            df_eff = get_sheet('efici')
            df_pot = get_sheet('pot')
            
            return df_dados, df_var, df_res, df_eff, df_pot, xls.sheet_names
        except Exception as e:
            st.error(f"Erro crítico ao ler o Excel: {e}")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), []
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), []

st.sidebar.header("📁 Upload do Arquivo")
st.sidebar.write("Insira a planilha atualizada do estudo (.xlsx)")
uploaded_file = st.sidebar.file_uploader("Carregar Planilha (.xlsx)", type=["xlsx"])

df, df_var, df_res, df_eff, df_pot, todas_abas = load_all_sheets(uploaded_file)

if df.empty:
    st.warning("⚠️ Aguardando o upload do arquivo Excel (.xlsx) contendo a aba 'Dados'.")
else:
    # Tratamento dos Dados Principais
    df = df.dropna(subset=['VAZÃO PROJETO [l/min]', 'VAZÃO PROPOSTA [l/min]', 'REDUTOR'])
    df['Delta Vazão'] = df['VAZÃO PROPOSTA [l/min]'] - df['VAZÃO PROJETO [l/min]']
    df['K_dissipacao'] = df['VAZÃO PROJETO [l/min]'] / df['VAZÃO PROPOSTA [l/min]']

    # 3. Estrutura de Abas
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Visão Geral (Dados)", 
        "📋 Resumo", 
        "📈 Eficiência de Consulta",
        "⚡ Curvas de Potência",
        "🧮 Calculadora"
    ])

    # ==========================================
    # ABA 1: VISÃO GERAL
    # ==========================================
    with tab1:
        st.header("Comportamento Geral das Consultas")
        c1, c2, c3 = st.columns(3)
        c1.metric("Projetos Analisados", len(df))
        super_qtd = len(df[df['Delta Vazão'] > 0])
        c2.metric("Casos Superdimensionados", f"{super_qtd} ({ (super_qtd/len(df))*100:.1f}%)")
        c3.metric("Superdimensionamento Médio (Vazão)", f"+{df['Delta Vazão'].mean():.1f} L/min")
        
        st.divider()
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            fig1 = px.scatter(
                df, x='VAZÃO PROJETO [l/min]', y='VAZÃO PROPOSTA [l/min]', color='REDUTOR',
                hover_data=['ELEMENTO PEP'], opacity=0.7, title="Dispersão de Vazão: Projeto vs. Consulta"
            )
            max_v = max(df['VAZÃO PROJETO [l/min]'].max(), df['VAZÃO PROPOSTA [l/min]'].max())
            fig1.add_trace(go.Scatter(x=[0, max_v], y=[0, max_v], mode='lines', name='Ideal', line=dict(color='red', dash='dash')))
            fig1.update_layout(plot_bgcolor='white')
            st.plotly_chart(fig1, use_container_width=True)
            
        with col_g2:
            fig2 = px.box(
                df, x='REDUTOR', y='Delta Vazão', color='REDUTOR', title="Erro de vazão (Consulta - Projeto) por modelo de Redutor"
            )
            fig2.add_hline(y=0, line_dash="dash", line_color="red")
            fig2.update_layout(plot_bgcolor='white', showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)


     # ==========================================
    # ABA 2: RESUMO
    # ==========================================
    with tab2:
        st.header("Resumo por Modelo de Equipamento")
        st.write("Consolidação automática do histórico de desempenho das propostas para cada linha de redutor.")
        
        # Criação dinâmica do Resumo baseado nos Dados reais
        resumo_dinamico = df.groupby('REDUTOR').agg(
            Total_Projetos=('ELEMENTO PEP', 'count'),
            Casos_Super=('Delta Vazão', lambda x: (x > 0).sum()),
            Casos_Sub=('Delta Vazão', lambda x: (x < 0).sum()),
            Media_Erro_Vazao=('Delta Vazão', 'mean'),
            Eficiencia_Media_Proj=('EFICIÊNCIA PROJETO', 'mean')
        ).reset_index()
        
        # Ordena do pior ofensor para o menor
        resumo_dinamico = resumo_dinamico.sort_values(by='Media_Erro_Vazao', ascending=False)
        
        col_r1, col_r2 = st.columns([1.5, 1])
        
        with col_r1:
            # Gráfico de Barras Horizontal de Ranking
            fig_bar = px.bar(
                resumo_dinamico, 
                x='Media_Erro_Vazao', 
                y='REDUTOR', 
                orientation='h',
                color='Media_Erro_Vazao',
                color_continuous_scale=px.colors.diverging.RdBu_r,
                title="Ranking de Maior Sobredimensionamento Médio (L/min)",
                text_auto='.1f'
            )
            fig_bar.add_vline(x=0, line_color="black")
            fig_bar.update_layout(plot_bgcolor='white', yaxis_title="Família do Redutor", xaxis_title="Média de Vazão Excedente [L/min]", coloraxis_showscale=False)
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col_r2:
            st.markdown("### Destaques")
            pior_familia = resumo_dinamico.iloc[0]
            st.error(f"🚨 **Superdimensionamento:** O modelo **{pior_familia['REDUTOR']}** gera um excesso médio de **+{pior_familia['Media_Erro_Vazao']:.1f} L/min** por proposta.")
            
            melhor_familia = resumo_dinamico.iloc[-1]
            if melhor_familia['Media_Erro_Vazao'] < 0:
                st.info(f"⚠️ **Subdimensionamento:** O modelo **{melhor_familia['REDUTOR']}** costuma ter falta de **{melhor_familia['Media_Erro_Vazao']:.1f} L/min** na proposta.")
        
        st.markdown("### Tabela de Desempenho")
        st.dataframe(
            resumo_dinamico.rename(columns={
                'REDUTOR': 'Modelo', 'Total_Projetos': 'Total Analisado', 
                'Casos_Super': 'Superdimensionados', 'Casos_Sub': 'Subdimensionados', 
                'Media_Erro_Vazao': 'Δ Erro Médio de Vazão [L/min]', 'Eficiencia_Media_Proj': 'Eficiência Média Real'
            }).style.format({'Δ Médio de Vazão [L/min]': '{:+.1f}', 'Eficiência Média Real': '{:.4f}'})
            .background_gradient(subset=['Δ Erro Médio de Vazão [L/min]'], cmap='coolwarm'),
            use_container_width=True
        )

    # ==========================================
    # ABA 3: EFICIÊNCIA DE CONSULTA
    # ==========================================
    with tab3:
        st.header("Curvas de Eficiência Estimada (Fase de Consulta)")
        if not df_eff.empty:
            try:
                df_eff_clean = df_eff.iloc[:, :5].copy()
                df_eff_clean.columns = ['RPM', '25% Carga', '50% Carga', '75% Carga', '100% Carga']
                df_eff_clean['RPM'] = pd.to_numeric(df_eff_clean['RPM'], errors='coerce')
                df_eff_clean = df_eff_clean.dropna(subset=['RPM'])

                df_eff_melted = df_eff_clean.melt(id_vars=['RPM'], var_name='Carga Nominal', value_name='Eficiência')
                df_eff_melted['RPM_str'] = df_eff_melted['RPM'].astype(int).astype(str) + " RPM"

                col_e1, col_e2 = st.columns([2, 1])
                with col_e1:
                    fig_eff = px.line(df_eff_melted, x='Carga Nominal', y='Eficiência', color='RPM_str', markers=True, title="Curvas de Eficiência em Função da Carga")
                    fig_eff.update_traces(line=dict(width=2.5), marker=dict(size=8), hovertemplate='%{y:.4f}<extra></extra>')
                    fig_eff.update_layout(plot_bgcolor='#FAFAFA', paper_bgcolor='#FAFAFA', yaxis=dict(range=[0.935, 0.995], tickformat=".4f", gridcolor='#EAEAEA', zeroline=False), xaxis=dict(gridcolor='#EAEAEA', zeroline=False), hovermode="x unified")
                    st.plotly_chart(fig_eff, use_container_width=True)
                with col_e2:
                    st.dataframe(df_eff_clean.style.format({'RPM': '{:.0f}', '25% Carga': '{:.4f}', '50% Carga': '{:.4f}', '75% Carga': '{:.4f}', '100% Carga': '{:.4f}'}), use_container_width=True)
            except Exception as e:
                st.error(f"Não foi possível renderizar o gráfico de eficiência: {e}")
        else:
            st.info("Aba de Eficiência não encontrada.")

    # ==========================================
    # ABA 4: CURVAS DE POTÊNCIA
    # ==========================================
    with tab4:
        st.header("Capacidade de Potência Máxima por Redutor")
        if not df_pot.empty:
            try:
                df_pot_clean = df_pot.copy()
                df_pot_clean = df_pot_clean.rename(columns={df_pot_clean.columns[0]: 'Redutor'})
                colunas_rpm = [col for col in df_pot_clean.columns if any(char.isdigit() for char in str(col))]
                
                df_melt = df_pot_clean.melt(id_vars=['Redutor'], value_vars=colunas_rpm, var_name='RPM_str', value_name='Potencia_kW')
                df_melt['RPM'] = df_melt['RPM_str'].astype(str).str.extract(r'(\d+)').astype(float)
                df_melt['Potencia_kW'] = pd.to_numeric(df_melt['Potencia_kW'].astype(str).str.replace(',', '.'), errors='coerce')
                
                df_plot = df_melt.dropna(subset=['RPM', 'Potencia_kW']).copy()
                df_plot = df_plot[df_plot['Redutor'].notna()]
                df_plot['Redutor'] = df_plot['Redutor'].astype(str)
                df_plot = df_plot.sort_values(by=['Redutor', 'RPM'])

                col_p1, col_p2 = st.columns([2, 1])
                with col_p1:
                    fig_pot = go.Figure()
                    for redutor in df_plot['Redutor'].unique():
                        df_sub = df_plot[df_plot['Redutor'] == redutor]
                        fig_pot.add_trace(go.Scatter(x=df_sub['RPM'], y=df_sub['Potencia_kW'], mode='lines+markers', name=redutor, line=dict(width=2.5), hovertemplate='%{y:,.0f} kW<extra></extra>'))
                    
                    fig_pot.update_layout(title="Curva Limite de Potência vs. RPM", plot_bgcolor='#FAFAFA', paper_bgcolor='#FAFAFA', xaxis_title="Rotação (RPM)", yaxis_title="Potência Máxima [kW]", yaxis=dict(range=[0, 70000], gridcolor='#EAEAEA', zeroline=False, tickformat=","), xaxis=dict(gridcolor='#EAEAEA', zeroline=False, tickmode='array', tickvals=[4000, 4800, 6000, 6800, 7550, 8500, 10880, 12000, 13600]), hovermode="x unified", margin=dict(l=40, r=40, t=60, b=40))
                    st.plotly_chart(fig_pot, use_container_width=True)
                with col_p2:
                    st.dataframe(df_pot_clean, use_container_width=True)
            except Exception as e:
                st.error(f"Não foi possível processar a aba de Potência: {e}")
        else:
            st.info("Aba de Potência não encontrada.")

    # ==========================================
    # ABA 5: CALCULADORA OTIMIZADA REATIVA
    # ==========================================
    with tab5:
        st.header("Calculadora Otimizada para Fase de Consulta")
        
        try:
            col_t1, col_t2 = st.columns([3, 1])
            with col_t1:
                st.write("Insira os dados operacionais abaixo. O sistema fará a seleção automática da carcaça e o cálculo termodinâmico da vazão estimada.")
            with col_t2:
                remover_outliers = st.toggle("Filtrar Casos Discrepantes (IQR)", value=True)

            # Preparação do Fator K Estatístico
            df_k_calc = df.copy()
            if remover_outliers:
                Q1 = df_k_calc.groupby('REDUTOR')['K_dissipacao'].transform(lambda x: x.quantile(0.25))
                Q3 = df_k_calc.groupby('REDUTOR')['K_dissipacao'].transform(lambda x: x.quantile(0.75))
                IQR = Q3 - Q1
                mask = (df_k_calc['K_dissipacao'] >= (Q1 - 1.5 * IQR)) & (df_k_calc['K_dissipacao'] <= (Q3 + 1.5 * IQR))
                df_limpo = df_k_calc[mask]
            else:
                df_limpo = df_k_calc

            df_k_media = df_limpo.groupby('REDUTOR')['K_dissipacao'].mean().reset_index()
            k_dict = dict(zip(df_k_media['REDUTOR'], df_k_media['K_dissipacao']))
            
            # INPUTS FORA DO FORMULÁRIO (Atualização instantânea)
            c_in1, c_in2, c_in3 = st.columns(3)
            
            with c_in1:
                potencia_in = st.number_input("Potência de Entrada ($P_{in}$) [kW]", min_value=0.0, value=10000.0, step=10.0)
                rpm_opts = [4000, 4800, 6000, 6800, 7550, 8500, 10880, 12000, 13600]
                rpm_in = st.selectbox("Rotação de Entrada [RPM]", options=rpm_opts, index=5)
            
            # --- LÓGICA DE AUTO-SELEÇÃO DO REDUTOR ---
            redutor_sugerido = None
            potencia_limite_encontrada = 0
            
            if not df_pot.empty:
                df_pot_bus = df_pot.copy()
                df_pot_bus.columns = ['Redutor'] + list(df_pot_bus.columns[1:])
                # Descobre qual coluna tem a rotação que o usuário escolheu
                col_match = [c for c in df_pot_bus.columns if str(rpm_in) in c]
                
                if col_match:
                    col_name = col_match[0]
                    df_s = df_pot_bus[['Redutor', col_name]].copy()
                    
                    # Converte a coluna de potência máxima daquele RPM para número
                    df_s[col_name] = pd.to_numeric(df_s[col_name].astype(str).str.replace(',', '.'), errors='coerce')
                    df_s = df_s.dropna()
                    
                    # Filtra apenas redutores que aguentam a potência inserida e pega o menor deles
                    df_validos = df_s[df_s[col_name] >= potencia_in].sort_values(by=col_name)
                    
                    if not df_validos.empty:
                        redutor_sugerido = str(df_validos.iloc[0]['Redutor']).strip()
                        potencia_limite_encontrada = df_validos.iloc[0][col_name]

            # Famílias Históricas
            familias_disponiveis = [str(f).strip() for f in df_k_media['REDUTOR'].unique()]
            if len(familias_disponiveis) == 0:
                familias_disponiveis = [str(f).strip() for f in df['REDUTOR'].unique()]
                
            index_sugerido = 0
            if redutor_sugerido and redutor_sugerido in familias_disponiveis:
                index_sugerido = familias_disponiveis.index(redutor_sugerido)
                
            with c_in2:
                familia_sel = st.selectbox("Família do Redutor Base", options=familias_disponiveis, index=index_sugerido)
                eficiencia = st.number_input("Eficiência Global Estimada ($\eta$)", min_value=0.0000, max_value=1.000, value=0.9850, step=0.0001, format="%.4f")
            
            with c_in3:
                delta_t = st.number_input("Salto Térmico do Óleo ($\Delta T$) [°C]", min_value=1.0, value=15.0, step=1.0)
                cp_oleo = st.number_input("Calor Específico do Óleo ($c_p$) [kJ/kg.°C]", value=2.0)
                rho_oleo = st.number_input("Densidade do Óleo ($\rho$) [kg/L]", value=0.86)

            # MENSAGEM DO SISTEMA (Feedback da Lógica)
            st.markdown("### Diagnóstico do Sistema")
            if redutor_sugerido:
                if redutor_sugerido == familia_sel:
                    st.success(f"💡 **Seleção Automática:** Para a demanda de **{potencia_in:,.0f} kW** a **{rpm_in} RPM**, o menor modelo adequado é o **{redutor_sugerido}** (limite técnico de {potencia_limite_encontrada:,.0f} kW).")
                else:
                    st.warning(f"⚠️ **Atenção:** Você modificou manualmente o modelo do redutor para **{familia_sel}**. Contudo, segundo a tabela de capacidade comercial, o recomendado para {potencia_in:,.0f} kW a {rpm_in} RPM seria o modelo **{redutor_sugerido}**.")
            else:
                st.error(f"❌ **Fora de Escopo:** Não há registro na aba de 'Potência' de uma carcaça capaz de suportar {potencia_in:,.0f} kW operando a {rpm_in} RPM.")

            # --- CÁLCULO IMEDIATO ---
            perda_total_kw = potencia_in * (1 - eficiencia)
            fator_k = k_dict.get(familia_sel, 0.85) # Se a família não tiver histórico usa conservadorismo moderado
            carga_termica_real = perda_total_kw * fator_k
            
            vazao_classica = ((perda_total_kw / (cp_oleo * delta_t)) / rho_oleo) * 60
            vazao_otimizada = ((carga_termica_real / (cp_oleo * delta_t)) / rho_oleo) * 60
            
            st.subheader("Balanço Térmico e Solução Hidráulica")
            rc1, rc2, rc3, rc4 = st.columns(4)
            rc1.metric("Potência Dissipada", f"{perda_total_kw:.2f} kW", help="Energia total perdida pelo redutor (perda_total_kw = potencia_in * (1 - eficiencia))")
            rc2.metric(f"Fator de Correção ($K$)", f"{fator_k * 100:.2f}%", f"Ref. Histórica {familia_sel}", delta_color="off", help="Com base no histórico, é a porcentagem da perda total que se converte em carga térmica no óleo.")
            rc3.metric("Carga Térmica Efetiva no Óleo", f"{carga_termica_real:.2f} kW", help="É a carga térmica após a aplicação do fator de correção, que será efetivamente usada no cálculo otimizado da vazão")
            rc4.metric("Redução de Vazão Estimada", f"{(vazao_classica - vazao_otimizada):.1f} L/min", f"-{((1 - fator_k)*100):.1f}% de Volume")
            
            st.divider()
            st.info(f"🚨 **Abordagem do Método Antigo (Calculando Carga Térmica Total (100% da perda)):** Vazão Conservadora de `{vazao_classica:.1f} L/min`")
            st.success(f"✅ **Abordagem Ajustada (Aplicando o Fator de Correção ($K$)):** Vazão Otimizada de `{vazao_otimizada:.1f} L/min`")
                
        except Exception as e:
            st.error(f"Erro na lógica do dimensionamento: {e}")
