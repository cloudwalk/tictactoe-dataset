class TicTacToe:
    def __init__(self):
        """
        Initializes
            board is a 3x3 grid; starting with empty cells, represented by 0
            player is represented by either 1 or -1; it cycles with moves
        """
        self.board = [[0,0,0],[0,0,0],[0,0,0]]
        self.player = 1

    def get_hashable_board(self):
        return tuple(tuple(row) for row in self.board)

    def get_available_moves(self):
        """
        Returns: a list of (row, col) tuples representing the available moves.
        """
        return [(i, j) for i in range(3) for j in range(3) if self.board[i][j] == 0]
    
    def get_lines(self):
        """
        Returns: list of all 8 line directions: 3 horizontal, 3 vertical, and 2 diagonal.
        """
        lines = self.board + \
                [[self.board[row][col] for row in range(3)] for col in range(3)] + \
                [[self.board[i][i] for i in range(3)], [self.board[i][2 - i] for i in range(3)]]
        return lines
    
    def get_winner(self):
        """
        Returns: the player number (1 or -1) if there is a winner, 0 otherwise.
        """
        for line in self.get_lines():
            if sum(line) == 3:  # Player with 1 wins
                return 1
            if sum(line) == -3:  # Player with -1 wins
                return -1
        return 0 # No winner

    def is_terminal_state(self):
        """
        Returns: true if board state is a terminal state (win, loss, or draw).
        """
        if self.get_winner() != 0: # Either player (1 or -1) won.
            return True
        elif not self.get_available_moves(): # Elif the board is full, then it is a draw.
            return True
        return False
    
    def do_move(self, move):
        self.board[move[0]][move[1]] = self.player
        self.player *= -1

    def undo_move(self, move):
        self.board[move[0]][move[1]] = 0
        self.player *= -1


class Minimax:
    def __init__(self):
        self.solution = {}

    def update(self, state, move, score, depth):
        hashable_board = state.get_hashable_board()
        if move:
            self.solution.setdefault(hashable_board, {
                "moves": [],
                "scores": [],
                "depths": []  # Add depths list
            })
            if move not in self.solution[hashable_board]["moves"]:
                self.solution[hashable_board]["moves"].append(move)
                self.solution[hashable_board]["scores"].append(score)
                self.solution[hashable_board]["depths"].append(depth)  # Add depth
        else:
            self.solution.setdefault(hashable_board, {
                "scores": [score],
                "depths": [depth]  # Add depth for terminal states
            })
    
    def get_best_score(self, state):
        board_state = self.solution[state.get_hashable_board()]
        scores = board_state["scores"]
        depths = board_state["depths"]
        
        if state.player == 1:
            max_score = max(scores)
            best_indices = [i for i, s in enumerate(scores) if s == max_score]
            if max_score == 1:
                return max_score, min(depths[i] for i in best_indices)
            else:
                return max_score, max(depths[i] for i in best_indices)
        else:
            min_score = min(scores)
            best_indices = [i for i, s in enumerate(scores) if s == min_score]
            if min_score == -1:
                return min_score, min(depths[i] for i in best_indices)
            else:
                return min_score, max(depths[i] for i in best_indices)

    def recursive_minimax(self, state):
        """
        Generate all reachable 5477 states, plus the empty state.
        """
        if state.is_terminal_state():
            score = state.get_winner()
            depth = sum(cell != 0 for row in state.board for cell in row)  # Calculate depth
            self.update(state, None, score, depth)
            return score, depth
        
        for move in state.get_available_moves():
            state.do_move(move)
            move_score, move_depth = self.recursive_minimax(state)
            state.undo_move(move)       
            self.update(state, move, move_score, move_depth)

        return self.get_best_score(state)

    def run(self):
        state = TicTacToe()
        self.recursive_minimax(state)
        print(f"States created, size: {len(self.solution)}")