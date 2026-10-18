"""Konten, Rollen und Anmeldung für den eigenen Port.

Passwörter werden nie im Klartext gespeichert (scrypt mit zufälligem Salz). Zu viele Fehlversuche sperren
Anmeldung für Name + Adresse zeitweise. Sitzungen liegen nur im Speicher (nach einem Neustart neu anmelden).
Über Home Assistant (Ingress) ist man bereits angemeldet und gilt als Besitzer.
"""
import hashlib
import hmac
import re
import secrets
import time

from util import load_json, save_json

ROLES = {"owner": "Besitzer", "member": "Mitbewohner", "viewer": "Nur lesen"}
MEMBER_POST = {"/api/goals/mode", "/api/goals/set", "/api/goals/preview", "/api/kill", "/api/resume", "/api/locks"}
MIN_PW = 8
MAX_FAILS, LOCK_S, SESSION_S = 5, 300, 30 * 86400
NAME_RE = re.compile(r"^[\w .@-]{2,32}$")


def _hash(pw, salt):
    return hashlib.scrypt(pw.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)


class AccountStore:
    def __init__(self, path, clock=time.time):
        self.path, self.clock = path, clock
        self.users = load_json(path, {}).get("users", {})
        self.sessions = {}      # Token -> (Name, Ablauf)
        self.fails = {}         # (Name, Adresse) -> (Anzahl, gesperrt bis)

    def _save(self):
        save_json(self.path, {"users": self.users})

    def has_any(self):
        return bool(self.users)

    def list(self):
        return [{"name": n, "role": u["role"], "role_label": ROLES[u["role"]]} for n, u in sorted(self.users.items(), key=lambda x: x[0].lower())]

    def _key(self, name):
        n = str(name or "").strip()
        for k in self.users:
            if k.lower() == n.lower():
                return k
        return None

    def create(self, name, pw, role):
        name = str(name or "").strip()
        if not NAME_RE.match(name):
            return "Name: 2–32 Zeichen (Buchstaben, Ziffern, Leerzeichen, . _ - @)"
        if role not in ROLES:
            return "Unbekannte Rolle"
        if len(str(pw or "")) < MIN_PW:
            return f"Das Passwort braucht mindestens {MIN_PW} Zeichen"
        if self._key(name):
            return "Diesen Namen gibt es schon"
        salt = secrets.token_bytes(16)
        self.users[name] = {"salt": salt.hex(), "hash": _hash(pw, salt).hex(), "role": role}
        self._save()
        return None

    def set_password(self, name, pw):
        k = self._key(name)
        if not k:
            return "Konto nicht gefunden"
        if len(str(pw or "")) < MIN_PW:
            return f"Das Passwort braucht mindestens {MIN_PW} Zeichen"
        salt = secrets.token_bytes(16)
        self.users[k].update(salt=salt.hex(), hash=_hash(pw, salt).hex())
        self._drop_sessions(k)
        self._save()
        return None

    def set_role(self, name, role):
        k = self._key(name)
        if not k or role not in ROLES:
            return "Konto oder Rolle unbekannt"
        if self.users[k]["role"] == "owner" and role != "owner" and self._owners() <= 1:
            return "Es muss mindestens ein Besitzer bleiben"
        self.users[k]["role"] = role
        self._drop_sessions(k)
        self._save()
        return None

    def delete(self, name):
        k = self._key(name)
        if not k:
            return "Konto nicht gefunden"
        if self.users[k]["role"] == "owner" and self._owners() <= 1:
            return "Der letzte Besitzer kann nicht gelöscht werden"
        del self.users[k]
        self._drop_sessions(k)
        self._save()
        return None

    def _owners(self):
        return sum(1 for u in self.users.values() if u["role"] == "owner")

    def _drop_sessions(self, name):
        self.sessions = {t: v for t, v in self.sessions.items() if v[0] != name}

    def login(self, name, pw, addr=""):
        """-> (Token|None, Fehlertext|None)"""
        now = self.clock()
        fk = (str(name or "").strip().lower(), addr)
        cnt, until = self.fails.get(fk, (0, 0))
        if until > now:
            return None, f"Zu viele Versuche. Bitte in {int((until - now) // 60) + 1} Min. erneut versuchen."
        k = self._key(name)
        ok = False
        if k:
            u = self.users[k]
            ok = hmac.compare_digest(_hash(str(pw or ""), bytes.fromhex(u["salt"])).hex(), u["hash"])
        else:
            _hash(str(pw or ""), b"0" * 16)         # gleiche Rechenzeit, damit Namen nicht erraten werden können
        if not ok:
            cnt += 1
            self.fails[fk] = (0, now + LOCK_S) if cnt >= MAX_FAILS else (cnt, 0)
            return None, "Name oder Passwort stimmt nicht"
        self.fails.pop(fk, None)
        tok = secrets.token_urlsafe(32)
        self.sessions[tok] = (k, now + SESSION_S)
        return tok, None

    def user_for(self, token):
        v = self.sessions.get(token or "")
        if not v:
            return None
        if v[1] < self.clock() or v[0] not in self.users:
            self.sessions.pop(token, None)
            return None
        return {"name": v[0], "role": self.users[v[0]]["role"]}

    def logout(self, token):
        self.sessions.pop(token or "", None)


def allowed(role, method, path):
    """Darf diese Rolle die Anfrage stellen? (Kontenverwaltung nur für Besitzer.)"""
    if path.startswith("/api/accounts"):
        return role == "owner"
    if role == "owner":
        return True
    if method in ("GET", "HEAD"):
        return True
    return role == "member" and method == "POST" and path in MEMBER_POST
