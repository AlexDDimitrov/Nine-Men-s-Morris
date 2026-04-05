# Nine-Men-s-Morris
Game of Nine Men's Morris against AI that trains on your movements


Method |      Endpoint      | Purpose
GET    | /stateFull         | game state
POST   | /place             | {"pos": N}
POST   | /move              | {"from": N, "to": M}
POST   | /remove            | {"pos": N}
GET    | /valid_placements  | Empty squares
POST   | /valid_moves       | {"pos": N}
GET    | /removable         | Pieces AI can take