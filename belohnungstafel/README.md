# 🏆 Belohnungstafel

Eine kleine Familien-Webanwendung in Python (Flask): Kinder haken Aufgaben ab,
sammeln Punkte und lösen sie im Belohnungs-Shop ein. Eltern legen im
Admin-Bereich Aufgaben, Belohnungen und Konten an und geben alles frei.

## Funktionen

**Für die Kinder**
- Eigener Login, eigene Tafel mit den für sie freigegebenen Aufgaben
- „Erledigt!"-Button je Aufgabe (täglich / wöchentlich / einmalig)
- Punktestand immer sichtbar, Verlauf aller Buchungen
- Belohnungs-Shop: einlösen, was man sich leisten kann

**Für die Eltern (Admin-Bereich)**
- Übersicht über alle Kinder und offene Freigaben
- Aufgaben anlegen/bearbeiten/löschen: Titel, Beschreibung, Emoji, Punkte,
  Wiederholung, Zuweisung an einzelne Kinder, Freigabe nötig ja/nein
- Belohnungen anlegen/bearbeiten/löschen: Kosten, Emoji, verfügbare Anzahl,
  im Shop sichtbar ja/nein
- Freigaben: erledigte Aufgaben bestätigen oder ablehnen, Belohnungswünsche
  freigeben oder ablehnen (dann werden die Punkte automatisch zurückgebucht)
- Kontomanagement: Kinder- und Elternkonten anlegen, umbenennen, Avatar und
  Passwort setzen, sperren, löschen
- Punkte manuell buchen (Bonus oder Abzug) mit Begründung
- Kontoauszug je Kind

## Installation

```bash
cd belohnungstafel
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Einrichten

```bash
export FLASK_APP=run.py
export SECRET_KEY="ein-langes-zufaelliges-geheimnis"

flask init-db                      # Datenbank anlegen
flask create-parent                # dein Elternkonto (fragt nach Passwort)
flask demo-data                    # optional: Beispielaufgaben und -belohnungen
```

Kinderkonten legst du danach bequem im Admin-Bereich an – oder auf der
Kommandozeile mit `flask create-child`.

## Starten

```bash
python run.py                      # http://127.0.0.1:5000
```

Damit Tablet und Handy im Heimnetz mitmachen können:

```bash
HOST=0.0.0.0 python run.py
```

Für den Dauerbetrieb (z. B. auf einem Raspberry Pi) lieber einen richtigen
Server verwenden, etwa:

```bash
pip install waitress
SECRET_KEY="..." waitress-serve --host 0.0.0.0 --port 5000 run:app
```

## Konfiguration

| Variable | Bedeutung | Standard |
| --- | --- | --- |
| `SECRET_KEY` | Schlüssel für Session-Cookies – im echten Betrieb unbedingt setzen | `dev-secret-bitte-aendern` |
| `DATABASE_URL` | Datenbank | SQLite unter `instance/belohnungstafel.db` |
| `HOST` / `PORT` | Adresse des Entwicklungsservers | `127.0.0.1` / `5000` |
| `FLASK_DEBUG` | Debug-Modus (nur lokal) | aus |

Zeitstempel und der Tageswechsel für „täglich"/„wöchentlich" richten sich nach
der Ortszeit des Servers.

## Wie die Punkte gebucht werden

Der Punktestand ist immer die Summe aller Buchungen in `PointTransaction` –
es gibt keinen separaten Zähler, der auseinanderlaufen könnte.

- Aufgabe mit Freigabe: Punkte gibt es erst, wenn ein Elternteil bestätigt.
- Aufgabe ohne Freigabe: Punkte werden sofort gutgeschrieben.
- Belohnung einlösen: Die Punkte werden sofort abgebucht (damit sie nicht
  doppelt ausgegeben werden) und bei einer Ablehnung wieder erstattet.

## Tests

```bash
pip install pytest
python -m pytest tests -q
```

## Aufbau

```
belohnungstafel/
├── run.py                 Startpunkt
├── app/
│   ├── __init__.py        Application Factory
│   ├── config.py          Konfiguration
│   ├── models.py          Datenmodell + Punktebuchungen
│   ├── forms.py           Formulare (mit CSRF-Schutz)
│   ├── security.py        Rollenprüfung Eltern/Kind
│   ├── cli.py             flask init-db / create-parent / create-child / demo-data
│   ├── views/             auth, kid (Tafel & Shop), admin
│   ├── templates/
│   └── static/css/
└── tests/
```
