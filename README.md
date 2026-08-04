# 🏁 Journeyman — F1

**[▶ Play now → f1-journeyman.netlify.app](https://f1-journeyman.netlify.app)**

Guess the mystery Formula 1 driver from their career — revealed one season at a
time. A daily puzzle for people who know their grids: read the entries, the
starts, the podiums and the DNFs, and name the driver before you run out of laps.

Back on the grid? There are sister games:
**[Journeyman — AFL](https://footy-journeyman.netlify.app)**,
**[Journeyman — MLB](https://mlb-journeyman.netlify.app)**,
**[Journeyman — NBA](https://nba-journeyman.netlify.app)** and
**[Globetrotter — Countries](https://country-globetrotter.netlify.app)** (guess the country from five clues)
— all reachable from the *Play our other games* button at the top of the page.

## How to play

A mystery driver's career record appears one season at a time, in a random
order. Each row shows the **year**, race **entries** and **starts**, then
**wins**, **podiums**, **poles**, **fastest laps** and **DNFs** for that season.

- Every wrong guess reveals **another season**. The fewer seasons you need, the
  better the drive.
- After each miss you get **clue chips**: whether you and the answer raced in
  the same season, whether you reached the same level, and whether the mystery
  driver debuted earlier or later than your guess.
- **Grand Prix mode:** 8 guesses. **Sprint mode:** 5 guesses, no clue chips, no
  bonus reveals.

Teams, engines, championship positions and points are all in the source data and
all deliberately left out of the table. Any one of them hands you the answer —
the constructor most of all.

Come back every day for a fresh round, share your result grid, and chase your
streak.

## Modes

- **Round** — one mystery driver a day, the same for everyone. Always drawn from
  drivers with 30+ starts whose careers ran into 1980 or later, so shared result
  grids are comparable.
- **Testing** — unlimited random drivers whenever you want more. The **minimum
  race starts** and **earliest era** settings apply here only.

## Building the data

`drivers.json` is generated from [F1DB](https://github.com/f1db/f1db), the
open-source all-time Formula 1 database, which is rebuilt after every race
weekend:

```
pip install pandas requests
python3 build_drivers.py drivers.json
```

The script resolves the latest F1DB release, downloads `f1db-csv.zip`, and
aggregates it into ~350 guessable drivers and ~220 possible answers. That answer
pool is a deliberate superset — the game's settings filter it client-side, so
changing them never needs a rebuild. Reserve and test-driver seasons (registered
for a year but never entered a race) are dropped: an all-zeros row reveals
nothing, and keeping them would misdate half the grid's debuts.

[`.github/workflows/refresh-data.yml`](.github/workflows/refresh-data.yml) runs
this weekly and commits the result only when the numbers move.

## Credits

Driver statistics via [F1DB](https://github.com/f1db/f1db) (CC BY 4.0). Not
affiliated with Formula 1, the FIA or any team — no team logos, driver photos or
F1 word marks are used, just public career statistics. Built by
[Nadav Moskow](https://buymeacoffee.com/nadavmoskow); if you enjoy it, the ☕
button keeps it running.
