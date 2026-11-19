import datetime
import sqlite3

import requests

# start danych w API NBP
DATA_POCZATKOWA = datetime.date(2002, 1, 2)


# Przygotowanie bazy
def stworz_baze():
    baza = sqlite3.connect('nbp_dane.db')
    baza.execute('''
        CREATE TABLE IF NOT EXISTS kursy (
            data TEXT,
            kod_waluty TEXT,
            kurs REAL,
            UNIQUE(data, kod_waluty)
        )
    ''')
    baza.commit()
    return baza


# Jakie dni są już w bazie
def pobierz_zakres_dat(baza):
    najstarsza, najnowsza = baza.execute('SELECT MIN(data), MAX(data) FROM kursy').fetchone()

    if najstarsza is None:
        return None, None
    return datetime.date.fromisoformat(najstarsza), datetime.date.fromisoformat(najnowsza)


# Pobieranie kursów z API i zapis do bazy
def pobierz_i_zapisz(baza, od_dnia, do_dnia):
    nowe_rekordy = 0
    poczatek = od_dnia

    # Pobieranie po kawałku (API max 93 dni na raz)
    while poczatek <= do_dnia:
        koniec = min(poczatek + datetime.timedelta(days=90), do_dnia)
        print(f"Pobieranie: {poczatek} -> {koniec}...")

        adres = f"https://api.nbp.pl/api/exchangerates/tables/A/{poczatek}/{koniec}/?format=json"
        odpowiedz = requests.get(adres, timeout=30)

        if odpowiedz.status_code == 200:
            for dzien in odpowiedz.json():
                for waluta in dzien['rates']:
                    kursor = baza.execute(
                        'INSERT OR IGNORE INTO kursy (data, kod_waluty, kurs) VALUES (?, ?, ?)',
                        (dzien['effectiveDate'], waluta['code'], waluta['mid']),
                    )
                    nowe_rekordy += kursor.rowcount
        elif odpowiedz.status_code == 404:
            print(f"Brak danych od NBP dla okresu {poczatek} - {koniec}.")
        else:
            print(f"Błąd API NBP: {odpowiedz.status_code}")

        baza.commit()
        poczatek = koniec + datetime.timedelta(days=1)

    print(f"\nZakończono. Dodano nowych rekordów do bazy: {nowe_rekordy}")


# Uruchomienie
if __name__ == "__main__":
    baza = stworz_baze()
    najstarsza, najnowsza = pobierz_zakres_dat(baza)
    dzisiaj = datetime.date.today()

    if najstarsza is None:
        print(f"Pusta baza. Pobieranie pełnej historii od {DATA_POCZATKOWA} do {dzisiaj}.")
        pobierz_i_zapisz(baza, DATA_POCZATKOWA, dzisiaj)
    else:
        if najstarsza > DATA_POCZATKOWA:
            print(f"Uzupełnianie historii od {DATA_POCZATKOWA} do {najstarsza}.")
            pobierz_i_zapisz(baza, DATA_POCZATKOWA, najstarsza - datetime.timedelta(days=1))

        if najnowsza >= dzisiaj:
            print("Baza jest już aktualna na dziś.")
        else:
            print(f"Baza wymaga aktualizacji od {najnowsza} do {dzisiaj}.")
            pobierz_i_zapisz(baza, najnowsza, dzisiaj)

    baza.close()
