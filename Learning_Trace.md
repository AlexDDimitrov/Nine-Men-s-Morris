# What we learned
* **What is the Monte Carlo Tree Search (MCTS)**

    * Search mehtod, whose main purpose it to find the most promising move, building a search tree using random simultaions

    * We chose it because it avoids exploring every single move and is suitable for a large need of searching

    * It has 4 phases

    - Selection(when the bot moves down the tree, while balancing exploitation (chosing the moves with higher rate)) and exploration(trying new moves)

    - Expansion (the main node expands into more child nodes (any vald for the game positon) until the game is over)

    - Simultaion(the bot does random playouts)

    - Backpropagation(the result of the simulation is sent back up the tree to the root, updating the statics - visit counts and win rates)


* **What is a heatmap and why is it useful**
    * The type of heatmap we are using is a Positional Frequency Heatmap
    * Instead of visual colors, it is a data structure (a dictionary) that records how often an event happens in a specific location. Every time the player places a piece on a specific board coordinate, that position's "temperature" (frequency count) increases.
    * It allows the AI to dynamically map human behavior and recognize patterns in real-time.
    
    

* **What are Heuristics and how did we apply them?**
    * Heuristics in machine learning are simple, rule-based, or intuitive shortcuts used to solve complex problems quickly when, unlike traditional machine learning, data is scarce, or optimal solutions are too slow to compute

    * By implementing simple heuristic rules (like adding +1000 points to a move that forms a mill, or penalizing a move by -500 if it leaves the bot vulnerable), we gave the AI human-like "instincts."

    * Speed and Simplicity
    * High interpretability

