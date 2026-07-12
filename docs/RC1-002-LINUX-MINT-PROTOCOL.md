# RC1-002 — Linux Mint telepítési jegyzőkönyv

> **Canonical QA framework:** [docs/qa/LINUX-RC1-CHECKLIST.md](qa/LINUX-RC1-CHECKLIST.md)  
> This document is a Hungarian locale instance of the Linux RC1 protocol.

**Verzió:** 0.3.0-alpha (RC1)  
**Platform:** Linux Mint 21+ / Ubuntu 22.04+ x86_64  
**Csomag:** `ProjectX.deb` (GitHub Release)  
**Dátum:** _______________  
**Tesztelő:** _______________  
**Gép / VM:** _______________

---

## Előfeltétel — GitHub Release

A jegyzőkönyv **GitHub Release-ről letöltött** `ProjectX.deb` fájllal futtatható.  
Ellenőrizd a release mellékleteit:

- `ProjectX.deb`
- `ProjectX.AppImage` (opcionális, ebben a protokollban nem kell)
- `SHA256SUMS`

Opcionális integritás-ellenőrzés:

```bash
sha256sum -c SHA256SUMS
```

---

## Konfigurációs politika (RC1 döntés)

| Esemény | Viselkedés | RC1 elvárás |
|---------|------------|-------------|
| `dpkg -r projectx` / Software Manager eltávolítás | `/opt/projectx` és menü ikon törlődik | PASS |
| Felhasználói adatok | `~/.local/share/projectx/` **megmarad** | **PASS — szándékos** |
| Újratelepítés | Korábbi beállítások visszatérnek | PASS |

**RC1 döntés:** konfiguráció **megmarad** eltávolításkor (Windows-szerű: adatmegőrzés).  
Teljes adattörlés csak kézzel: `rm -rf ~/.local/share/projectx/`

---

## Előkészítés — régi Project X teljes eltávolítása

Végezd el **mindkét** lehetséges telepítési mód ellenőrzését:

### A) Korábbi .deb telepítés

```bash
sudo dpkg -r projectx
# vagy Software Manager → Project X → Eltávolítás
```

### B) Fejlesztői forrásfa telepítés (ha volt)

```bash
installer/linux/uninstall.sh
```

### C) Manuális maradványok (opcionális ellenőrzés)

```bash
dpkg -l projectx          # nincs telepítve
ls /opt/projectx          # nem létezik
ls ~/.local/share/applications/projectx.desktop   # nem létezik (dev install után)
ls ~/Desktop/"Project X.desktop"                    # nem létezik
```

Megjegyzés: `~/.local/share/projectx/` **maradhat** — ez felhasználói adat, nem régi csomag.

---

## Teszt checklist

Jelölés: ☐ → futás közben pipáld; **Eredmény:** PASS / FAIL / N/A

| # | Lépés | Elvárás | Eredmény | Megjegyzés |
|---|-------|---------|----------|------------|
| 1 | Régi Project X teljes eltávolítása | Nincs `projectx` csomag, nincs `/opt/projectx` | | |
| 2 | Új `ProjectX.deb` letöltése GitHub Release-ről | Fájl a Letöltések mappában | | |
| 3 | Dupla kattintás a `.deb` fájlon | | | |
| 4 | Csomagkezelő megnyílik | GDebi vagy Software Install | | |
| 5 | Csomag neve | **Project X** | | |
| 6 | Leírás | **Professional Maritime Monitoring Platform** | | |
| 7 | Ikon megfelelő | Project X logó, nem generikus | | |
| 8 | Telepítés gomb | Telepítés elindul | | |
| 9 | Jelszó kérés | sudo/jelszó ablak megjelenik | | |
| 10 | Telepítés sikeres | „Installed” / „Telepítve” | | |
| 11 | Asztali ikon létrejött | `Project X.desktop` az asztalon | | |
| 12 | Menü ikon létrejött | Project X a Mint menüben | | |
| 13 | Menü neve | **Project X** | | |
| 14 | Első indítás | Alkalmazás elindul | | |
| 15 | Terminál NEM jelenik meg | Nincs fekete terminál ablak | | |
| 16 | First Run Wizard működik | Varázsló végigjárható | | |
| 17 | Bezárás | Alkalmazás tiszta kilépés | | |
| 18 | Újraindítás | Gép/VM újraindítása | | |
| 19 | Menüből indul | Dupla katt → app indul, nincs terminál | | |
| 20 | Asztalról indul | Dupla katt asztali ikon → app indul | | |
| 21 | Eltávolítás | Software Manager vagy `sudo dpkg -r projectx` | | |
| 22 | Menü ikon eltűnik | Project X nincs a menüben | | |
| 23 | Asztali ikon eltűnik | `Project X.desktop` nincs az asztalon | | |
| 24 | Konfiguráció | `~/.local/share/projectx/` **megmarad** (RC1 döntés) | | |
| 25 | RC1 jegyzőkönyv lezárása | Minden kritikus lépés PASS | | |

---

## Ismert korlátok / elfogadható FAIL

| Tétel | Megjegyzés |
|-------|------------|
| Telepítés után azonnali indítás | GDebi nem mindig ad `SUDO_USER`-t; asztali ikon / indítás postinst-től függ |
| Software Manager vs GDebi | Mindkettővel érdemes külön futtatni, ha az egyik FAIL |
| Asztali ikon eltávolítás | `postrm` a telepítő felhasználót `/var/lib/projectx/install-user` fájlból olvassa |

---

## Gyors parancsok (referencia)

```bash
# Telepítés (terminálból)
sudo dpkg -i ~/Downloads/ProjectX.deb
sudo apt-get install -f

# Indítás
/usr/bin/projectx

# Eltávolítás
sudo dpkg -r projectx

# Konfiguráció helye
ls -la ~/.local/share/projectx/

# Csomag metaadat ellenőrzés (telepítés előtt)
dpkg-deb -I ProjectX.deb | head -20
```

---

## Lezárás

| Mező | Érték |
|------|-------|
| **Összesített eredmény** | PASS / FAIL / FELTÉTELES |
| **Blokkoló hibák** | |
| **RC1 publikálható?** | Igen / Nem |
| **Aláírás / dátum** | |

**Kritikus (blokkoló) tételek:** 5, 6, 10, 13, 15, 16, 19, 22
