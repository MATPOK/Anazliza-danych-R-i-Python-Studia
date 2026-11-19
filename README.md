# Analiza kursów walut NBP

Aplikacja pokazuje historyczne kursy walut z Narodowego Banku Polskiego.
Można wybrać waluty i okres, a aplikacja pokaże wykres, statystyki i powiązania między walutami.

Dane są od 2 stycznia 2002 roku do dziś.

## Pliki

- `fetch_data.py` – pobiera kursy z API NBP i zapisuje je do bazy
- `app.py` – aplikacja w przeglądarce
- `nbp_dane.db` – baza z kursami

## Jak uruchomić

### Bez Dockera

```
pip install -r requirements.txt
python fetch_data.py
streamlit run app.py
```

Aplikacja otworzy się w przeglądarce.

### Z Dockerem

```
docker compose up -d --build
```

Aplikacja będzie pod adresem http://localhost:8501.
Nowe kursy pobierają się same co godzinę.

Wyłączenie:

```
docker compose down
```
