import curses
import difflib
import random
import time
from PIL import Image
from collections import deque
import threading
import base64
from PIL import Image
from io import BytesIO

map_data = "iVBORw0KGgoAAAANSUhEUgAAAB4AAAAeCAYAAAA7MK6iAAACC0lEQVR4AcSWUXLbMAxE+fLf3v+c7QFSPXJAA6Qk281M4slqSQDcBUQnk4/PH/p8tOMDNPg+HJatG7s4BpdaZtfCxP+wZzLUCUzjCATD4w1E7F2GofG7sR29NL7qFHaRTTUF1PnTPlNkLC+NTZ91avxdAA0ox26N/9ba9mtvvIjdbZw8YF0xfiZ89soUeRW+QRjTFON1wlXQg2vsnX3WL8ZODKOjM8GvTAxVtxjbkfdwZmosTwxVyPwd1BVRU4wNwhCEwcYCeWJFRORe4dz4ZhwCiorYy/kg0H9FAFMvwTcahZfGwCZ8NrHNiRB8lS+NFQuE2NXEMJqMulf40hh2sbuJ1ybPzK2J+GYcyeAolAGpA5hXAXXdC5YHjJoIb8aRuOJoSL7Dej7Xmrs19g+KRWfwvmFMATvfnTFXjFej/PW3OMP7zlPkda6LNdCyXjHOCaCfgcF9czxg7IF5x+v0R9nTn2KcJ76awLiqcmCd3vwKa7N+MXZioJ8B5kQ9sDzgkYe6XkrnNho0UIztSpiQA+5X5Jxr88GuV8CjOXPTGGhxVyagFhpbAcz/SvJrXOtsKBC5aWwivwr3gSg+Y88Y95rkM8A+xDT2AIypXcf0gNtbwPMa34iDhFAxNhgTyBYK488QdbJY69XLsWkMo2t4MNC/2R4ApNs90PMw2AOANON9czy6sR1+Jw7f9g8AAP//prwLHwAAAAZJREFUAwBNUSTjeon9bQAAAABJRU5ErkJggg=="
img = Image.open(BytesIO(base64.b64decode(map_data)))

# ----------------------------
# Game Settings
# ----------------------------
VALID_WORDS = ["look", "map", "quit", "help", "move", "work"]

player_pos = [1, 1]
baddie_pos = [5, 5]
GAME_OVER = False
TASK_DONE = False
DETECTION_RADIUS = 5
new_path = True

baddie_lock = threading.Lock()

# ----------------------------
# Load Map from Image
# ----------------------------
def load_map_from_image_obj(img):
    img = img.convert("RGB")
    width, height = img.size
    walls = [[0 for _ in range(width)] for _ in range(height)]
    green_spots = []

    for y in range(height):
        for x in range(width):
            r, g, b = img.getpixel((x, y))
            if r > 200 and g > 200 and b > 200:  # white -> wall
                walls[y][x] = 1
            elif g > 200 and r < 100 and b < 100:  # green -> task spot
                green_spots.append((y, x))
    return walls, green_spots, width, height

# Use the base64-decoded image
WALLS, GREEN_SPOTS, MAP_WIDTH, MAP_HEIGHT = load_map_from_image_obj(img)


# ----------------------------
# Helper Functions
# ----------------------------
def find_closest_word(word):
    matches = difflib.get_close_matches(word, VALID_WORDS, n=1, cutoff=0.0)
    return matches[0] if matches else word

def move_player(direction):
    y, x = player_pos
    new_y, new_x = y, x
    if direction == "w" and y > 0:
        new_y -= 1
    elif direction == "s" and y < MAP_HEIGHT - 1:
        new_y += 1
    elif direction == "a" and x > 0:
        new_x -= 1
    elif direction == "d" and x < MAP_WIDTH - 1:
        new_x += 1
    if WALLS[new_y][new_x] == 0:
        player_pos[0], player_pos[1] = new_y, new_x

def find_path(start, goal):
    queue = deque([start])
    visited = {tuple(start): None}
    while queue:
        current = queue.popleft()
        if current == goal:
            path = [current]
            while visited[tuple(current)] is not None:
                current = visited[tuple(current)]
                path.append(current)
            path.reverse()
            return path
        y, x = current
        for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < MAP_HEIGHT and 0 <= nx < MAP_WIDTH:
                if WALLS[ny][nx] == 0 and (ny, nx) not in visited:
                    visited[(ny, nx)] = current
                    queue.append([ny, nx])
    return None

# ----------------------------
# Baddie Thread (Continuous Wandering)
# ----------------------------
def baddie_thread(messages):
    global baddie_target, GAME_OVER

    empty_tiles = [(y, x) for y in range(MAP_HEIGHT) for x in range(MAP_WIDTH) if WALLS[y][x] == 0]

    # Persistent state variables
    baddie_target = random.choice(empty_tiles)
    path = find_path(list(baddie_pos), list(baddie_target))
    pause_time = 0

    while not GAME_OVER:
        with baddie_lock:
            doing_task = tuple(player_pos) in GREEN_SPOTS

            if doing_task:
                # Chase player directly
                path = find_path(list(baddie_pos), list(player_pos))
                if path and len(path) > 1:
                    baddie_pos[0], baddie_pos[1] = path[1]
            else:
                if pause_time > 0:
                    # Baddie is pausing
                    pause_time -= 0.2
                else:
                    if path is None or len(path) <= 1:
                        # Pick a new target and generate path
                        baddie_target = random.choice(empty_tiles)
                        path = find_path(list(baddie_pos), list(baddie_target))
                        pause_time = random.uniform(1.0, 2.0)  # pause AFTER reaching target
                    else:
                        # Move along path
                        baddie_pos[0], baddie_pos[1] = path[1]
                        path = path[1:]  # step forward in path

            # Collision check
            if tuple(baddie_pos) == tuple(player_pos):
                messages.append(("The baddie found you! Game over.", "text"))
                GAME_OVER = True

        time.sleep(0.2)

