from app import app


# Permite iniciar a aplicacao a partir deste arquivo auxiliar.
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
