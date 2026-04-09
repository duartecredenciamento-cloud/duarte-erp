import streamlit as st
import sqlite3
import os
import pandas as pd
import plotly.express as px
import bcrypt
from datetime import datetime

st.set_page_config(page_title="Duarte Gestão", layout="wide")

# =========================
# 🎨 UI STARTUP
# =========================
st.markdown("""
<style>
body {background: linear-gradient(135deg,#0f172a,#020617);color:#e2e8f0;}
.card {
    background: #111827;
    padding:20px;
    border-radius:15px;
    margin-bottom:15px;
    border:1px solid #1f2937;
}
.title {font-size:28px;font-weight:bold;}
</style>
""", unsafe_allow_html=True)

# =========================
# DB
# =========================
def connect():
    os.makedirs("uploads", exist_ok=True)
    return sqlite3.connect("banco.db", check_same_thread=False)

def criar_tabelas():
    conn = connect()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE,
        senha TEXT,
        admin INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS despesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        descricao TEXT,
        categoria TEXT,
        valor REAL,
        arquivos TEXT,
        status TEXT DEFAULT 'PENDENTE',
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        data_aprovacao TIMESTAMP,
        data_pagamento TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def criar_admin():
    conn = connect()
    c = conn.cursor()
    senha_hash = bcrypt.hashpw("123456".encode(), bcrypt.gensalt()).decode()

    try:
        c.execute("INSERT INTO usuarios VALUES (NULL, ?, ?, ?)", ("admin", senha_hash, 1))
        conn.commit()
    except:
        pass

    conn.close()

criar_tabelas()
criar_admin()

# =========================
# AUTH
# =========================
def verificar_senha(senha, hash):
    return bcrypt.checkpw(senha.encode(), hash.encode())

def login(user, senha):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE usuario=?", (user,))
    result = c.fetchone()
    conn.close()

    if result and verificar_senha(senha, result[2]):
        return result
    return None

def criar_usuario(user, senha):
    conn = connect()
    c = conn.cursor()
    senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()

    try:
        c.execute("INSERT INTO usuarios VALUES (NULL, ?, ?, ?)", (user, senha_hash, 0))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

# =========================
# SESSION
# =========================
if "logado" not in st.session_state:
    st.session_state["logado"] = False

# =========================
# LOGIN
# =========================
if not st.session_state["logado"]:

    st.markdown("""
    <div style="text-align:center;">
        <a href="https://www.duartegestao.com.br/index.html" target="_blank">
            <img src="https://www.duartegestao.com.br/images/logo-duartegestao.png" width="220">
        </a>
    </div>
    """, unsafe_allow_html=True)

    abas = st.tabs(["Login", "Criar Conta"])

    with abas[0]:
        user = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")

        if st.button("Entrar"):
            r = login(user, senha)
            if r:
                st.session_state["logado"] = True
                st.session_state["usuario"] = r[1]
                st.session_state["admin"] = r[3]
                st.rerun()
            else:
                st.error("Erro no login")

    with abas[1]:
        u = st.text_input("Novo usuário")
        s = st.text_input("Nova senha", type="password")

        if st.button("Criar Conta"):
            if criar_usuario(u, s):
                st.success("Conta criada!")
            else:
                st.error("Usuário já existe")

    st.stop()

# =========================
# SIDEBAR
# =========================
st.sidebar.markdown("""
<a href="https://www.duartegestao.com.br/index.html" target="_blank">
    <img src="https://www.duartegestao.com.br/images/logo-duartegestao.png" width="180">
</a>
""", unsafe_allow_html=True)

menu = st.sidebar.radio("Menu", ["Dashboard", "Despesas", "Reembolsos", "Relatórios"])

if st.sidebar.button("Sair"):
    st.session_state["logado"] = False
    st.rerun()

# =========================
# DASHBOARD STARTUP
# =========================
if menu == "Dashboard":

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    st.markdown('<div class="title">📊 Dashboard Inteligente</div>', unsafe_allow_html=True)

    if not df.empty:
        df["data_criacao"] = pd.to_datetime(df["data_criacao"])
        df["mes"] = df["data_criacao"].dt.to_period("M").astype(str)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total", f"R$ {df['valor'].sum() if not df.empty else 0:.2f}")
    col2.metric("Qtde", len(df))
    col3.metric("Média", f"R$ {df['valor'].mean() if not df.empty else 0:.2f}")

    if not df.empty:
        st.plotly_chart(px.line(df.groupby("mes")["valor"].sum().reset_index(),
                               x="mes", y="valor", title="Evolução Mensal"), use_container_width=True)

        st.plotly_chart(px.bar(df, x="usuario", y="valor", color="categoria"),
                        use_container_width=True)

    conn.close()

# =========================
# RELATÓRIOS
# =========================
elif menu == "Relatórios":

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    st.dataframe(df)

    st.download_button("📥 Baixar Excel",
                       df.to_csv(index=False),
                       "relatorio.csv")

    conn.close()

# =========================
# DESPESAS E REEMBOLSOS (mantém o anterior)
# =========================
else:
    st.info("Use as versões anteriores das abas Despesas e Reembolsos já enviadas.")