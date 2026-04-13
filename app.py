import streamlit as st
import sqlite3
import os
import pandas as pd
import plotly.express as px
import bcrypt
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

st.set_page_config(page_title="Duarte Gestão", layout="wide")

# =========================
# 🔥 LOGO TOPO
# =========================
st.markdown("""
<div style="text-align:center;">
    <a href="https://www.duartegestao.com.br/index.html" target="_blank">
        <img src="https://www.duartegestao.com.br/images/logo-duartegestao.png" width="220">
    </a>
</div>
""", unsafe_allow_html=True)

# =========================
# CONFIG EMAIL
# =========================
EMAIL_REMETENTE = "financeiro.duartegestao@gmail.com"
SENHA_EMAIL = "SUA_SENHA_APP_AQUI"

def enviar_email(destinatario, nome, descricao, valor, categoria):
    try:
        corpo = f"""
Olá {nome},

Seu reembolso foi aprovado e pago com sucesso!

Descrição: {descricao}
Categoria: {categoria}
Valor: R$ {valor}

NÃO RESPONDER ESTE EMAIL.

Duarte Gestão
"""
        msg = MIMEText(corpo)
        msg["Subject"] = "Reembolso Pago"
        msg["From"] = EMAIL_REMETENTE
        msg["To"] = destinatario

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_REMETENTE, SENHA_EMAIL)
            server.send_message(msg)

    except Exception as e:
        st.error(f"Erro email: {e}")

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
        nome TEXT,
        usuario TEXT UNIQUE,
        email TEXT,
        senha TEXT,
        tipo TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS despesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        descricao TEXT,
        categoria TEXT,
        centro_custo TEXT,
        valor REAL,
        arquivos TEXT,
        status TEXT DEFAULT 'PENDENTE',
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        data_pagamento TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def criar_usuarios_padrao():
    conn = connect()
    c = conn.cursor()

    usuarios = [
        ("Admin", "admin", "admin@email.com", "123456", "admin"),
        ("Financeiro", "financeiro", "financeiro@email.com", "123456", "financeiro"),
        ("Operacional", "operacional", "operacional@email.com", "123456", "operacional"),
    ]

    for nome, user, email, senha, tipo in usuarios:
        senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
        try:
            c.execute("INSERT INTO usuarios VALUES (NULL, ?, ?, ?, ?, ?)",
                      (nome, user, email, senha_hash, tipo))
        except:
            pass

    conn.commit()
    conn.close()

criar_tabelas()
criar_usuarios_padrao()

# =========================
# AUTH
# =========================
def verificar_senha(senha, hash):
    return bcrypt.checkpw(senha.encode(), hash.encode())

def login(user, senha):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE usuario=?", (user,))
    r = c.fetchone()
    conn.close()
    if r and verificar_senha(senha, r[4]):
        return r
    return None

def criar_usuario(nome, user, email, senha):
    conn = connect()
    senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
    try:
        conn.execute("INSERT INTO usuarios VALUES (NULL, ?, ?, ?, ?, ?)",
                     (nome, user, email, senha_hash, "usuario"))
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
# LOGIN / CADASTRO
# =========================
if not st.session_state["logado"]:

    abas = st.tabs(["Login", "Criar Conta"])

    with abas[0]:
        user = st.text_input("Usuário", key="login_user")
        senha = st.text_input("Senha", type="password", key="login_senha")

        if st.button("Entrar", key="btn_login"):
            r = login(user, senha)
            if r:
                st.session_state["logado"] = True
                st.session_state["usuario"] = r[2]
                st.session_state["tipo"] = r[5]
                st.session_state["nome"] = r[1]
                st.session_state["email"] = r[3]
                st.rerun()

    with abas[1]:
        nome = st.text_input("Nome completo", key="cad_nome")
        user = st.text_input("Usuário", key="cad_user")
        email = st.text_input("Email", key="cad_email")
        senha = st.text_input("Senha", type="password", key="cad_senha")

        if st.button("Criar Conta", key="btn_criar"):
            if criar_usuario(nome, user, email, senha):
                st.success("Conta criada!")
            else:
                st.error("Erro ao criar")

    st.stop()

