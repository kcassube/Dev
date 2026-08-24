from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    IntegerField,
    PasswordField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    EqualTo,
    Length,
    NumberRange,
    Optional,
)


class LoginForm(FlaskForm):
    username = StringField("Benutzername", validators=[DataRequired()])
    password = PasswordField("Passwort", validators=[DataRequired()])
    remember = BooleanField("Angemeldet bleiben")
    submit = SubmitField("Anmelden")


class PasswordChangeForm(FlaskForm):
    current_password = PasswordField("Aktuelles Passwort", validators=[DataRequired()])
    password = PasswordField("Neues Passwort", validators=[DataRequired(), Length(min=4)])
    confirm = PasswordField(
        "Neues Passwort wiederholen",
        validators=[DataRequired(), EqualTo("password", message="Passwörter stimmen nicht überein.")],
    )
    submit = SubmitField("Passwort ändern")


class UserForm(FlaskForm):
    """Konto anlegen oder bearbeiten (Passwort beim Bearbeiten optional)."""

    username = StringField("Benutzername", validators=[DataRequired(), Length(min=2, max=64)])
    display_name = StringField("Anzeigename", validators=[DataRequired(), Length(max=64)])
    avatar = StringField("Avatar (Emoji)", validators=[Length(max=8)], default="🙂")
    role = SelectField("Rolle", choices=[("child", "Kind"), ("parent", "Elternteil")])
    password = PasswordField("Passwort", validators=[Optional(), Length(min=4)])
    confirm = PasswordField(
        "Passwort wiederholen",
        validators=[EqualTo("password", message="Passwörter stimmen nicht überein.")],
    )
    enabled = BooleanField("Konto aktiv", default=True)
    submit = SubmitField("Speichern")


class TaskForm(FlaskForm):
    title = StringField("Aufgabe", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Beschreibung", validators=[Optional(), Length(max=2000)])
    icon = StringField("Symbol (Emoji)", validators=[Length(max=8)], default="⭐")
    points = IntegerField("Punkte", validators=[DataRequired(), NumberRange(min=1, max=1000)])
    recurrence = SelectField(
        "Wiederholung",
        choices=[("daily", "täglich"), ("weekly", "wöchentlich"), ("once", "einmalig")],
    )
    assignees = SelectMultipleField("Für welche Kinder?", coerce=int)
    requires_approval = BooleanField("Muss von mir bestätigt werden", default=True)
    active = BooleanField("Aktiv", default=True)
    submit = SubmitField("Speichern")


class RewardForm(FlaskForm):
    title = StringField("Belohnung", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Beschreibung", validators=[Optional(), Length(max=2000)])
    icon = StringField("Symbol (Emoji)", validators=[Length(max=8)], default="🎁")
    cost = IntegerField("Kosten in Punkten", validators=[DataRequired(), NumberRange(min=1, max=100000)])
    stock = IntegerField(
        "Verfügbare Anzahl (leer = unbegrenzt)", validators=[Optional(), NumberRange(min=0, max=10000)]
    )
    active = BooleanField("Im Shop sichtbar", default=True)
    submit = SubmitField("Speichern")


class PointAdjustForm(FlaskForm):
    child_id = SelectField("Kind", coerce=int, validators=[DataRequired()])
    delta = IntegerField(
        "Punkte (negativ = Abzug)", validators=[DataRequired(), NumberRange(min=-10000, max=10000)]
    )
    reason = StringField("Grund", validators=[DataRequired(), Length(max=255)])
    submit = SubmitField("Buchen")


class DecisionForm(FlaskForm):
    """Nur für CSRF-Schutz der Freigabe-Buttons."""

    note = StringField("Notiz", validators=[Optional(), Length(max=255)])
    submit = SubmitField("OK")
