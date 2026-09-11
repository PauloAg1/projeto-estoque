import os

from flask import Flask

from db import get_connection

app = Flask(__name__)
app.secret_key=os.getenv("SECRET_KEY", "dev")


@app.route("/")
def inicio():
    return "Sistema de estoque funcionando."

@app.route("/testar-banco")
def testar_banco():
    # pagina temp de teste do db
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 AS ok")
            resultado = cursor.fetchone()
        conn.close()
        return f"Conexão com o MySQL OK: {resultado}"
    except Exception as error:
        return f"Erro na conexão: {error}", 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
    # host 0.0.0.0 pra acessar por outro device na mesma rede, port 5001 por causa do mac