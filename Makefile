setup: ; bash scripts/setup_mac.sh
run: ; streamlit run app.py
api: ; uvicorn api:app --port 8000
test: ; SKYGUARD_EPOCHS=2 pytest -q
docker: ; docker compose up --build
