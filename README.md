# Sistema de Controle de Estoque - Panificadora

Sistema web de controle de estoque desenvolvido como Atividade Extensionista III, de forma voluntária, para uma panificadora da comunidade.

## Como executar
1. 'python -m venv vevnv' e ative o ambiente
2. 'pip install -r requirements.txt'
3. Crie o banco: 'mysql -u root -p < schema.sql'
4. Crie o arquivo '.env'(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, SECRET_KEY)
5. Crie o administrador: 'python criar_admin.py'
6. Rode o sistema: 'python app.py'
7. Acesse 'http://IP-DO-SERVIDOR:5001'


