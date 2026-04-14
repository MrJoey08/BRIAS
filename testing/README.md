# Testing Map

Gooi hier bestanden in die je wil testen voordat ze live gaan.

## Hoe het werkt

- Alles in deze map staat op de branch `claude/setup-testing-folder-7iDPp`
- Die branch is **niet** de live site — Vercel maakt er een aparte **preview URL** voor
- Zodra je tevreden bent, verplaats je het bestand naar de juiste map en merge je naar `main`

## Workflow

1. Zet je testbestand hier neer (bijv. `testing/app.html`)
2. Commit & push naar deze branch
3. Vercel geeft je een preview URL — open die en test
4. Werkt het? Verplaats het naar de echte map (`frontend/app.html` o.i.d.)
5. Merge naar `main` → live

## Wat staat hier niet in productie?

Vercel deployt de `main` branch als live site. Deze branch is alleen een preview.
Dus wat je hier test, ziet niemand anders — tenzij je ze de preview URL geeft.
