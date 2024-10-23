import aiohttp
import asyncio
import os
from dotenv import load_dotenv
import time
import re
import json


def async_batch_openai(requests): 
    """
    Asynchronously sends multiple requests to the OpenAI chat completions API.
    Args:
        requests (list): A list of request JSON objects to be sent to the API.
    Returns:
        list: A list of response messages from the API.
    """
    REQUEST_URL = "https://api.openai.com/v1/chat/completions"
    REQUEST_HEADER = {"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"}

    async def _post_request(session, request_json):
        start_time = time.time()
        dataset_index = request_json.pop('dataset_index', None)
        async with session.post(REQUEST_URL, json=request_json) as response:
            response_json = await response.json()
            end_time = time.time()
            duration = end_time - start_time
            content = response_json['choices'][0]['message']['content']
            return {'content': content, 'duration': duration, 'dataset_index': dataset_index}

    async def _run_tasks(requests):
        async with aiohttp.ClientSession(headers=REQUEST_HEADER) as session:
            tasks = [_post_request(session, request) for request in requests]
            return await asyncio.gather(*tasks, return_exceptions=True)
    return asyncio.run(_run_tasks(requests))



def extract_move(response):
    pattern = r'submit_move\((\d)\)'
    matches = re.findall(pattern, response)
    if matches:
        move = int(matches[-1])
        if 1 <= move <= 9:
            return move
    return None


if __name__ == '__main__':
    load_dotenv()
    with open('dataset_top50.json', 'r') as f:
        DATA = json.load(f)['boards']
    
    # Limit the dataset to 3 entries for testing
    #DATA = dict(list(DATA.items())[:2])

    prompt = """
    You are an expert TicTacToe player.
    
    # input
    ## player-mark
    {player_mark}
    ## board-state
    {board_state}
    
    # instruction
    {instruction}

    # output
    A move MUST be submitted by writing "submit_move(d)", where d is a digit in [1,2,3,4,5,6,7,8,9].
    """

    heuristic_instructions = """
    A player can play a perfect game of tic-tac-toe (to win or at least draw) if, each time it is their turn to play, they choose the first available move from the following list, as used in Newell and Simon's 1972 tic-tac-toe program.[19]
    1. Win: If the player has two in a row, they can place a third to get three in a row.
    2. Block: If the opponent has two in a row, the player must play the third themselves to block the opponent.
    3. Fork: Cause a scenario where the player has two ways to win (two non-blocked lines of 2).
    4. Block an opponent's fork: If there is only one possible fork for the opponent, the player should block it. Otherwise, the player should block all forks in any way that simultaneously allows them to make two in a row. Otherwise, the player should make a two in a row to force the opponent into defending, as long as it does not result in them producing a fork. For example, if "X" has two opposite corners and "O" has the center, "O" must not play a corner move to win. (Playing a corner move in this scenario produces a fork for "X" to win.)
    5. Center: A player marks the center. (If it is the first move of the game, playing a corner move gives the second player more opportunities to make a mistake and may therefore be the better choice; however, it makes no difference between perfect players.)
    6. Opposite corner: If the opponent is in the corner, the player plays the opposite corner.
    7. Empty corner: The player plays in a corner square.
    8. Empty side: The player plays in a middle square on any of the four sides.
    """

    cases = [
        {"model": "gpt-4o", "instruction": "Your answer must be only the submit_move with the chosen move."},
        {"model": "gpt-4o", "instruction": "Let's think step-by-step."},
        {"model": "o1-preview", "instruction": "Let's think step-by-step."},
        {"model": "o1-preview", "instruction": heuristic_instructions}
    ]

    all_results = []
    results_file = 'machine_tests/progressive_results.json'

    # Load existing results if the file exists
    if os.path.exists(results_file):
        with open(results_file, 'r') as f:
            all_results = json.load(f)

    for case in cases[-1:]:
        model = case["model"]
        instruction = case["instruction"]
        requests = []

        case_result = {
            "model": model,
            "instruction": instruction,
            "boards": {}
        }

        for dataset_index, (board_key, board_data) in enumerate(DATA.items()):
            board_state = ''.join(str(cell) for cell in board_data['state'])
            player_mark = board_data['player']
            messages = [
                {
                    "role": "user", 
                    "content": prompt.format(player_mark=player_mark, board_state=board_state, instruction=instruction)
                }
            ]
            requests.append({
                "model": model,
                "messages": messages,
                "dataset_index": dataset_index
            })

        completions = async_batch_openai(requests)

        for completion in completions:
            try:
                move = extract_move(completion['content'])
            except:
                move = None
            dataset_index = completion['dataset_index']
            board_key = list(DATA.keys())[dataset_index]
            case_result["boards"][board_key] = {
                "content": completion['content'],
                "duration": completion['duration'],
                "move": move
            }

        all_results.append(case_result)

        # Save results progressively after each case
        with open(results_file, 'w') as f:
            json.dump(all_results, f, indent=2)

        print(f"Completed all requests for model {model} with instruction '{instruction}'. Results saved.")

    print("All cases completed and results saved.")
