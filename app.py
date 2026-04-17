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
    border-right: 1px solid rgba(255,255,255,0.05);
}

/* MENU */
div[role="radiogroup"] label {
    display: flex;
    align-items: center;
    padding: 14px;
    margin-bottom: 8px;
    border-radius: 12px;
    color: #cbd5e1;
    cursor: pointer;
    transition: all 0.3s ease;
}

div[role="radiogroup"] label:hover {
    background: rgba(59,130,246,0.15);
    transform: translateX(8px);
}

div[role="radiogroup"] input:checked + div {
    background: linear-gradient(90deg,#2563eb,#1d4ed8);
    color: #fff;
    transform: scale(1.05);
    box-shadow: 0 0 20px rgba(37,99,235,0.5);
}

/* CARD PADRÃO (REEMBOLSO + DESPESA) */
.card {
    background: var(--secondary-background-color);
    padding: 18px;
    border-radius: 14px;
    margin-bottom: 12px;
    transition: all 0.3s ease;
    animation: fadeIn 0.4s ease-in-out;
    color: var(--text-color);
    border: 1px solid rgba(128,128,128,0.2);
}

.card:hover {
    transform: translateY(-5px) scale(1.02);
    box-shadow: 0 10px 25px rgba(0,0,0,0.2);
}
.card:hover {
    transform: translateY(-5px) scale(1.02);
    box-shadow: 0 10px 25px rgba(0,0,0,0.4);
}

/* ANIMAÇÃO ENTRADA */
@keyframes fadeIn {
    from {opacity: 0; transform: translateY(15px);}
    to {opacity: 1; transform: translateY(0);}
}

/* BOTÕES */
.stButton>button {
    border-radius: 10px;
    transition: 0.2s;
}

.stButton>button:hover {
    transform: scale(1.05);
}

/* SUCESSO ANIMADO */
.success-check {
    background: linear-gradient(90deg,#22c55e,#16a34a);
    padding: 12px;
    border-radius: 10px;
    color: white;
    text-align: center;
    font-weight: bold;
    animation: pop 0.3s ease;
}

@keyframes pop {
    from {transform: scale(0.8); opacity: 0;}
    to {transform: scale(1); opacity: 1;}
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
SENHA_EMAIL = "hgxe wlet rwdg nzov"

def enviar_email(destinatario, nome, descricao, valor, categoria, centro_custo, data_pagamento):
    try:
        corpo = f"""
Olá {nome},

Seu reembolso foi aprovado e pago com sucesso!

📄 Descrição: {descricao}
📂 Categoria: {categoria}
🏢 Centro de Custo: {centro_custo}
💰 Valor: R$ {valor}
📅 Data do Pagamento: {data_pagamento}

⚠️ NÃO RESPONDER ESTE EMAIL

Duarte Gestão
"""

        msg = MIMEText(corpo)
        msg["Subject"] = "💰 Reembolso Pago"
        msg["From"] = EMAIL_REMETENTE
        msg["To"] = destinatario

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_REMETENTE, SENHA_EMAIL)
        server.send_message(msg)
        server.quit()

        st.success("📧 Email enviado!")

    except Exception as e:
        st.error(f"❌ Erro ao enviar email: {e}")

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
    telefone TEXT,
    cpf TEXT,
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
        ("Admin","admin","admin@email.com","11999999999","00000000000","123456","admin"),
        ("Financeiro","financeiro","financeiro@email.com","11999999999","00000000000","123456","financeiro"),
        ("Operacional","operacional","operacional@email.com","11999999999","00000000000","123456","operacional")
    ]

    for nome, user, email, tel, cpf, senha, tipo in usuarios:
        hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
        try:
            c.execute("""
                INSERT INTO usuarios 
                (nome, usuario, email, telefone, cpf, senha, tipo)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (nome, user, email, tel, cpf, hash, tipo))
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

    if r:
        senha_hash = r[6]  # 👈 CONFIRMA POSIÇÃO

        if senha_hash and verificar_senha(senha, senha_hash):
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
                st.session_state["nome"] = r[1]
                st.session_state["email"] = r[3]
                st.session_state["tipo"] = r[7]
                st.rerun()

    with abas[1]:
    
    nome = st.text_input("Nome", key="cad_nome")
    user = st.text_input("Usuário", key="cad_user")
    email = st.text_input("Email", key="cad_email")
    telefone = st.text_input("Telefone", key="cad_tel")
    cpf = st.text_input("CPF", key="cad_cpf")
    senha = st.text_input("Senha", type="password", key="cad_pass")

    if st.button("Criar Conta"):
        conn = connect()
        try:
            hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()

            conn.execute("""
                INSERT INTO usuarios 
                (nome, usuario, email, telefone, cpf, senha, tipo)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (nome, user, email, telefone, cpf, hash, "usuario"))

            conn.commit()
            st.success("Conta criada!")

        except Exception as e:
            st.error(f"Erro: {e}")

        conn.close()

    st.stop()

# =========================
# MENU
# =========================
menu = st.sidebar.radio(
    "",
    ["dashboard", "despesas", "reembolsos"],
    format_func=lambda x: {
        "dashboard": "📊 Dashboard",
        "despesas": "💸 Despesas",
        "reembolsos": "💰 Reembolsos"
    }[x]
)


# =========================
# DASHBOARD
# =========================
if menu == "dashboard":

    import time

    with st.spinner("Carregando dashboard..."):
        time.sleep(1)

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    st.markdown('<div class="dashboard">', unsafe_allow_html=True)

    st.title("📊 Dashboard")

    if not df.empty:

        # =========================
        # 🔥 KPIs (CARDS)
        # =========================
        total = df["valor"].sum()
        qtd = len(df)
        media = df["valor"].mean()

        col1, col2, col3 = st.columns(3)

        col1.markdown(f'''
        <div class="card">
            💰 Total<br>
            <h2>R$ {total:.2f}</h2>
        </div>
        ''', unsafe_allow_html=True)

        col2.markdown(f'''
        <div class="card">
            📊 Média<br>
            <h2>R$ {media:.2f}</h2>
        </div>
        ''', unsafe_allow_html=True)

        col3.markdown(f'''
        <div class="card">
            📦 Registros<br>
            <h2>{qtd}</h2>
        </div>
        ''', unsafe_allow_html=True)

        # =========================
        # 📊 GRÁFICO DONUT
        # =========================
        st.subheader("📊 Despesas por Categoria")

        fig1 = px.pie(
            df,
            names="categoria",
            values="valor",
            hole=0.5
        )

        fig1.update_traces(textinfo='percent+label')
        fig1.update_layout(showlegend=True)

        st.plotly_chart(fig1, use_container_width=True)

        # =========================
        # 📊 GRÁFICO BARRAS
        # =========================
        st.subheader("🏢 Gastos por Centro de Custo")

        fig2 = px.bar(
            df,
            x="centro_custo",
            y="valor",
            text_auto=True
        )

        fig2.update_layout(hovermode="x unified")

        st.plotly_chart(fig2, use_container_width=True)

    else:
        st.info("Nenhuma despesa cadastrada ainda.")

    st.markdown('</div>', unsafe_allow_html=True)

    conn.close()

# =========================
# DESPESAS
# =========================
elif menu == "despesas":

    tab1, tab2 = st.tabs(["Nova", "Minhas"])

    categorias = [
        "Limpeza",
        "Remuneração Sócios",
        "Alimentação",
        "Telefonia e Internet",
        "Software E Licenças - Informática",
        "Transportes / Logística",
        "Material de Escritório",
        "Equipamentos de Informática",
        "Estacionamento",
        "Móveis e Utensílios",
        "Despesas de Viagens",
        "Máquinas e Equipamentos"
    ]

    centros = [
        "CREDENCIAMENTO",
        "REDE",
        "DIRETORIA",
        "DUARTE GESTÃO",
        "MARKETING",
        "FINANCEIRO"
    ]

    # =========================
    # 🆕 NOVA DESPESA
    # =========================
    with tab1:

        desc = st.text_input("Descrição")
        valor = st.number_input("Valor")

        categoria = st.selectbox("Categoria", categorias)
        centro = st.selectbox("Centro de Custo", centros)

        arquivos = st.file_uploader(
            "📎 Anexar arquivos",
            accept_multiple_files=True
        )

        if st.button("Enviar"):

            lista = []

            if arquivos:
                for i, arq in enumerate(arquivos):
                    nome = f"{datetime.now().timestamp()}_{i}_{arq.name}"
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

            st.markdown('<div class="success-check">✔ Enviado com sucesso!</div>', unsafe_allow_html=True)
            st.balloons()
            st.rerun()

    # =========================
    # 📋 MINHAS DESPESAS
    # =========================
    with tab2:

        conn = connect()
        df = pd.read_sql(f"""
            SELECT * FROM despesas 
            WHERE usuario='{st.session_state["usuario"]}'
            ORDER BY id DESC
        """, conn)

        for _, row in df.iterrows():

            st.markdown('<div class="card">', unsafe_allow_html=True)

            st.write(f"💸 {row['descricao']} - R$ {row['valor']}")
            st.write(f"📌 {row['categoria']} | {row['centro_custo']} | {row['status']}")

            # 📎 ARQUIVOS
            if row["arquivos"]:
                arquivos = row["arquivos"].split(",")

                for i, arq in enumerate(arquivos):
                    if os.path.exists(arq):

                        if arq.lower().endswith((".png", ".jpg", ".jpeg")):
                            st.image(arq, width=150)

                        else:
                            with open(arq, "rb") as f:
                                st.download_button(
                                    "📎 Baixar",
                                    f,
                                    file_name=os.path.basename(arq),
                                    key=f"down_{row['id']}_{i}"
                                )

            # 🔥 BOTÕES
            col1, col2 = st.columns(2)

            # ❌ EXCLUIR
            if col1.button("❌ Excluir", key=f"del_{row['id']}"):
                conn.execute("DELETE FROM despesas WHERE id=?", (row["id"],))
                conn.commit()
                st.rerun()

            # ✏️ EDITAR
            if col2.button("✏️ Editar", key=f"edit_{row['id']}"):
                st.session_state["editando"] = row["id"]

            # 🔥 FORM DE EDIÇÃO
            if st.session_state.get("editando") == row["id"]:

                nova_desc = st.text_input("Nova descrição", value=row["descricao"], key=f"desc_{row['id']}")
                novo_valor = st.number_input("Novo valor", value=row["valor"], key=f"val_{row['id']}")
                nova_cat = st.selectbox("Categoria", categorias, index=categorias.index(row["categoria"]), key=f"cat_{row['id']}")
                novo_centro = st.selectbox("Centro", centros, index=centros.index(row["centro_custo"]), key=f"cent_{row['id']}")

                if st.button("💾 Salvar", key=f"save_{row['id']}"):

                    conn.execute("""
                        UPDATE despesas
                        SET descricao=?, valor=?, categoria=?, centro_custo=?
                        WHERE id=?
                    """, (nova_desc, novo_valor, nova_cat, novo_centro, row["id"]))

                    conn.commit()

                    st.success("Atualizado!")
                    st.session_state["editando"] = None
                    st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

        conn.close()

# =========================
# REEMBOLSOS
# =========================
elif menu == "reembolsos":

    if st.session_state["tipo"] not in ["admin", "financeiro", "operacional"]:
        st.warning("Sem permissão")
        st.stop()

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas ORDER BY id DESC", conn)

    for _, row in df.iterrows():

        st.markdown('<div class="card">', unsafe_allow_html=True)

        st.write(f"👤 {row['usuario']} | 💰 R$ {row['valor']} | 📌 {row['status']}")
        st.write(f"📅 {row['data_criacao']}")

        # =========================
        # 📎 ARQUIVOS
        # =========================
        if row["arquivos"]:
            arquivos = row["arquivos"].split(",")

            for i, arq in enumerate(arquivos):
                if os.path.exists(arq):

                    # 🖼️ IMAGEM
                    if arq.lower().endswith((".png", ".jpg", ".jpeg")):
                        st.image(arq, width=200)

                    # 📄 PDF
                    elif arq.lower().endswith(".pdf"):
                        with open(arq, "rb") as f:
                            st.download_button(
                                "📄 Baixar PDF",
                                f,
                                file_name=os.path.basename(arq),
                                key=f"pdf_{row['id']}_{i}"
                            )

                    # 📎 OUTROS
                    else:
                        with open(arq, "rb") as f:
                            st.download_button(
                                "📎 Baixar arquivo",
                                f,
                                file_name=os.path.basename(arq),
                                key=f"file_{row['id']}_{i}"
                            )

        # =========================
        # 🔥 BOTÕES
        # =========================
        col1, col2, col3, col4 = st.columns(4)

        # ✅ APROVAR
        if col1.button("✅ Aprovar", key=f"ap_{row['id']}"):
            conn.execute(
                "UPDATE despesas SET status='APROVADO' WHERE id=?",
                (row["id"],)
            )
            conn.commit()
            st.rerun()

        # ❌ REJEITAR
        if col2.button("❌ Rejeitar", key=f"rej_{row['id']}"):
            conn.execute(
                "UPDATE despesas SET status='REJEITADO' WHERE id=?",
                (row["id"],)
            )
            conn.commit()
            st.rerun()

        # 💰 PAGAR + EMAIL
        if col3.button("💰 Pagar", key=f"pg_{row['id']}"):

            if row["status"] == "PAGO":
                st.warning("Já foi pago!")
                st.stop()

            # 🔥 BUSCAR USUÁRIO
            c = conn.cursor()
            c.execute("""
                SELECT nome, email, telefone 
                FROM usuarios 
                WHERE usuario=?
            """, (row["usuario"],))

            user_data = c.fetchone()

            if user_data:
                nome = user_data[0]
                email = user_data[1]
                telefone = user_data[2]

                # 📧 EMAIL
                enviar_email(
                    email,
                    nome,
                    row["descricao"],
                    row["valor"],
                    row["categoria"]
                )

                # 📲 (FUTURO WHATSAPP)
                # enviar_whatsapp(telefone, nome, row["valor"])

            # 🔥 ATUALIZA STATUS
            conn.execute("""
                UPDATE despesas 
                SET status='PAGO', data_pagamento=? 
                WHERE id=?
            """, (datetime.now(), row["id"]))

            conn.commit()

            st.markdown(
                '<div class="success-check">💰 Pago com sucesso!</div>',
                unsafe_allow_html=True
            )

            st.balloons()
            st.rerun()

        # 🗑️ EXCLUIR
        if col4.button("🗑️ Excluir", key=f"del_{row['id']}"):
            conn.execute("DELETE FROM despesas WHERE id=?", (row["id"],))
            conn.commit()
            st.warning("Despesa excluída!")
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    conn.close()