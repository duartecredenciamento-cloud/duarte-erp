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
EMAIL_REMETENTE = "financeiro.duartegestao@gmail.com"
SENHA_EMAIL = "apqc vzxq isvs yfuz"

def enviar_email(destinatario, nome, descricao, valor, categoria):
    corpo = f"""
Olá {nome},

🎉 SEU REEMBOLSO FOI PAGO!

📌 Descrição: {descricao}
📂 Categoria: {categoria}
💰 Valor: R$ {valor}

Seu pagamento já foi realizado com sucesso.

⚠️ Este é um e-mail automático, não responda.

Atenciosamente,  
Duarte Gestão 🚀
"""
    msg = MIMEText(corpo)
    msg["Subject"] = "💰 Reembolso Pago - Duarte Gestão"
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = destinatario

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_REMETENTE, SENHA_EMAIL)
            server.send_message(msg)
    except Exception as e:
        st.error(f"Erro ao enviar email: {e}")

# =========================
# LISTAS
# =========================
CATEGORIAS = [
"Limpeza","Remuneração Sócios","Alimentação","Telefonia e Internet",
"Software E Licenças - Informática","Transportes / Logística",
"Material de Escritório","Equipamentos de Informática",
"Estacionamento","Móveis e Utensílios",
"Despesas de Viagens","Máquinas e Equipamentos"
]

CENTROS = [
"CREDENCIAMENTO","REDE","DIRETORIA",
"DUARTE GESTÃO","MARKETING","FINANCEIRO"
]

# =========================
# DB
# =========================
def connect():
    os.makedirs("uploads", exist_ok=True)
    return sqlite3.connect("banco.db", check_same_thread=False)

def criar_tabelas():
    conn = connect()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        usuario TEXT,
        email TEXT,
        senha TEXT,
        admin INTEGER
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS despesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        descricao TEXT,
        categoria TEXT,
        centro TEXT,
        valor REAL,
        status TEXT,
        data_pagamento TEXT
    )
    """)

    conn.commit()
    conn.close()

def criar_admin():
    conn = connect()
    senha_hash = bcrypt.hashpw("123456".encode(), bcrypt.gensalt()).decode()
    try:
        conn.execute("INSERT INTO usuarios VALUES (NULL,?,?,?,?,?)",
                     ("Admin","admin","admin@email.com",senha_hash,1))
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
    r = conn.execute("SELECT * FROM usuarios WHERE usuario=?", (user,)).fetchone()
    conn.close()
    if r and verificar_senha(senha, r[4]):
        return r
    return None

def criar_usuario(nome, user, email, senha):
    conn = connect()
    senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
    try:
        conn.execute("INSERT INTO usuarios VALUES (NULL,?,?,?,?,?)",
                     (nome,user,email,senha_hash,0))
        conn.commit()
        return True
    except:
        return False

# =========================
# SESSION
# =========================
if "logado" not in st.session_state:
    st.session_state["logado"] = False

# =========================
# LOGIN
# =========================
if not st.session_state["logado"]:

    abas = st.tabs(["Login","Criar Conta"])

    with abas[0]:
        u = st.text_input("Usuário", key="l1")
        s = st.text_input("Senha", type="password", key="l2")

        if st.button("Entrar"):
            r = login(u,s)
            if r:
                st.session_state["logado"]=True
                st.session_state["usuario"]=r[2]
                st.session_state["admin"]=r[5]
                st.session_state["nome"]=r[1]
                st.session_state["email"]=r[3]
                st.rerun()

    with abas[1]:
        n = st.text_input("Nome")
        u = st.text_input("Usuário")
        e = st.text_input("Email")
        s = st.text_input("Senha", type="password")

        if st.button("Criar Conta"):
            if criar_usuario(n,u,e,s):
                st.success("Conta criada!")

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
        st.plotly_chart(px.pie(df, names="categoria", values="valor"))
        st.plotly_chart(px.bar(df, x="centro", y="valor"))

    conn.close()

# =========================
# DESPESAS
# =========================
elif menu == "Despesas":

    desc = st.text_input("Descrição")
    valor = st.number_input("Valor")
    categoria = st.selectbox("Categoria", CATEGORIAS)
    centro = st.selectbox("Centro de Custo", CENTROS)

    if st.button("Enviar"):
        conn = connect()
        conn.execute("""
        INSERT INTO despesas VALUES (NULL,?,?,?,?,?,?,?)
        """,(st.session_state["usuario"],desc,categoria,centro,valor,"PENDENTE",None))
        conn.commit()
        conn.close()
        st.success("Enviado!")

# =========================
# REEMBOLSOS
# =========================
elif menu == "Reembolsos":

    if not st.session_state["admin"]:
        st.stop()

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    for _,row in df.iterrows():

        st.write(row["usuario"], row["descricao"], row["valor"], row["status"])

        if st.button("Pagar", key=f"pg_{row['id']}"):

            user = conn.execute(
                "SELECT nome,email FROM usuarios WHERE usuario=?",
                (row["usuario"],)
            ).fetchone()

            if user:
                enviar_email(user[1], user[0], row["descricao"], row["valor"], row["categoria"])

            conn.execute("""
            UPDATE despesas SET status='PAGO', data_pagamento=? WHERE id=?
            """,(datetime.now(), row["id"]))

            conn.commit()
            st.success("Pago + Email enviado!")

    conn.close()