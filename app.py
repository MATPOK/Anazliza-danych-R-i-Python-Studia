import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st

# Ustawienia strony
st.set_page_config(
    page_title="Analiza Walut NBP",
    layout="wide",
    initial_sidebar_state=420,
)
st.title("Analiza Kursów Walut NBP")
st.markdown("Made by Mateusz Pokrywka")


# Wczytanie danych
# Dane są trzymane w pamięci przez godzinę, żeby nie czytać bazy przy każdym kliknięciu
@st.cache_data(ttl=3600)
def wczytaj_dane():
    baza = sqlite3.connect('nbp_dane.db')
    dane = pd.read_sql_query("SELECT * FROM kursy", baza)
    baza.close()

    dane['data'] = pd.to_datetime(dane['data'])
    return dane.sort_values('data')


try:
    dane = wczytaj_dane()
except sqlite3.OperationalError:
    st.error("Nie znaleziono pliku nbp_dane.db. Uruchom skrypt ETL.")
    st.stop()

najstarsza_data = dane['data'].min()
najnowsza_data = dane['data'].max()


#  Panel boczny - wybór walut
st.sidebar.header("Ustawienia Analizy")

zakresy = dane.groupby('kod_waluty')['data'].agg(['min', 'max'])

# Waluty bez notowania z ostatniego dnia - wycofane przez NBP
waluty_aktualne = sorted(zakresy.index[zakresy['max'] == najnowsza_data])
waluty_historyczne = sorted(zakresy.index[zakresy['max'] < najnowsza_data])

domyslne = ['USD', 'EUR', 'CHF'] if 'USD' in waluty_aktualne else waluty_aktualne[:3]


def pokaz_waluty(waluty):
    zaznaczone = []
    kolumny = st.columns(3)
    for i, waluta in enumerate(waluty):
        od = zakresy.loc[waluta, 'min'].date()
        do = zakresy.loc[waluta, 'max'].date()
        with kolumny[i % 3]:
            if st.checkbox(waluta, value=waluta in domyslne, key=f"waluta_{waluta}",
                           help=f"Notowania: {od} – {do}"):
                zaznaczone.append(waluta)
    return zaznaczone


with st.sidebar.expander(f"Waluty aktualne ({len(waluty_aktualne)})", expanded=True):
    wybrane = pokaz_waluty(waluty_aktualne)

if waluty_historyczne:
    with st.sidebar.expander(f"Waluty historyczne ({len(waluty_historyczne)})", expanded=False):
        st.caption("Waluty wycofane z tabeli A NBP – dane tylko za część okresu.")
        wybrane += pokaz_waluty(waluty_historyczne)


# Panel boczny - zakres dat
st.sidebar.markdown("---")
st.sidebar.subheader("Zakres czasu")

kolumna_od, kolumna_do = st.sidebar.columns(2)
with kolumna_od:
    data_od = st.date_input("Od:", min_value=najstarsza_data, max_value=najnowsza_data, value=najstarsza_data)
with kolumna_do:
    data_do = st.date_input("Do:", min_value=najstarsza_data, max_value=najnowsza_data, value=najnowsza_data)


# Filtrowanie
filtr = (
    (dane['data'].dt.date >= data_od)
    & (dane['data'].dt.date <= data_do)
    & (dane['kod_waluty'].isin(wybrane))
)
wybrane_dane = dane[filtr]

if wybrane_dane.empty:
    st.warning("Brak danych dla wybranych filtrów. Zmień zakres dat lub dodaj walutę.")
    st.stop()


# Kafelki z ostatnim kursem
st.subheader("Bieżące statystyki dla wybranego okresu")

kafelki = st.columns(len(wybrane))
for i, waluta in enumerate(wybrane):
    kursy_waluty = wybrane_dane[wybrane_dane['kod_waluty'] == waluta]
    if kursy_waluty.empty:
        continue

    pierwszy_kurs = kursy_waluty.iloc[0]['kurs']
    ostatni_kurs = kursy_waluty.iloc[-1]['kurs']

    with kafelki[i]:
        # Spadek kursu jest na zielono, bo oznacza mocniejszego złotego
        st.metric(
            label=f"Ostatni kurs {waluta}",
            value=f"{ostatni_kurs:.4f} PLN",
            delta=f"{ostatni_kurs - pierwszy_kurs:.4f} (od pocz. okresu)",
            delta_color="inverse",
        )

st.markdown("---")


# Wykres kursów
st.subheader("Historia kształtowania się kursów")

wykres = px.line(
    wybrane_dane,
    x='data',
    y='kurs',
    color='kod_waluty',
    title="Przebieg w czasie",
    labels={'data': 'Data', 'kurs': 'Kurs (PLN)', 'kod_waluty': 'Waluta'},
)
wykres.update_layout(hovermode="x unified")
st.plotly_chart(wykres, width="stretch")


# Statystyki
st.subheader("Podsumowanie statystyczne")

# Tabela
tabela_kursow = wybrane_dane.pivot(index='data', columns='kod_waluty', values='kurs')

pierwsze_kursy = tabela_kursow.apply(lambda kolumna: kolumna.dropna().iloc[0])
ostatnie_kursy = tabela_kursow.apply(lambda kolumna: kolumna.dropna().iloc[-1])

statystyki = pd.DataFrame({
    'Średnia': tabela_kursow.mean(),
    'Mediana': tabela_kursow.median(),
    'Min': tabela_kursow.min(),
    'Data min': tabela_kursow.idxmin().dt.date,
    'Max': tabela_kursow.max(),
    'Data max': tabela_kursow.idxmax().dt.date,
    'Odch. std.': tabela_kursow.std(),
    'Wsp. zmienności': tabela_kursow.std() / tabela_kursow.mean() * 100,
    'Zmiana': (ostatnie_kursy - pierwsze_kursy) / pierwsze_kursy * 100,
})
statystyki.index.name = 'Waluta'

liczba = st.column_config.NumberColumn(format="%.4f")
st.dataframe(
    statystyki,
    width="stretch",
    column_config={
        'Średnia': liczba,
        'Mediana': liczba,
        'Min': liczba,
        'Max': liczba,
        'Odch. std.': liczba,
        'Wsp. zmienności': st.column_config.NumberColumn(
            format="%.2f %%", help="Odchylenie standardowe jako procent średniej"),
        'Zmiana': st.column_config.NumberColumn(
            format="%+.2f %%", help="Zmiana kursu od pierwszego do ostatniego notowania w okresie"),
    },
)

st.markdown("---")


# Mapa korelacji
st.subheader("Zależności między walutami")

if tabela_kursow.shape[1] < 2:
    st.info("Zaznacz co najmniej dwie waluty, aby zobaczyć korelację.")
else:
    zmiany_dzienne = tabela_kursow.pct_change(fill_method=None)
    korelacja = zmiany_dzienne.corr(min_periods=20)

    mapa = px.imshow(
        korelacja,
        zmin=-1,
        zmax=1,
        color_continuous_scale="RdBu",
        text_auto=".2f" if len(korelacja) <= 12 else False,
        labels={'x': 'Waluta', 'y': 'Waluta', 'color': 'Korelacja'},
        aspect="auto",
    )
    mapa.update_layout(height=max(400, 28 * len(korelacja)))
    st.plotly_chart(mapa, width="stretch")
    st.caption(
        "Współczynnik korelacji Pearsona dziennych zmian kursów (od -1 do 1). "
    )

st.markdown("---")


# 10. Dane surowe
st.subheader("Dane surowe")
st.dataframe(wybrane_dane, width="stretch", height=250)
