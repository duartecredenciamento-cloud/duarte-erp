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
# EMAIL CONFIG
# =========================
EMAIL_REMETENTE = "SEUEMAIL@gmail.com"
SENHA_EMAIL = "SENHA_APP"

def enviar_email(destinatario, nome, descricao, valor, categoria):
    corpo = f"""
Olá {nome},

🎉 Seu reembolso foi aprovado e pago!

📌 {descricao}
💰 R$ {valor}
📂 {categoria}

⚠️ Não responda este e-mail.

Duarte Gestão 🚀
"""
    msg = MIMEText(corpo)
    msg["Subject"] = "Reembolso Pago"
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = destinatario

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_REMETENTE, SENHA_EMAIL)
            server.send_message(msg)
    except Exception as e:
        print("Erro email:", e)

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
        status TEXT DEFAULT 'PENDENTE',
        data_criacao TEXT,
        data_pagamento TEXT
    )
    """)

    conn.commit()
    conn.close()

def criar_admin():
    conn = connect()
    senha_hash = bcrypt.hashpw("123456".encode(), bcrypt.gensalt()).decode()
    try:
        conn.execute("INSERT INTO usuarios VALUES (NULL, ?, ?, ?, ?, ?)",
                     ("Admin","admin","admin@email.com", senha_hash, 1))
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
                     (nome, user, email, senha_hash, 0))
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

    abas = st.tabs(["Login", "Criar Conta"])

    with abas[0]:
        user = st.text_input("Usuário", key="login_user")
        senha = st.text_input("Senha", type="password", key="login_senha")

        if st.button("Entrar", key="btn_login"):
            r = login(user, senha)
            if r:
                st.session_state["logado"] = True
                st.session_state["usuario"] = r[2]
                st.session_state["admin"] = r[5]
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
# MENU
# =========================
menu = st.sidebar.radio("Menu", ["Dashboard","Despesas","Reembolsos"])

# =========================
# DASHBOARD
# =========================
if menu == "Dashboard":
    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    if not df.empty:
        st.metric("Total", f"R$ {df['valor'].sum():.2f}")
        st.plotly_chart(px.pie(df, names="categoria", values="valor"))
        st.plotly_chart(px.bar(df, x="usuario", y="valor"))

    conn.close()

# =========================
# DESPESAS
# =========================
elif menu == "Despesas":

    tab1, tab2 = st.tabs(["Nova","Minhas"])

    # NOVA
    with tab1:
        desc = st.text_input("Descrição", key="desc")
        valor = st.number_input("Valor", key="valor")
        categoria = st.text_input("Categoria", key="cat")

        if st.button("Enviar", key="btn_env"):
            conn = connect()
            conn.execute("""
            INSERT INTO despesas (usuario, descricao, categoria, valor, data_criacao)
            VALUES (?, ?, ?, ?, ?)
            """,(st.session_state["usuario"], desc, categoria, valor, datetime.now()))
            conn.commit()
            conn.close()
            st.success("Enviado!")

    # MINHAS
    with tab2:
        conn = connect()
        df = pd.read_sql(f"SELECT * FROM despesas WHERE usuario='{st.session_state['usuario']}'", conn)

        for _, row in df.iterrows():
            st.write(row["descricao"], row["valor"], row["status"])

            if st.button("Excluir", key=f"del_{row['id']}"):
                conn.execute("DELETE FROM despesas WHERE id=?", (row["id"],))
                conn.commit()
                st.rerun()

        conn.close()

# =========================
# REEMBOLSOS
# =========================
elif menu == "Reembolsos":

    if not st.session_state.get("admin"):
        st.stop()

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    for _, row in df.iterrows():

        st.write(row["usuario"], row["descricao"], row["valor"], row["status"])

        if st.button("Pagar", key=f"pagar_{row['id']}"):

            c = conn.cursor()
            c.execute("SELECT nome, email FROM usuarios WHERE usuario=?", (row["usuario"],))
            user_data = c.fetchone()

            if user_data:
                nome, email = user_data

                enviar_email(email, nome, row["descricao"], row["valor"], row["categoria"])

            conn.execute("""
            UPDATE despesas SET status='PAGO', data_pagamento=? WHERE id=?
            """,(datetime.now(), row["id"]))

            conn.commit()
            st.success("Pago + Email enviado!")

    conn.close()