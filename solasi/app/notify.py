"""Benachrichtigungen bei Störungen (mit Verzögerung, Sperrzeit und Entwarnung)."""
import logging
import time

log = logging.getLogger("solasi.notify")

MESSAGES = {
    "meter": ("Zähler ohne Meldung",
              "Der Stromzähler meldet nichts mehr. Die Speicher wurden zur Sicherheit auf 0 W gesetzt.",
              "Der Stromzähler meldet wieder Werte. Die Regelung läuft weiter."),
    "offline": ("Speicher nicht erreichbar",
                "Mindestens ein Speicher liefert keinen Ladestand mehr.",
                "Alle Speicher liefern wieder Werte."),
    "empty": ("Speicher leer",
              "Alle Speicher haben den Mindest-Ladestand erreicht. Es wird nicht weiter entladen.",
              "Die Speicher sind wieder über dem Mindest-Ladestand."),
    "curtail": ("Einspeisung trotz vollem Speicher",
                "Der Speicher ist voll, es wird aber weiter eingespeist. Die Abregelung greift offenbar nicht, "
                "SOLASI weicht auf Verbraucher aus.",
                "Die Einspeisung bei vollem Speicher ist wieder beendet."),
    "errors": ("Steuerbefehle schlagen fehl",
               "Mehrere Befehle an die Speicher sind fehlgeschlagen. Bitte das Protokoll prüfen.",
               "Befehle gehen wieder durch."),
}


class Notifier:
    def __init__(self, ctrl):
        self.ctrl = ctrl
        self.since = {}      # Ereignis -> Beginn der Störung
        self.notified = {}   # Ereignis -> bereits gemeldet
        self.last_sent = {}  # Ereignis -> Zeitpunkt der letzten Meldung

    @property
    def cfg(self):
        return self.ctrl.cfg["notify"]

    async def send(self, title, message, tag="solasi"):
        service = self.cfg["service"]
        if not service:
            return False
        domain, _, name = service.partition(".")
        data = {"title": title, "message": message}
        if domain == "persistent_notification":
            name, data = "create", {**data, "notification_id": f"solasi_{tag}"}
        try:
            await self.ctrl.ha.call_service(domain, name or "send_message", data)
            self.ctrl.event("info", f"Benachrichtigung gesendet: {title}")
            return True
        except Exception as e:  # noqa: BLE001
            self.ctrl.event("error", f"Benachrichtigung fehlgeschlagen: {e}")
            return False

    async def check(self, problems, now=None):
        """problems: {Ereignis: bool}. Meldet nach Verzögerung, hält die Sperrzeit ein, sendet Entwarnung."""
        cfg = self.cfg
        if not cfg["service"]:
            return
        now = time.monotonic() if now is None else now
        for key, active in problems.items():
            if not cfg["events"].get(key, True):
                continue
            title, bad, good = MESSAGES[key]
            if active:
                self.since.setdefault(key, now)
                waited = now - self.since[key]
                cooled = now - self.last_sent.get(key, -1e9) >= cfg["cooldown_min"] * 60
                if waited >= cfg["delay_min"] * 60 and not self.notified.get(key) and cooled:
                    if await self.send(f"⚠️ {title}", bad, key):
                        self.last_sent[key] = now
                    self.notified[key] = True       # auch bei Fehlschlag nicht im Sekundentakt wiederholen
            else:
                self.since.pop(key, None)
                if self.notified.pop(key, False) and cfg.get("recovery", True):
                    await self.send(f"✅ {title} behoben", good, key)
