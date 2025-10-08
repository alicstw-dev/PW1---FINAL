from app import create_app, db

app = create_app()

# Garante que as tabelas do banco de dados sejam criadas antes da primeira requisição
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    # Remova debug=True para produção
    app.run(host="0.0.0.0", port=5000)
