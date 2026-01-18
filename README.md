# SAT Reševanje Conwayjeve Igre Življenja

## Pregled

Ta projekt implementira Conwayjevo Igro Življenja z funkcionalnostjo **povratnega SAT reševanja** (backward SAT solving). Omogoča iskanje začetnih stanj, ki vodijo do določenega ciljnega stanja po določenem številu generacij. Projekt vključuje dve vizualizacijski aplikaciji z interaktivnimi vmesniki.

## Kazalo

1. [Uvod](#uvod)
2. [Značilnosti](#značilnosti)
3. [Namestitev](#namestitev)
4. [Struktura Projekta](#struktura-projekta)
5. [Uporaba](#uporaba)
6. [Tehnične Podrobnosti](#tehnične-podrobnosti)
7. [Algoritmi](#algoritmi)
8. [Vizualizacije](#vizualizacije)
9. [Primeri Uporabe](#primeri-uporabe)
10. [Napredne Nastavitve](#napredne-nastavitve)
11. [Omejitve in Znane Težave](#omejitve-in-znane-težave)
12. [Literatura in Reference](#literatura-in-reference)

---

## Uvod

### Kaj je Conwayjeva Igra Življenja?

Conwayjeva Igra Življenja je celični avtomat, ki ga je leta 1970 razvil matematik John Conway. Deluje na dvodimenzionalni mreži celic, kjer vsaka celica lahko biti živa (1) ali mrtva (0). Simulacija poteka v diskretnih generacijah, kjer se stanje vsake celice določi na podlagi njenih osmih sosedov.

### Pravila

1. **Rojstvo**: Mrtva celica z natanko 3 živimi sosedi postane živa.
2. **Preživetje**: Živa celica z 2 ali 3 živimi sosedi preživi.
3. **Smrt**: V vseh drugih primerih celica umre ali ostane mrtva.

### Problem Povratnega Reševanja

Klasična simulacija poteka naprej v času: iz začetnega stanja izračunamo prihodnje generacije. **Povratno reševanje** pa išče začetno stanje, ki po določenem številu korakov vodi do danega ciljnega stanja. To je pa NP-težek problem, ki ga tu rešujemo z uporabo SAT (Boolean Satisfiability) reševalnika.

---

## Značilnosti

### Osnovne Funkcionalnosti

-  **Simulacija Conwayjeve Igre Življenja** - standardna naprej simulacija
-  **Povratno SAT reševanje** - iskanje začetnih stanj za dane ciljne konfiguracije
-  **Iterativna minimizacija** - iskanje manjših začetnih stanj
-  **Shranjevanje in nalaganje** konfiguracij
-  **Interaktivni vmesniki** z različnimi vizualizacijskimi načini

### Napredne Funkcionalnosti

-  **Drevesna vizualizacija** - prikaz več možnih prednikov
-  **Iskanje prednikov** - avtomatsko iskanje več generacij nazaj
-  **Statistike** - število živih celic, globina iskanja

---

## Namestitev

### Zahteve

- Python 3.7 ali novejši
- pip (Python Package Manager)

## Struktura Projekta

```
conway-sat/
├── src/
│   ├── game_of_life.py      # Osnovna implementacija igre
│   ├── sat_solver.py         # SAT reševanje za povratno iskanje
│   ├── visualization.py      # Osnovna vizualizacija
│   ├── tree_vis.py           # Drevesna vizualizacija
│   └── main.py               # Preprosta konzolna animacija
├── data/
│   ├── *.npz                 # Shranjene konfiguracije
├── requirements.txt          # Python odvisnosti
└── README.md                 # Ta dokumentacija
```

### Opis Datotek

#### `game_of_life.py`
Osrednja implementacija Conwayjeve Igre Življenja:
- `GameOfLife` razred - upravljanje z mrežo in simulacijo
- Metode: `step()`, `set_pattern()`, `count_alive()`

#### `sat_solver.py`
SAT reševanje za povratno iskanje:
- `solve_initial_for_target()` - rešuje začetno stanje za dano ciljno stanje
- `solve_initial_minimal_iterative()` - iterativno minimizira število živih celic
- Uporablja Z3 SAT reševalnik

#### `visualization.py`
Osnovna interaktivna vizualizacija:
- Grafični vmesnik z pygame
- Shranjevanje/nalaganje konfiguracij
- Povratno reševanje na pritisk tipke

#### `tree_vis.py`
Napredna drevesna vizualizacija:
- Prikaz več možnih prednikov hkrati
- Avtomatsko iskanje v globino
- Interaktivna navigacija po drevesu


---

## Uporaba

### Osnovna Vizualizacija

Zaženite osnovno vizualizacijo:

```bash
python src/visualization.py
```

#### Tipkovne Kratice

- **SPACE** - Zaustavi/nadaljuj simulacijo
- **B** - Zaženi povratno reševanje (backward solve)
- **C** - Počisti mrežo
- **→ (Desna puščica)** - Korak naprej za eno generacijo
- **Klik na mrežo** - Preklopi stanje celice (živa/mrtva)
- **Save gumb** - Shrani trenutno konfiguracijo
- **Load gumb** - Naloži shranjeno konfiguracijo

#### Postopek Povratnega Reševanja

1. Ustvarite ali naložite ciljno konfiguracijo
2. Pritisnite **B** za začetek povratnega reševanja
3. Program poišče začetno stanje, ki po 1 generaciji vodi do ciljnega stanja
4. Rezultat se prikaže na mreži

### Drevesna Vizualizacija

Zaženite napredno drevesno vizualizacijo:

```bash
python src/tree_vis.py
```

#### Značilnosti Drevesne Vizualizacije

- **Leva stran**: Interaktivna mreža Conwayjeve Igre Življenja
- **Desna stran**: Drevo možnih prednikov

#### Tipkovne Kratice

- **SPACE** - Zaustavi/nadaljuj simulacijo
- **B** - Zaženi/ustavi avtomatsko iskanje prednikov
- **S** - Shrani konfiguracijo
- **C** - Počisti mrežo
- **→ (Desna puščica)** - Korak naprej
- **HOME** - Ponastavi zoom in pozicijo drevesa
- **CTRL + Kolesce miške** - Zoom drevesa
- **SHIFT + Kolesce miške** - Horizontalno pomikanje
- **Kolesce miške** - Vertikalno pomikanje
- **Klik na vozlišče** - Pokaži to stanje na mreži

#### Gumbi

- **Save** - Shrani trenutno konfiguracijo
- **Load** - Naloži konfiguracijo
- **Clear** - Počisti mrežo
- **Step** - Korak naprej
- **Go Deeper** - Zaženi avtomatsko iskanje prednikov

#### Avtomatsko Iskanje Prednikov

Ko pritisnete "Go Deeper" ali tipko **B**, program začne avtomatsko iskati prednike trenutnega stanja v globino:

1. Za vsako vozlišče poišče prednika (stanje, ki po 1 generaciji vodi do tega stanja)(v primeru backtrackinga pa išče prednika ki se dovolj razlikuje glede na metriko podobnosti)
2. Če najde več kot 4 možne prednike, se vrne nazaj (backtracking)
3. Če ne najde prednika, se vrne en korak nazaj
4. Z 15% verjetnostjo se vrne več korakov nazaj (naključno med 1 in globino)

---

## Tehnične Podrobnosti

### Implementacija Conwayjeve Igre Življenja

Simulacija uporablja NumPy za učinkovito izračunavanje:

```python
neighbors = sum(
    np.roll(np.roll(self.grid, i, 0), j, 1)
    for i in (-1, 0, 1)
    for j in (-1, 0, 1)
    if (i, j) != (0, 0)
)
```

Ta pristop uporablja ciklične premike (`np.roll`) za izračun števila sosedov za vse celice hkrati, kar je veliko hitreje kot iteriranje po posameznih celicah.

### SAT Reševanje

#### Boolean Satisfiability Problem (SAT)

SAT problem vpraša, ali obstaja dodelitev Boolean spremenljivk, ki zadovolji dano logično formulo. V našem primeru:

- **Spremenljivke**: Vsaka celica v vsaki generaciji (Boolean: živa/mrtva)
- **Omejitve**: Pravila Conwayjeve Igre Življenja med generacijami
- **Cilj**: Najti začetno stanje, ki vodi do danega ciljnega stanja

#### Z3 Reševalnik

Projekt uporablja Z3, močan SAT/SMT reševalnik od Microsoft Research. Kljub temu, da je Boolean satisfiability problem NP-poln (kar pomeni, da v najslabšem primeru zahteva eksponenten čas), Z3 omogoča praktično reševanje za veliko primerov zahvaljujoč naprednim optimizacijskim tehnikam:

- **Conflict-Driven Clause Learning (CDCL)** - učenje iz konfliktov za hitrejše izločanje neuspešnih vej
- **Hevristike za razvejanje** - pametna izbira spremenljivk za razvejanje
- **Unit propagation** - hitro propagiranje enostavnih omejitev
- **Restart strategije** - ponovno začetje z novimi hevristikami
- **Učinkovite podatkovne strukture** - optimizirane za hitro iskanje in posodabljanje

Za večje primere ali več korakov nazaj se čas reševanja močno poveča, vendar Z3 še vedno omogoča reševanje, ki bi bilo z naivnimi pristopi praktično nemogoče. 
#### Struktura SAT Problema

Za iskanje začetnega stanja, ki po `steps` generacijah vodi do ciljnega stanja:

1. **Ustvarimo Bool spremenljivke** za vsako celico v vsaki generaciji:
   ```
   t0_y_x  - stanje celice (y,x) v generaciji 0
   t1_y_x  - stanje celice (y,x) v generaciji 1
   ...
   tN_y_x  - stanje celice (y,x) v generaciji N (ciljno stanje)
   ```

2. **Dodamo omejitve prehodov** med generacijami:
   - Za vsako celico v generaciji t+1 določimo, kako je odvisna od sosedov v generaciji t
   - To kodira pravila Conwayjeve Igre Življenja

3. **Fiksiramo ciljno stanje**:
   - Vse celice v generaciji N morajo biti enake ciljnemu stanju

4. **Dodamo dodatne omejitve**:
   - Omejimo število živih celic v začetnem stanju (`max_ones`)
   - Omejimo območje, kjer lahko živijo celice v začetnem stanju (`restrict`)
   - Izključimo že preizkušene konfiguracije (`exclude_grids`)

#### Optimizacije

- **Preizračun sosedov**: Namesto da izračunavamo sosede vsakič, jih preizračunamo enkrat
- **Iterativna minimizacija**: Postopoma zmanjšujemo maksimalno število živih celic, da najdemo minimalno rešitev
- **Timeout**: Vsak SAT klic ima timeout, da preprečimo neskončno čakanje

---

## Algoritmi

### Algoritem Povratnega Reševanja

Najbolj bistveno izboljšavo hitrosti smo dobili s tem da pri iskanju smo iskali prejšno stanje vedno samo v prostoru sestavljen iz unij vseh soseščin živih celic. Utemeljitev je da na celice ki so v ciljnem stanju žive uplivajo lahko v enem koraku samo njihove sosede. Ta pristop seveda deluje samo ko je steps=1, vendar to se je iskazalo za optimalno v vsakem smislu, saj za steps>2 je bilo skoraj nemogoče dobiti rešitev v razumnem času. 

Utemeljitev odločitve iskanja stanj s čim manj živih celic je pa direktna posledica prejšne ugotovitve. Manj živih celic ponavadi pomeni manj soseščin za pregledovanje v naslednjih korakih iskanja (oz. manjše bounding boxe -> hitrejše rezultate).
```
Funkcija solve_initial_for_target(target, steps, max_ones):
    1. Ustvari Bool spremenljivke za vse generacije
    2. Dodaj omejitve prehodov med generacijami
    3. Fiksiraj ciljno stanje (zadnja generacija)
    4. Omeji število živih celic v začetnem stanju
    5. Po potrebi omeji območje začetnih celic
    6. Pošlji problem Z3 reševalniku
    7. Če je SAT (satisfiable):
       - Izlušči model (vrednosti spremenljivk)
       - Vrni začetno stanje
    8. Če je UNSAT (unsatisfiable):
       - Vrni None
```

### Iterativna Minimizacija

```
Funkcija solve_initial_minimal_iterative(target, start_bound):
    1. Začni z max_ones = start_bound
    2. Dokler max_ones >= 0:
       a. Poskusi najti rešitev z kvečjemu max_ones
       b. Če najdemo rešitev:
          - Shrani kot najboljšo
          - Zmanjšaj max_ones na (število_živih - naključno(1-3))
       c. Če ne najdemo:
          - Končaj, vrni najboljšo rešitev
    3. Vrni najboljšo rešitev
```

Ta pristop iterativno zmanjšuje mejo, dokler ne najdemo čim manjše (ne pa vedno najmanjše zaradi preskokov meje ali omejitev časa) rešitve.

### Drevesno Iskanje Prednikov

```
Funkcija search_worker (v ozadju):
    1. Dokler iskanje aktivno:
       a. Če trenutno vozlišče ima > 4 otrok:
          - Vrni se nazaj (backtrack)
       b. Poišči prednika trenutnega stanja
       c. Če najdemo prednika:
          - Dodaj kot otroka
          - Premakni se na novega prednika
       d. Če ne najdemo:
          - Z 15% verjetnostjo: vrni se naključno(1-globina) korakov
          - Sicer: vrni se 1 korak nazaj
```

---

## Vizualizacije

### Barvna Kodiranja

Obe vizualizaciji uporabljata barvno kodiranje glede na število sosedov:

- **Bela** - Mrtva celica
- **Temno modra → Zelena → Rumena** - Žive celice z različnim številom sosedov (0-8)

Barve so iz palete Viridis, ki omogoča dobro razlikovanje različnih gostot.

### Primer Drevesne Vizualizacije

Spodaj je prikazan primer najkompleksnejše vizualizacije - drevesnega iskanja prednikov. Ta animacija prikazuje, kako program avtomatsko raziskuje možne prednike konfiguracije, gradijo se veje drevesa, ki predstavljajo različne možne zgodovine stanj. To je najnaprednejša funkcionalnost projekta, ki omogoča razumevanje kompleksnih odnosov med različnimi generacijami Conwayjeve Igre Življenja.

<div align="center">
  <img src="primer_tree.gif" alt="Primer drevesne vizualizacije" width="90%">
</div>

## Primeri Uporabe

### Primer 1: Iskanje Začetnega Stanja

1. Zaženite `visualization.py`
2. Ustvarite ali naložite ciljno konfiguracijo
3. Pritisnite **B** za povratno reševanje
4. Program poišče začetno stanje (1 korak nazaj) , ki vodi do ciljnega stanja

Priporočamo majhne ciljne konfiguracije če hočete hitrejše iskanje
### Primer 2: Raziskovanje Prednikov

1. Zaženite `tree_vis.py`
2. Naložite konfiguracijo
3. Pritisnite **B** ali kliknite "Go Deeper"
4. Program začne avtomatsko iskati prednike
5. Opazujte, kako se drevo razvija
6. Kliknite na vozlišče, da vidite to stanje

Spet priporočamo majhne ciljne konfiguracije če hočete hitrejše iskanje
### Primer 3: Shranjevanje in Nalaganje

1. Ustvarite konfiguracijo (kliknite na mrežo ali naložite)
2. Kliknite **Save** ali pritisnite **S**
3. Konfiguracija se shrani v `data/` mapo kot `.npz` datoteka
4. Za nalaganje kliknite **Load** in izberite datoteko

---

## Napredne Nastavitve

### Parametri SAT Reševanja

V `sat_solver.py` lahko prilagodite:

- `timeout_ms`: Timeout za vsak SAT klic (privzeto: 10000ms , ko uporabljamo drevesnega reševanja pa adaptivno nastavimo timeout glede na globino na kateri trenutno preiskujemo)
- `max_ones`: Maksimalno število živih celic v prejšnem stanju
- `restrict`: Ali omejiti območje začetnih celic
- `steps`: Število generacij nazaj (trenutno: 1 za več se je iskazalo da problem postane bistveno težji rešiti v razumnem času) 


---

## Omejitve in Znane Težave

### Računska Zahtevnost

SAT reševanje je eksponentno kompleksno v najslabšem primeru. Za večje mreže ali več korakov nazaj (>2) lahko reševanje traja zelo dolgo ali celo timeout.

---

## Literatura in Reference

- [Conway's Game of Life - Wikipedia](https://en.wikipedia.org/wiki/Conway%27s_Game_of_Life)
- [Z3 Theorem Prover](https://github.com/Z3Prover/z3)
- [Boolean Satisfiability Problem](https://en.wikipedia.org/wiki/Boolean_satisfiability_problem)
- [SAT Solving in Practice](https://www.cs.utexas.edu/~isil/cs389L/sat.pdf)

