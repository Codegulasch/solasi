# SOLASI – Home-Assistant-Add-on („App“)

Lokale Installation (ohne GitHub):

1. Ordner `solasi` nach `/addons/solasi` auf dem Home-Assistant-Rechner kopieren
   (Samba-Freigabe „addons“ oder Add-on „File editor“/„Terminal“).
2. *Einstellungen → Add-ons (bzw. Apps) → Store → ⋮ → Nach Updates suchen*.
3. Unter **Lokale Add-ons** „SOLASI“ öffnen → **Installieren** → **Starten**
   → **In der Seitenleiste anzeigen** aktivieren.

Alles Weitere steht im Reiter „Dokumentation“ des Add-ons (DOCS.md).

Tests: `pip install aiohttp pytest pytest-asyncio && python -m pytest tests`

Dashboard-Karte: SOLASI installiert `solasi-card.js` automatisch nach `<config>/www/solasi/`.
Details im Reiter „Dashboard-Karte“ der Oberfläche bzw. in DOCS.md.
