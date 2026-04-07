import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime
import os

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Controle de Despesas", layout="wide")

# =========================
# BANCO
# =========================
conn = sqlite3.connect("sistema.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    username TEXT PRIMARY KEY,
    senha TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS gastos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT,
    data TEXT,
    descricao TEXT,
    valor REAL,
    arquivo TEXT,
    status TEXT
)
""")

conn.commit()

# =========================
# CRIPTO
# =========================
def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# =========================
# CADASTRO
# =========================
def cadastro():
    st.title("📝 Criar Conta")

    novo_user = st.text_input("Usuário")
    nova_senha = st.text_input("Senha", type="password")

    if st.button("Cadastrar"):
        try:
            cursor.execute(
                "INSERT INTO usuarios VALUES (?, ?)",
                (novo_user, hash_senha(nova_senha))
            )
            conn.commit()
            st.success("Conta criada!")
        except:
            st.error("Usuário já existe")

# =========================
# LOGIN
# =========================
if "logado" not in st.session_state:
    st.session_state.logado = False

def login():
    st.title("🔐 Controle de Despesas")

    user = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        cursor.execute("SELECT * FROM usuarios WHERE username=?", (user,))
        result = cursor.fetchone()

        if result and result[1] == hash_senha(senha):
            st.session_state.logado = True
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Login inválido")

# =========================
# TELA INICIAL
# =========================
if not st.session_state.logado:
    opcao = st.radio("Escolha", ["Login", "Criar conta"])

    if opcao == "Login":
        login()
    else:
        cadastro()

    st.stop()

# =========================
# MENU
# =========================
menu = st.sidebar.radio(
    "Menu",
    ["📊 Meus Gastos", "➕ Novo Gasto", "📁 Notas", "💰 Pagamentos"]
)

st.title(f"💼 Bem-vindo, {st.session_state.user}")

# =========================
# CARREGAR DADOS
# =========================
df = pd.read_sql("SELECT * FROM gastos", conn)

# =========================
# NOVO GASTO
# =========================
if menu == "➕ Novo Gasto":

    data = st.date_input("Data")
    descricao = st.text_input("Descrição")
    valor = st.number_input("Valor", min_value=0.0)

    arquivo = st.file_uploader("Nota Fiscal (PDF/Imagem)")

    if st.button("Salvar"):
        nome_arquivo = None

        if arquivo:
            os.makedirs("uploads", exist_ok=True)
            caminho = f"uploads/{arquivo.name}"

            with open(caminho, "wb") as f:
                f.write(arquivo.read())

            nome_arquivo = caminho

        cursor.execute("""
            INSERT INTO gastos (usuario, data, descricao, valor, arquivo, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            st.session_state.user,
            str(data),
            descricao,
            valor,
            nome_arquivo,
            "PENDENTE"
        ))

        conn.commit()
        st.success("Gasto enviado!")

# =========================
# MEUS GASTOS
# =========================
elif menu == "📊 Meus Gastos":

    meus = df[df["usuario"] == st.session_state.user]

    st.dataframe(meus, use_container_width=True)

# =========================
# NOTAS
# =========================
elif menu == "📁 Notas":

    notas = df[df["usuario"] == st.session_state.user]

    for _, row in notas.iterrows():
        st.write(f"{row['descricao']} - R$ {row['valor']}")

        if row["arquivo"]:
            st.download_button(
                "📥 Baixar Nota",
                open(row["arquivo"], "rb"),
                file_name=row["arquivo"]
            )

# =========================
# PAGAMENTOS (EMPRESA)
# =========================
elif menu == "💰 Pagamentos":

    st.subheader("Controle da Empresa")

    st.dataframe(df, use_container_width=True)

    id_pag = st.number_input("ID para marcar como pago", min_value=1)

    if st.button("Marcar como PAGO"):
        cursor.execute("""
            UPDATE gastos
            SET status='PAGO'
            WHERE id=?
        """, (id_pag,))
        conn.commit()

        st.success("Pagamento realizado!")
        st.rerun()