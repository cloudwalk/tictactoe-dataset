from pydantic import BaseModel
from typing import Dict, List, Literal, Tuple
import random

class Score(BaseModel):
    value: int
    depth: int
    move: int | None

class Category(BaseModel):
    choice_complexity: Tuple[int, int] | None
    depth_complexity: int
    decision: Literal['offensive', 'defensive'] | None
    pattern: Literal['threat', 'fork', 'threat-fork', "has 7, 8, or 9 scores"] | None
    symmetry_group: str
    
class Board(BaseModel):
    state: List[Literal['X', 'O', 1, 2, 3, 4, 5, 6, 7, 8, 9]]
    player: Literal['X', 'O']
    scores: List[Score]
    category: Category

    @staticmethod
    def hash_board(state) -> str:
        return ''.join(str(x) for x in state)

class Dataset(BaseModel):
    boards: Dict[str, Board]

    def get_board(self, state) -> Board:
        key = Board.hash_board(state)
        return self.boards[key]
    
    def get_sample(self, n: int) -> List[Board]:
        keys = random.sample(list(self.boards.keys()), n)
        return [self.boards[key] for key in keys]

    def to_json(self, path: str) -> None:
        with open(path, 'w') as file:
            file.write(self.model_dump_json(indent=2))
            
    @classmethod
    def from_json(cls, path: str):
        with open(path, 'r') as file:
            return cls.model_validate_json(file.read())


def get_symmetry_group(board) -> str:
    def _rotate_board(board):
        return [board[6], board[3], board[0],
                board[7], board[4], board[1],
                board[8], board[5], board[2]]

    def _mirror_board(board):
        return [board[2], board[1], board[0],
                board[5], board[4], board[3],
                board[8], board[7], board[6]]  
        
    transformations = set()
    
    def _add_transformation(board):
        correctly_numbered_board = [x if isinstance(x, str) and x in 'XO' else (i + 1) for i, x in enumerate(board)]
        hasheable_board = ''.join(str(x) for x in correctly_numbered_board)
        transformations.add(hasheable_board)
    
    # Original board and its rotations
    current = board
    for _ in range(4):
        _add_transformation(current)
        current = _rotate_board(current)
    
    # Mirrored board and its rotations
    mirrored = _mirror_board(board)
    current = mirrored
    for _ in range(4):
        _add_transformation(current)
        current = _rotate_board(current)
    
    symmetry_group = "|".join(sorted(transformations))
    return symmetry_group


def convert_board_representation(board):
    """
    Converts board representation from ((1,-1,0),(0,0,0),(0,0,0)) to ["X", "O", 3, 4, 5, 6, 7, 8, 9].
    """
    flat_list = [item for sublist in board for item in sublist]
    return [
        "X" if val == 1 else
        "O" if val == -1 else
        i + 1
        for i, val in enumerate(flat_list)
    ]

def convert_moves_representation(move):
    """
    Converts the representation of a move.
    Converts move from (row, col) to a number 1-9.
    """
    return move[0] * 3 + move[1] + 1


def create_dataset(minimax_solution):
    """
    create dataset from minimax solution (created by solve_tictactoe.py)
    """
    dataset = Dataset(boards={})
    for board_key, board_values in minimax_solution.items():
        state = convert_board_representation(board_key)
        player = 'O' if state.count('X') > state.count('O') else 'X'
        scores = [
            Score(
                value = score if player == 'X' else -score, # make score relative to player
                depth = board_values["depths"][i],
                move = convert_moves_representation(board_values["moves"][i]) if "moves" in board_values else None
            ) for i, score in enumerate(board_values["scores"])
        ]

        highest_score = max(scores, key=lambda x: x.value).value

        no_decision_to_be_made = len(set(score.value for score in scores)) == 1 
        if no_decision_to_be_made:
            decision = None
            depth_complexity = 0
            pattern = None
        else:
            if highest_score == 1:
                decision = "offensive"
                lookahead_depth = min(score.depth for score in scores if score.value == 1)
            else:
                decision = "defensive"
                lookahead_depth = max(score.depth for score in scores if score.value == -1)
            board_depth = state.count('X') + state.count('O')
            depth_complexity = lookahead_depth - board_depth
            if depth_complexity in [1,2]:
                pattern = "threat"
            elif depth_complexity in [3,4]:
                pattern = "fork"
            elif depth_complexity in [5,6]:
                pattern = "threat-fork"
            else:
                pattern = "has 7, 8, or 9 scores"

        highest_score_count = sum(1 for score in scores if score.value == highest_score)
        category = Category(
            choice_complexity = (len(scores) - highest_score_count, len(scores)),
            depth_complexity = depth_complexity,
            decision = decision,
            pattern = pattern,
            symmetry_group = get_symmetry_group(state)
        )
        dataset.boards[Board.hash_board(state)] = Board(
            state = state,
            player = player,
            scores = scores,
            category = category
        )
    return dataset




if __name__ == "__main__":
    from solve_tictactoe import Minimax
    minimax = Minimax()
    minimax.run()
    dataset = create_dataset(minimax.solution)
    dataset.to_json("development/tic-tac-toe/dataset.json")
