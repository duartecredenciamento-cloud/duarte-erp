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
# 🎨 ESTILO TOP
# =========================
st.markdown("""
<style>

/* SIDEBAR */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #020617, #0f172a);
}

/* MENU */
div[role="radiogroup"] label {
    padding: 12px;
    margin-bottom: 6px;
    border-radius: 10px;
    transition: 0.2s;
    color: #cbd5e1;
}

/* HOVER */
div[role="radiogroup"] label:hover {
    background: rgba(59,130,246,0.15);
    transform: translateX(5px);
}

/* ATIVO (SEM QUEBRAR STREAMLIT) */
div[role="radiogroup"] input:checked + div {
    background: #2563eb !important;
    color: white !important;
    border-radius: 10px;
}

/* CLICK */
div[role="radiogroup"] label:active {
    transform: scale(0.95);
}

/* TRANSIÇÃO */
html, body, [class*="css"] {
    transition: all 0.2s ease-in-out;
}

</style>
""", unsafe_allow_html=True)

# =========================
# 🔥 LOGO
# =========================
st.markdown("""
<div style="text-align:center;">
<a href="https://www.duartegestao.com.br/index.html" target="_blank">
<img src="https://www.duartegestao.com.br/images/logo-duartegestao.png" width="220">
</a>
</div>
""", unsafe_allow_html=True)

# =========================
# 📧 EMAIL
# =========================
EMAIL_REMETENTE = "financeiro.duartegestao@gmail.com"
SENHA_EMAIL = "adre gnlu xrmg eheu"

def enviar_email(destinatario, nome, descricao, valor, categoria):
    try:
        corpo = f"""
Olá {nome},

Seu reembolso foi aprovado e pago com sucesso!

Descrição: {descricao}
Categoria: {categoria}
Valor: R$ {valor}

⚠️ NÃO RESPONDER ESTE EMAIL

Duarte Gestão
"""
        msg = MIMEText(corpo)
        msg["Subject"] = "💰 Reembolso Pago"
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

def criar_admins():
    conn = connect()
    c = conn.cursor()

    usuarios = [
        ("Admin","admin","admin@email.com","123456","admin"),
        ("Financeiro","financeiro","financeiro@email.com","123456","financeiro"),
        ("Operacional","operacional","operacional@email.com","123456","operacional")
    ]

    for nome, user, email, senha, tipo in usuarios:
        hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
        try:
            c.execute("INSERT INTO usuarios VALUES (NULL, ?, ?, ?, ?, ?)",
                      (nome, user, email, hash, tipo))
        except:
            pass

    conn.commit()
    conn.close()

criar_tabelas()
criar_admins()

# =========================
# LOGIN
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

if "logado" not in st.session_state:
    st.session_state["logado"] = False

# =========================
# LOGIN / CADASTRO
# =========================
if not st.session_state["logado"]:

    abas = st.tabs(["Login", "Criar Conta"])

    with abas[0]:
        user = st.text_input("Usuário", key="login_user")
        senha = st.text_input("Senha", type="password", key="login_pass")

        if st.button("Entrar"):
            r = login(user, senha)
            if r:
                st.session_state["logado"] = True
                st.session_state["usuario"] = r[2]
                st.session_state["tipo"] = r[5]
                st.session_state["nome"] = r[1]
                st.session_state["email"] = r[3]
                st.rerun()

    with abas[1]:
        nome = st.text_input("Nome", key="cad_nome")
        user = st.text_input("Usuário", key="cad_user")
        email = st.text_input("Email", key="cad_email")
        senha = st.text_input("Senha", type="password", key="cad_pass")

        if st.button("Criar Conta"):
            conn = connect()
            try:
                hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
                conn.execute("INSERT INTO usuarios VALUES (NULL, ?, ?, ?, ?, ?)",
                             (nome, user, email, hash, "usuario"))
                conn.commit()
                st.success("Conta criada!")
            except:
                st.error("Erro ao criar")
            conn.close()

    st.stop()

# =========================
# MENU
# =========================
menu = st.sidebar.radio(
    "",
    ["dashboard", "despesas", "reembolsos"],
    format_func=lambda x: {
        "dashboard": "📊  Dashboard",
        "despesas": "💸  Despesas",
        "reembolsos": "💰  Reembolsos"
    }[x]
)

