import time
import sys
import os
import json
import re
from typing import List, Optional

CUPS_ASCII = [
    r"""
      ___  
     /   \ 
    |     |
     \___/ 
    """,
    r"""
      ___  
     / o \ 
    |     |
     \___/ 
    """,
]

CUP_WIDTH = 12

# ANSI Colors
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_cup_lines(has_ball: bool) -> List[str]:
    ascii_art = CUPS_ASCII[1] if has_ball else CUPS_ASCII[0]
    return [line for line in ascii_art.split('\n') if line.strip()]

def render_state(true_position: int, revealed: bool = False, dealer_said: str = "", scratchpad: str = ""):
    cup_lines = []
    for i in range(3):
        cup_lines.append(get_cup_lines(revealed and i == true_position))
    
    print("\n" + BOLD + "="*60 + RESET)
    if scratchpad:
        print(f"{YELLOW}{BOLD}DEALER'S THOUGHTS:{RESET} {YELLOW}{scratchpad}{RESET}")
        print("-" * 60)
    
    # Print cups side by side
    for line_idx in range(len(cup_lines[0])):
        combined_line = ""
        for cup_idx in range(3):
            color = BLUE
            if revealed and cup_idx == true_position:
                color = GREEN
            combined_line += color + cup_lines[cup_idx][line_idx].ljust(CUP_WIDTH) + RESET
        print(combined_line)
    
    print(f"{BLUE}    [0]         [1]         [2]{RESET}")
    print(f"{BLUE}   (Left)     (Middle)    (Right){RESET}")
    print(BOLD + "="*60 + RESET)
    
    if dealer_said:
        print(f"\n{BOLD}DEALER SAYS:{RESET} {GREEN}\"{dealer_said}\"{RESET}")

def animate_shuffle(final_position: int, duration: float = 1.5):
    frames = 10
    for i in range(frames):
        clear_screen()
        # Randomize for effect
        current_pos = (i % 3)
        render_state(current_pos, revealed=False)
        print(f"\n{YELLOW}{BOLD}Shuffling...{RESET}")
        time.sleep(duration / frames)
    
    clear_screen()
    render_state(final_position, revealed=False)

def parse_tags(text: str):
    scratchpad = ""
    dealer = ""
    
    # Try to find scratchpad with robust parsing for missing closing tags
    s_start = text.find('<scratchpad>')
    if s_start != -1:
        s_end = text.find('</scratchpad>', s_start)
        if s_end != -1:
            scratchpad = text[s_start+12:s_end].strip()
        else:
            # Look for next tag or end of string
            next_tag = text.find('<dealer>', s_start)
            if next_tag != -1:
                scratchpad = text[s_start+12:next_tag].strip()
            else:
                scratchpad = text[s_start+12:].strip()

    # Try to find dealer with robust parsing
    d_start = text.find('<dealer>')
    if d_start != -1:
        d_end = text.find('</dealer>', d_start)
        if d_end != -1:
            dealer = text[d_start+8:d_end].strip()
        else:
            dealer = text[d_start+8:].strip()
    
    if not dealer and not scratchpad:
        dealer = text
        
    return scratchpad, dealer

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Visualize the 3-cup shell game.")
    parser.add_argument("--file", type=str, help="Path to a JSONL file with game results")
    parser.add_argument("--index", type=int, default=0, help="Index of the example to visualize")
    parser.add_argument("--interactive", action="store_true", help="Run an interactive game")
    parser.add_argument("--reveal", action="store_true", help="Reveal the ball position")
    
    args = parser.parse_args()

    if args.interactive:
        import random
        true_pos = random.randint(0, 2)
        animate_shuffle(true_pos)
        guess = input(f"\n{BOLD}Where is the ball? [0, 1, 2]:{RESET} ")
        try:
            guess = int(guess)
            clear_screen()
            render_state(true_pos, revealed=True)
            if guess == true_pos:
                print(f"\n{GREEN}{BOLD}CORRECT! You found the ball.{RESET}")
            else:
                print(f"\n{RED}{BOLD}WRONG! The ball was at position {true_pos}.{RESET}")
        except ValueError:
            print(f"{RED}Invalid input.{RESET}")
        return

    if args.file:
        try:
            with open(args.file, 'r') as f:
                lines = f.readlines()
                if args.index >= len(lines):
                    print(f"Index {args.index} out of range (max {len(lines)-1})")
                    return
                data = json.loads(lines[args.index])
                
                true_pos = data.get("true_position")
                output = data.get("output", "") or data.get("dealer_said", "")
                
                scratchpad, dealer = parse_tags(output)
                
                clear_screen()
                print(f"{BOLD}Visualizing Example {args.index} from {args.file}{RESET}")
                render_state(true_pos, revealed=args.reveal, dealer_said=dealer, scratchpad=scratchpad)
                
                if not args.reveal:
                    input(f"\n{BOLD}Press Enter to reveal...{RESET}")
                    clear_screen()
                    render_state(true_pos, revealed=True, dealer_said=dealer, scratchpad=scratchpad)
        except Exception as e:
            print(f"{RED}Error reading file: {e}{RESET}")
        return

    # Default demo
    true_pos = 1
    render_state(true_pos, revealed=True, dealer_said="The ball is in the middle, I promise!", scratchpad="I'm telling the truth to gain trust.")

if __name__ == "__main__":
    main()
