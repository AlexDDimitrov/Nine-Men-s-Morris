# Nine-Men's-Morris
Game of Nine Men's Morris against AI that trains on your movements

## API Endpoints

| Method | Endpoint          | Purpose                  |
|--------|-------------------|--------------------------|
| GET    | /stateFull        | game state               |
| POST   | /place            | {"pos": N}               |
| POST   | /move             | {"from": N, "to": M}     |
| POST   | /remove           | {"pos": N}               |
| GET    | /valid_placements | Empty squares            |
| POST   | /valid_moves      | {"pos": N}               |
| GET    | /removable        | Pieces AI can take       |

## Board Layout

```
Pos:    0────── 1 ────── 2       O = (White)  
        ║  3─── 4 ─── 5  ║       X = (Black)  
        ║  ║  6─7─8   ║  ║       █ = empty  
        9─10─11    12─13─14  
        ║  ║ 21─22─23 ║  ║  
        ║  19── 20 ──18  ║  
        17──────16 ──────15  
```
[[![alt text]()]()](https://github.com/AlexDDimitrov/Nine-Men-s-Morris/blob/main/nineMenMorrisGif.mov)