# =========================
# DASHBOARD
# =========================
if menu == "dashboard":

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    st.title("📊 Dashboard")

    if not df.empty:
        st.plotly_chart(px.pie(df, names="categoria", values="valor"), use_container_width=True)
        st.plotly_chart(px.bar(df, x="centro_custo", y="valor"), use_container_width=True)

    conn.close()

# =========================
# DESPESAS
# =========================
elif menu == "despesas":

    tab1, tab2 = st.tabs(["Nova", "Minhas"])

    categorias = [
        "Limpeza","Remuneração Sócios","Alimentação","Telefonia e Internet",
        "Software e Licenças - Informática","Transportes / Logística",
        "Material de Escritório","Equipamentos de Informática",
        "Estacionamento","Móveis e Utensílios",
        "Despesas de Viagens","Máquinas e Equipamentos"
    ]

    centros = [
        "CREDENCIAMENTO","REDE","DIRETORIA",
        "DUARTE GESTÃO","MARKETING","FINANCEIRO"
    ]

    # NOVA
    with tab1:

        desc = st.text_input("Descrição", key="desc")
        valor = st.number_input("Valor", key="valor")

        categoria = st.selectbox("Categoria", categorias, key="cat")
        centro = st.selectbox("Centro de Custo", centros, key="centro")

        arquivos = st.file_uploader(
            "📎 Anexar arquivos",
            accept_multiple_files=True,
            key="upload_files"
        )

        if st.button("Enviar"):

            lista = []

            if arquivos:
                for arq in arquivos:
                    nome = f"{datetime.now().timestamp()}_{arq.name}"
                    caminho = os.path.join("uploads", nome)

                    with open(caminho, "wb") as f:
                        f.write(arq.read())

                    lista.append(caminho)

            conn = connect()
            conn.execute("""
            INSERT INTO despesas (usuario, descricao, categoria, centro_custo, valor, arquivos)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (st.session_state["usuario"], desc, categoria, centro, valor, ",".join(lista)))
            conn.commit()
            conn.close()

            st.success("Enviado!")

    # MINHAS
    with tab2:

        conn = connect()
        df = pd.read_sql(f"SELECT * FROM despesas WHERE usuario='{st.session_state['usuario']}'", conn)

        for _, row in df.iterrows():

            st.write(f"{row['descricao']} - R$ {row['valor']}")

            if st.button("Excluir", key=f"del_{row['id']}"):
                conn.execute("DELETE FROM despesas WHERE id=?", (row["id"],))
                conn.commit()
                st.rerun()

        conn.close()

# =========================
# REEMBOLSOS
# =========================
elif menu == "reembolsos":

    if st.session_state["tipo"] not in ["admin", "financeiro", "operacional"]:
        st.stop()

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    for _, row in df.iterrows():

        st.markdown('<div class="card">', unsafe_allow_html=True)

        st.write(f"👤 {row['usuario']} | 💰 R$ {row['valor']} | 📌 {row['status']}")
        st.write(f"📅 Criado: {row['data_criacao']}")
        st.write(f"💸 Pago: {row['data_pagamento']}")

        # 📎 ARQUIVOS
        if row["arquivos"]:
            arquivos = row["arquivos"].split(",")

            for arq in arquivos:
                if os.path.exists(arq):

                    if arq.endswith(".pdf"):
                        with open(arq, "rb") as f:
                            st.download_button("📄 PDF", f, file_name=os.path.basename(arq), key=f"pdf_{arq}")

                    elif arq.endswith((".png",".jpg",".jpeg")):
                        st.image(arq, width=200)

                    else:
                        with open(arq, "rb") as f:
                            st.download_button("📎 Arquivo", f, file_name=os.path.basename(arq), key=f"file_{arq}")

        col1, col2, col3 = st.columns(3)

        if col1.button("Aprovar", key=f"ap_{row['id']}"):
            conn.execute("UPDATE despesas SET status='APROVADO' WHERE id=?", (row["id"],))
            conn.commit()

        if col2.button("Rejeitar", key=f"rej_{row['id']}"):
            conn.execute("UPDATE despesas SET status='REJEITADO' WHERE id=?", (row["id"],))
            conn.commit()

        if col3.button("Pagar", key=f"pg_{row['id']}"):

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

        st.markdown('</div>', unsafe_allow_html=True)

    conn.close()