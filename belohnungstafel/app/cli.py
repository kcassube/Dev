import click

from .extensions import db
from .models import ROLE_CHILD, ROLE_PARENT, Reward, Task, User


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Datenbank anlegen (fehlende Tabellen erzeugen)."""
        db.create_all()
        click.echo("Datenbank ist bereit.")

    @app.cli.command("create-parent")
    @click.option("--username", prompt=True)
    @click.option("--name", prompt="Anzeigename")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_parent(username, name, password):
        """Elternkonto (Admin) anlegen."""
        username = username.strip().lower()
        if User.query.filter_by(username=username).first():
            raise click.ClickException("Benutzername ist schon vergeben.")
        user = User(username=username, display_name=name, role=ROLE_PARENT, avatar="🧑")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Elternkonto '{username}' angelegt.")

    @app.cli.command("create-child")
    @click.option("--username", prompt=True)
    @click.option("--name", prompt="Anzeigename")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option("--avatar", default="🙂")
    def create_child(username, name, password, avatar):
        """Kinderkonto anlegen."""
        username = username.strip().lower()
        if User.query.filter_by(username=username).first():
            raise click.ClickException("Benutzername ist schon vergeben.")
        user = User(username=username, display_name=name, role=ROLE_CHILD, avatar=avatar)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Kinderkonto '{username}' angelegt.")

    @app.cli.command("demo-data")
    def demo_data():
        """Beispiel-Aufgaben und -Belohnungen anlegen (nur wenn noch nichts da ist)."""
        if Task.query.count() or Reward.query.count():
            raise click.ClickException("Es gibt bereits Aufgaben oder Belohnungen.")
        tasks = [
            ("Zähne putzen", "Morgens und abends", 2, "🪥", "daily", False),
            ("Zimmer aufräumen", "Boden frei, Bett gemacht", 5, "🧸", "daily", True),
            ("Hausaufgaben", "Selbstständig erledigt", 5, "📚", "daily", True),
            ("Müll rausbringen", "", 3, "🗑️", "weekly", True),
            ("Tisch decken", "", 2, "🍽️", "daily", True),
        ]
        for title, desc, points, icon, recurrence, approval in tasks:
            db.session.add(
                Task(
                    title=title,
                    description=desc,
                    points=points,
                    icon=icon,
                    recurrence=recurrence,
                    requires_approval=approval,
                )
            )
        rewards = [
            ("30 Minuten Bildschirmzeit", "", 15, "📺", None),
            ("Eis essen gehen", "", 30, "🍦", None),
            ("Kinobesuch", "", 80, "🎬", 2),
            ("Freund:in übernachten lassen", "", 60, "🛌", None),
            ("Spielzeug bis 10 €", "", 120, "🧩", 1),
        ]
        for title, desc, cost, icon, stock in rewards:
            db.session.add(
                Reward(title=title, description=desc, cost=cost, icon=icon, stock=stock)
            )
        db.session.commit()
        click.echo("Beispieldaten angelegt.")