# ----------------------------
# Drawing Functions
# ----------------------------
def draw_map(stdscr, doing_task):
    height, width = stdscr.getmaxyx()
    for y in range(MAP_HEIGHT):
        x_pos = 0
        for x in range(MAP_WIDTH):
            char = " "
            color = None

            # Walls
            if WALLS[y][x] == 1:
                char = "■"
            # Green task spot
            elif (y, x) in GREEN_SPOTS:
                char = "*"
                color = 3
            # Player
            if [y, x] == player_pos:
                char = " "
                color = 4
            # Baddie
            if [y, x] == baddie_pos:
                char = " "
                color = 2

            if color:
                stdscr.attron(curses.color_pair(color))
                stdscr.addstr(y+1, x_pos, char)
                stdscr.attroff(curses.color_pair(color))
            else:
                stdscr.addstr(y+1, x_pos, char)
            x_pos += 2

def draw_ui(stdscr, messages, input_text="", task_progress=0):
    height, width = stdscr.getmaxyx()
    bar_text = " COMMAND PROMPT GAME "
    stdscr.attron(curses.color_pair(1))
    stdscr.addstr(0, 0, " "*(width-1))
    stdscr.addstr(0, max((width-len(bar_text))//2,0), bar_text)
    stdscr.attroff(curses.color_pair(1))

    start_line = max(1, height-4-len(messages))
    line_idx = start_line
    for msg, _ in messages[-(height-4):]:
        if line_idx < height-3:
            stdscr.addstr(line_idx, 0, msg[:width-1])
            line_idx += 1

    if task_progress > 0:
        progress_width = width-4
        done = int(progress_width * task_progress)
        stdscr.addstr(height-3, 0, "[" + "#"*done + "-"*(progress_width-done) + "]")
    else:
        stdscr.addstr(height-3, 0, " "*(width-1))

    stdscr.addstr(height-2, 0, "> "+input_text[:width-3])
    stdscr.move(height-2, 2+len(input_text[:width-3]))

# ----------------------------
# Movement Mode
# ----------------------------
def movement_mode(stdscr, messages, alerted):
    stdscr.nodelay(True)
    doing_task = False
    task_start = None
    task_progress = 0

    while True:
        if GAME_OVER:
            stdscr.clear()
            stdscr.addstr(0,0,"The baddie got you! Press any key to exit.")
            stdscr.refresh()
            stdscr.getch()
            return

        stdscr.clear()
        draw_ui(stdscr, messages, "", task_progress)
        draw_map(stdscr, doing_task)
        stdscr.refresh()

        # Handle tasks
        if tuple(player_pos) in GREEN_SPOTS:
            if not doing_task:
                doing_task = True
                task_start = time.time()
            task_progress = (time.time() - task_start) / 3
            if task_progress >= 1.0:
                doing_task = False
                GREEN_SPOTS.remove(tuple(player_pos))
                messages.append(("Task completed!", "text"))
        else:
            doing_task = False
            task_progress = 0
            task_start = None

        key = stdscr.getch()
        if key in (10,13):
            break
        elif key in (ord('w'), curses.KEY_UP):
            move_player('w')
        elif key in (ord('s'), curses.KEY_DOWN):
            move_player('s')
        elif key in (ord('a'), curses.KEY_LEFT):
            move_player('a')
        elif key in (ord('d'), curses.KEY_RIGHT):
            move_player('d')

        time.sleep(0.1)

# ----------------------------
# Command Handler
# ----------------------------
def handle_command(cmd, messages, stdscr, alerted):
    cmd = cmd.lower()
    if cmd=="look":
        messages.append(("You see a dark, empty room with faint green lights.", "text"))
    elif cmd=="help":
        messages.append(("Available commands: "+", ".join(VALID_WORDS), "text"))
    elif cmd=="quit":
        return True
    elif cmd=="map":
        messages.append(("Displaying map...", "text"))
        draw_map(stdscr, False)
        stdscr.refresh()
        stdscr.getch()
    elif cmd=="move":
        movement_mode(stdscr, messages, alerted)
    else:
        messages.append((f"Unknown command: {cmd}", "text"))
    return False

# ----------------------------
# Main Loop
# ----------------------------
def main(stdscr):
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_RED)
    curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    curses.curs_set(1)
    input_text = ""
    messages = []
    alerted = [False]

    # Start the baddie thread
    threading.Thread(target=baddie_thread, args=(messages,), daemon=True).start()

    while True:
        if GAME_OVER:
            stdscr.clear()
            stdscr.addstr(0,0,"The baddie got you! Press any key to exit.")
            stdscr.refresh()
            stdscr.getch()
            break

        stdscr.clear()
        draw_ui(stdscr, messages, input_text)
        draw_map(stdscr, False)
        stdscr.refresh()

        key = stdscr.getch()
        if key==ord('q'):
            break
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            input_text = input_text[:-1]
        elif key in (10,13):
            if input_text.strip():
                words = input_text.strip().split()
                recognized_words = [find_closest_word(w) for w in words]
                for word in recognized_words:
                    quit_game = handle_command(word, messages, stdscr, alerted)
                    if quit_game:
                        return
                input_text = ""
        elif 32 <= key <= 126:
            input_text += chr(key)

        time.sleep(0.1)

curses.wrapper(main)