# =========================
# SIDEBAR LOGO
# =========================
st.sidebar.markdown("""
<a href="https://www.duartegestao.com.br/index.html" target="_blank">
    <img src="https://www.duartegestao.com.br/images/logo-duartegestao.png" width="150">
</a>
""", unsafe_allow_html=True)

menu = st.sidebar.radio("Menu", ["Dashboard", "Despesas", "Reembolsos"])

# =========================
# DASHBOARD
# =========================
if menu == "Dashboard":

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    st.title("📊 Dashboard")

    if not df.empty:
        st.plotly_chart(px.pie(df, names="categoria", values="valor"))
        st.plotly_chart(px.bar(df, x="centro_custo", y="valor"))

    conn.close()

# =========================
# DESPESAS
# =========================
elif menu == "Despesas":

    tab1, tab2 = st.tabs(["Nova", "Minhas"])

    categorias = [
        "Limpeza","Remuneração Sócios","Alimentação","Telefonia e Internet",
        "Software e Licenças","Transportes","Material Escritório",
        "Equipamentos","Estacionamento","Móveis","Viagens","Máquinas"
    ]

    centros = ["FINANCEIRO","MARKETING","DIRETORIA","REDE","DUARTE GESTÃO","CREDENCIAMENTO"]

    with tab1:
        desc = st.text_input("Descrição", key="desc")
        valor = st.number_input("Valor", key="valor")
        categoria = st.selectbox("Categoria", categorias, key="cat")
        centro = st.selectbox("Centro de custo", centros, key="centro")
        arquivos = st.file_uploader("Arquivos", accept_multiple_files=True, key="file")

        if st.button("Enviar", key="btn_env"):
            lista = []
            for arq in arquivos:
                path = f"uploads/{arq.name}"
                with open(path, "wb") as f:
                    f.write(arq.read())
                lista.append(path)

            conn = connect()
            conn.execute("""
            INSERT INTO despesas (usuario, descricao, categoria, centro_custo, valor, arquivos)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (st.session_state["usuario"], desc, categoria, centro, valor, ",".join(lista)))
            conn.commit()
            conn.close()

            st.success("Enviado!")

    with tab2:
        conn = connect()
        df = pd.read_sql(f"SELECT * FROM despesas WHERE usuario='{st.session_state['usuario']}'", conn)

        for i, row in df.iterrows():
            st.write(f"{row['descricao']} - R$ {row['valor']}")

            if st.button("Excluir", key=f"del_{i}"):
                conn.execute("DELETE FROM despesas WHERE id=?", (row["id"],))
                conn.commit()
                st.rerun()

        conn.close()

# =========================
# REEMBOLSOS
# =========================
elif menu == "Reembolsos":

    if st.session_state["tipo"] not in ["admin", "financeiro", "operacional"]:
        st.stop()

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    for i, row in df.iterrows():

        st.write(f"👤 {row['usuario']} | 💰 {row['valor']} | {row['status']}")
        st.write(f"📅 Criado: {row['data_criacao']}")
        st.write(f"💸 Pago: {row['data_pagamento']}")

        if st.button("Pagar", key=f"pagar_{i}"):

            c = conn.cursor()
            c.execute("SELECT nome, email FROM usuarios WHERE usuario=?", (row["usuario"],))
            user_data = c.fetchone()

            if user_data:
                nome, email = user_data
                enviar_email(email, nome, row["descricao"], row["valor"], row["categoria"])

            conn.execute("UPDATE despesas SET status='PAGO', data_pagamento=? WHERE id=?",
                         (datetime.now(), row["id"]))
            conn.commit()

            st.success("Pago + Email enviado!")

    conn.close()