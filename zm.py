import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import random
import sys
import os

# Настройки игры
WINDOW_WIDTH = 640
WINDOW_HEIGHT = 480
GRID_SIZE = 20

RESOLUTIONS = [(640, 480)]
UI_SCALE = 1.0

GRID_WIDTH = WINDOW_WIDTH // GRID_SIZE
GRID_HEIGHT = WINDOW_HEIGHT // GRID_SIZE

SNAKE_LENGTH = 3
MIN_BOTS = 3
DEFAULT_BOT_COUNT = 4
MAX_BOTS = 7
MAX_FOOD = 15
WIN_SCORE_BASE = 10

# Сложность: название, количество ботов, количество еды
DIFFICULTIES = [
    ("Легко", 3, 6),
    ("Нормально", DEFAULT_BOT_COUNT, 3),
    ("Сложно", 5, 2),
    ("Безумие", 7, 1),
]
DEFAULT_DIFFICULTY_INDEX = 1

# Постепенное сжатие поля
SHRINK_GRACE_TICKS = 150      # 15 секунд до первого сжатия
SHRINK_INTERVAL_TICKS = 100   # сжатие раз в 10 секунд
MIN_FIELD_WIDTH = 16
MIN_FIELD_HEIGHT = 10

# Цвета (R, G, B)
COLOR_BG = (0.05, 0.08, 0.12)
COLOR_SNAKE = (0.2, 0.9, 0.4)
COLOR_SNAKE_HEAD = (0.4, 1.0, 0.6)
COLOR_FOOD = (1.0, 0.25, 0.25)
COLOR_GRID = (0.12, 0.16, 0.22)
COLOR_TEXT = (230, 235, 245)
COLOR_HINT = (170, 180, 200)
COLOR_ACCENT = (255, 210, 90)
COLOR_TITLE_RED = (240, 55, 60)
COLOR_SETTING_RED = (225, 95, 100)
COLOR_SETTING_SELECTED = (255, 60, 65)

BOT_COLORS = [
    (0.95, 0.60, 0.20),
    (0.30, 0.60, 1.00),
    (0.80, 0.40, 0.95),
    (1.00, 0.85, 0.25),
    (0.25, 0.85, 0.85),
    (0.95, 0.45, 0.65),
    (0.65, 0.90, 0.30),
    (0.80, 0.80, 0.90),
]

# Личности ботов: характер, агрессивность и время переключения между охотой и едой
PERSONALITIES = {
    "hunter": {
        "title": "Охотник",
        "aggression": (1.3, 1.7),
        "food_weight": 0.50,
        "hunt_weight": 1.50,
        "forage_time": (50, 80),
        "hunt_time": (140, 220),
        "initial_mode": "hunt",
        "tactic": "front",
        "hunger": (45, 70),
        "forced_forage": (40, 70),
        "goal_hunt": False,
        "min_food": 0,
        "goal": "kill",
    },
    "strategist": {
        "title": "Стратег",
        "aggression": (1.0, 1.3),
        "food_weight": 1.00,
        "hunt_weight": 1.20,
        "forage_time": (70, 110),
        "hunt_time": (110, 170),
        "initial_mode": "forage",
        "tactic": "ring",
        "hunger": (55, 85),
        "forced_forage": (55, 85),
        "goal_hunt": True,
        "min_food": 3,
        "goal": "kill",
    },
    "bait": {
        "title": "Провокатор",
        "aggression": (1.0, 1.3),
        "food_weight": 0.75,
        "hunt_weight": 1.15,
        "forage_time": (40, 70),
        "hunt_time": (100, 160),
        "initial_mode": "hunt",
        "tactic": "back",
        "hunger": (50, 75),
        "forced_forage": (40, 70),
        "goal_hunt": False,
        "min_food": 0,
        "goal": "kill",
    },
    "collector": {
        "title": "Собиратель",
        "aggression": (0.6, 0.9),
        "food_weight": 3.2,
        "hunt_weight": 0.0,
        "forage_time": (999, 999),
        "hunt_time": (999, 999),
        "initial_mode": "forage",
        "tactic": "ring",
        "hunger": (999, 999),
        "forced_forage": (999, 999),
        "goal_hunt": False,
        "min_food": 999,
        "goal": "score",
    },
}

PERSONALITY_ORDER = ["hunter", "strategist", "bait"]

# Направления
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)
DIRECTIONS = [UP, DOWN, LEFT, RIGHT]


def opposite(direction):
    return (-direction[0], -direction[1])


def lighten(color):
    return tuple(min(1.0, v * 1.25 + 0.1) for v in color)


def s(value):
    """Масштабирование интерфейса под выбранное разрешение."""
    return int(round(value * UI_SCALE))


def field_label():
    """Фиксированный размер поля в клетках и в пикселях."""
    width, height = RESOLUTIONS[0]
    return f"{width // GRID_SIZE}×{height // GRID_SIZE} ({width}×{height})"


def difficulty_label(index):
    if index is None:
        return "Своя"
    return DIFFICULTIES[index][0]


def match_difficulty(bot_count, food_count):
    """Возвращает индекс сложности или None, если настройки изменены вручную."""
    for i, (_, bots, food) in enumerate(DIFFICULTIES):
        if (bots, food) == (bot_count, food_count):
            return i
    return None


def win_score_for(bot_count, food_count):
    """Счёт для автоматической победы.

    Чем меньше ботов и чем больше еды на поле, тем выше нужный счёт.
    """
    bot_bonus = (MAX_BOTS - bot_count) * 0.6
    food_bonus = food_count * 1.5
    return max(WIN_SCORE_BASE, int(round(WIN_SCORE_BASE + bot_bonus + food_bonus)))


class Snake:
    def __init__(self, head, direction, color, is_player=False, name="Бот", aggression=1.0):
        x, y = head
        self.body = [(x - direction[0] * i, y - direction[1] * i) for i in range(SNAKE_LENGTH)]
        self.direction = direction
        self.next_direction = direction
        self.grow = False
        self.color = color
        self.is_player = is_player
        self.name = name
        self.place = None
        self.aggression = aggression
        self.personality = "hunter"
        self.personality_title = "Охотник"
        self.goal = "kill"
        self.mode = "hunt"
        self.mode_timer = 0
        self.food_eaten = 0
        self.hunger = 0
        self.hunger_limit = 60
        self.attack_style = "front"
        self.flank = 1
        self.straight_ticks = 0
        self.last_direction = direction
        self.distance_stall_ticks = 0
        self.last_target_distance = None
        self.fatigue_timer = 0
        self.alive = True

    def change_direction(self, direction):
        if direction == opposite(self.direction):
            return
        self.next_direction = direction

    def update(self):
        self.direction = self.next_direction
        head_x, head_y = self.body[0]
        new_head = (head_x + self.direction[0], head_y + self.direction[1])
        self.body.insert(0, new_head)

        if self.grow:
            self.grow = False
        else:
            self.body.pop()

    def eat(self):
        self.grow = True

    def get_body(self):
        return self.body


class Game:
    def __init__(self, bot_count, food_count):
        self.bot_count = max(MIN_BOTS, min(MAX_BOTS, bot_count))
        self.food_count = max(1, food_count)
        self.win_score = win_score_for(self.bot_count, self.food_count)
        self.arena_left = 0
        self.arena_right = GRID_WIDTH - 1
        self.arena_top = 0
        self.arena_bottom = GRID_HEIGHT - 1
        self.shrink_timer = SHRINK_GRACE_TICKS
        self.player = Snake(self.player_spawn(), RIGHT, COLOR_SNAKE, is_player=True, name="Ты")
        self.bots = []
        self.foods = []
        self.score = 0
        self.state = "playing"
        self.lose_reason = ""
        self.player_dead = False
        self.player_place = None
        self.winner = None
        self.total_participants = bot_count + 1
        self.food_targets = {}
        self.spawn_bots()
        self.maintain_food()

    def player_spawn(self):
        return (GRID_WIDTH // 2, GRID_HEIGHT // 2)

    def bot_spawns(self, count):
        """Подбираем места для любого количества ботов подальше от игрока и друг от друга."""
        center_x, center_y = self.player_spawn()
        margin = SNAKE_LENGTH
        candidates = []

        for y in range(margin, GRID_HEIGHT - margin):
            for x in range(margin, GRID_WIDTH - margin):
                distance = abs(x - center_x) + abs(y - center_y)
                # Не ставим ботов вплотную к точке появления игрока
                if distance < 8:
                    continue
                delta_x = center_x - x
                delta_y = center_y - y
                if abs(delta_x) >= abs(delta_y):
                    direction = RIGHT if delta_x > 0 else LEFT
                else:
                    direction = DOWN if delta_y > 0 else UP
                candidates.append((distance, x, y, direction))

        # Сначала занимаем места подальше от центра
        candidates.sort(reverse=True)

        def pick(gap):
            spawns = []
            for _, x, y, direction in candidates:
                if any(abs(x - sx) + abs(y - sy) < gap for sx, sy, _ in spawns):
                    continue
                spawns.append((x, y, direction))
                if len(spawns) >= count:
                    break
            return spawns

        spawns = pick(6)
        if len(spawns) < count:
            spawns = pick(4)
        if len(spawns) < count:
            spawns = pick(2)
        return spawns

    def spawn_bots(self):
        spawns = self.bot_spawns(self.bot_count)
        for i, (x, y, direction) in enumerate(spawns):
            # Один бот охотится за автоматической победой, остальные — за головами
            if i == 0:
                personality_key = "collector"
            else:
                personality_key = PERSONALITY_ORDER[(i - 1) % len(PERSONALITY_ORDER)]
            personality = PERSONALITIES[personality_key]
            bot = Snake(
                (x, y), direction, BOT_COLORS[i % len(BOT_COLORS)], name=f"Бот {i + 1}",
                aggression=random.uniform(*personality["aggression"]),
            )
            bot.personality = personality_key
            bot.personality_title = personality["title"]
            bot.goal = personality.get("goal", "kill")
            bot.mode = personality["initial_mode"]
            if bot.mode == "hunt":
                bot.mode_timer = random.randint(*personality["hunt_time"])
            else:
                bot.mode_timer = random.randint(*personality["forage_time"])
            bot.hunger_limit = random.randint(*personality["hunger"])
            bot.hunger = random.randint(0, 20)
            bot.attack_style = personality["tactic"]
            bot.flank = random.choice((-1, 1))
            self.bots.append(bot)

    def all_snakes(self):
        snakes = []
        if self.player is not None:
            snakes.append(self.player)
        snakes.extend(self.bots)
        return snakes

    def arena_width(self):
        return self.arena_right - self.arena_left + 1

    def arena_height(self):
        return self.arena_bottom - self.arena_top + 1

    def in_bounds(self, cell):
        x, y = cell
        return (
            self.arena_left <= x <= self.arena_right
            and self.arena_top <= y <= self.arena_bottom
        )

    def can_shrink(self):
        return (
            self.arena_width() > MIN_FIELD_WIDTH
            or self.arena_height() > MIN_FIELD_HEIGHT
        )

    def shrink_arena(self):
        """Сжимает поле на одну клетку с каждой доступной стороны."""
        if self.arena_width() > MIN_FIELD_WIDTH:
            self.arena_left += 1
            self.arena_right -= 1
        if self.arena_height() > MIN_FIELD_HEIGHT:
            self.arena_top += 1
            self.arena_bottom -= 1

        self.foods = [food for food in self.foods if self.in_bounds(food)]

        survivors = []
        for snake in self.all_snakes():
            if not snake.alive:
                continue
            # Змея, которую накрыло сжимающейся стеной, погибает
            if any(not self.in_bounds(segment) for segment in snake.get_body()):
                snake.alive = False
                if snake.is_player:
                    self.lose_reason = "Поле сжалось"
            else:
                survivors.append(snake)

        place = len(survivors) + 1
        for snake in self.all_snakes():
            if not snake.alive and snake.place is None:
                snake.place = place
                if snake.is_player:
                    self.player_place = place

        self.bots = [bot for bot in self.bots if bot.alive]
        self.maintain_food()

    def field_status(self):
        if self.can_shrink():
            seconds = max(0, (self.shrink_timer + 9) // 10)
            return f"Поле: {self.arena_width()}×{self.arena_height()} • сжатие через {seconds}с"
        return f"Поле: {self.arena_width()}×{self.arena_height()} • минимальное"

    def food_target(self):
        return max(1, self.food_count)

    def free_cells(self):
        occupied = set()
        for snake in self.all_snakes():
            if snake.alive:
                occupied.update(snake.get_body())
        occupied.update(self.foods)
        cells = []
        for x in range(self.arena_left, self.arena_right + 1):
            for y in range(self.arena_top, self.arena_bottom + 1):
                if (x, y) not in occupied:
                    cells.append((x, y))
        return cells

    def maintain_food(self):
        target = self.food_target()
        if len(self.foods) > target:
            self.foods = self.foods[:target]
        while len(self.foods) < target:
            cells = self.free_cells()
            if not cells:
                break
            self.foods.append(random.choice(cells))

    def body_after_move(self, snake):
        """Тело змеи после хода: хвост сдвигается, если змея не растёт."""
        if snake.grow:
            return snake.get_body()
        return snake.get_body()[:-1]

    def next_head(self, snake, direction=None):
        move = direction if direction is not None else snake.direction
        head_x, head_y = snake.get_body()[0]
        return (head_x + move[0], head_y + move[1])

    def is_safe_cell(self, cell, snake):
        if not self.in_bounds(cell):
            return False
        for other in self.all_snakes():
            if not other.alive:
                continue
            if cell in self.body_after_move(other):
                return False
            # Не идём в клетку, куда уже направлена чужая голова (лобовое столкновение)
            if other is not snake and cell == self.next_head(other):
                return False
        return True

    def blocked_cells(self):
        blocked = set()
        for snake in self.all_snakes():
            if snake.alive:
                blocked.update(self.body_after_move(snake))
        return blocked

    def open_space(self, start, blocked, limit=140):
        """Сколько свободных клеток доступно из точки (защита от тупиков)."""
        visited = {start}
        stack = [start]
        count = 0
        while stack and count < limit:
            x, y = stack.pop()
            count += 1
            for dx, dy in DIRECTIONS:
                nxt = (x + dx, y + dy)
                if self.in_bounds(nxt) and nxt not in visited and nxt not in blocked:
                    visited.add(nxt)
                    stack.append(nxt)
        return count

    def distance_to_wall(self, cell):
        x, y = cell
        return min(
            x - self.arena_left,
            self.arena_right - x,
            y - self.arena_top,
            self.arena_bottom - y,
        )

    def wall_penalty(self, cell, direction):
        """Насколько опасно оказаться у края поля и идти прямо в стену."""
        x, y = cell

        if direction == LEFT:
            ahead = x - self.arena_left
        elif direction == RIGHT:
            ahead = self.arena_right - x
        elif direction == UP:
            ahead = y - self.arena_top
        else:
            ahead = self.arena_bottom - y

        penalty = 0.0
        # Чем меньше клеток до стены по ходу движения, тем хуже
        if ahead <= 3:
            penalty += (4 - ahead) * 1.2

        # У края и в углу меньше путей для отхода
        open_neighbors = 0
        for dx, dy in DIRECTIONS:
            if self.in_bounds((x + dx, y + dy)):
                open_neighbors += 1
        penalty += (4 - open_neighbors) * 0.5

        return penalty

    def clamp_point(self, point, margin=2):
        """Держим точку атаки внутри поля, не давая боту уткнуться в край."""
        x, y = point
        x = max(self.arena_left + margin, min(self.arena_right - margin, x))
        y = max(self.arena_top + margin, min(self.arena_bottom - margin, y))
        return (x, y)

    def head_danger(self, cell, snake):
        """Сколько чужих голов окажется рядом после их хода."""
        danger = 0
        x, y = cell
        for other in self.all_snakes():
            if other is snake or not other.alive:
                continue
            next_x, next_y = self.next_head(other)
            distance = abs(x - next_x) + abs(y - next_y)
            if distance == 0:
                return 100
            if distance == 1:
                danger += 1
        return danger

    def pick_target(self, bot):
        """Выбираем жертву: игрок приоритетнее, но ближайший бот тоже подходит."""
        bot_x, bot_y = bot.get_body()[0]
        target = None
        best_score = None
        for other in self.all_snakes():
            if other is bot or not other.alive:
                continue
            other_x, other_y = other.get_body()[0]
            distance = abs(bot_x - other_x) + abs(bot_y - other_y)
            # Крупный бот выбирает добычу поменьше, мелкий избегает гигантов
            distance += (len(bot.get_body()) - len(other.get_body())) * 2.0
            # Прижатая к стене жертва — удобная цель, у неё меньше путей отхода
            if self.distance_to_wall((other_x, other_y)) <= 3:
                distance -= 5.0
            if other.is_player:
                # Боты специально охотятся на игрока
                distance -= 15
            if best_score is None or distance < best_score:
                target = other
                best_score = distance
        return target

    def update_bot_behavior(self, bot):
        """Личность бота решает, когда он охотится, а когда идёт за едой."""
        personality = PERSONALITIES[bot.personality]
        bot.hunger += 1

        if bot.direction == bot.last_direction:
            bot.straight_ticks += 1
        else:
            bot.straight_ticks = 1
            bot.last_direction = bot.direction

        if bot.goal == "score":
            # Собиратель не отвлекается на драки — только еда и очки
            bot.mode = "forage"
            bot.mode_timer = 0
            if bot.fatigue_timer > 0:
                bot.fatigue_timer -= 1
            return

        target = self.pick_target(bot)
        if target is not None:
            bot_x, bot_y = bot.get_body()[0]
            target_x, target_y = target.get_body()[0]
            distance = abs(bot_x - target_x) + abs(bot_y - target_y)
            if bot.last_target_distance is not None and distance >= bot.last_target_distance:
                bot.distance_stall_ticks += 1
            else:
                bot.distance_stall_ticks = 0
            bot.last_target_distance = distance
        else:
            bot.distance_stall_ticks = 0
            bot.last_target_distance = None

        if bot.fatigue_timer > 0:
            bot.fatigue_timer -= 1
            return

        # Редкая усталость: бот долго идёт по прямой, не сближается с целью
        # и давно не ел. Тогда он ненадолго уходит к ближайшей еде.
        if bot.mode == "hunt" and bot.hunger >= 25:
            vertical = bot.direction[1] != 0
            straight_needed = 8 if vertical else 14
            stalled = (
                bot.distance_stall_ticks >= 8
                or bot.last_target_distance is None
                or bot.last_target_distance >= 6
            )
            if bot.straight_ticks >= straight_needed and stalled:
                bot.fatigue_timer = random.randint(18, 30)
                return

        bot.mode_timer -= 1
        hungry = bot.hunger >= bot.hunger_limit

        if bot.mode == "hunt":
            if hungry:
                # Пора подкрепиться — отвлекаемся на еду
                bot.mode = "forage"
                bot.mode_timer = random.randint(*personality["forced_forage"])
            elif bot.mode_timer <= 0:
                bot.mode = "forage"
                bot.mode_timer = random.randint(*personality["forage_time"])
            return

        # Режим сбора еды
        if hungry:
            if bot.mode_timer <= 0:
                bot.mode_timer = random.randint(*personality["forced_forage"])
            return

        if personality["goal_hunt"] and bot.food_eaten >= personality["min_food"]:
            # Набрал очки — идёт замыкать кольцо вокруг остальных
            bot.mode_timer = min(bot.mode_timer, 12)

        if bot.mode_timer <= 0:
            bot.mode = "hunt"
            bot.mode_timer = random.randint(*personality["hunt_time"])

    def assign_food_targets(self, bots):
        """Каждому боту — своя еда, чтобы они не ходили друг за другом."""
        available = list(self.foods)
        result = {}

        def nearest_food_distance(bot):
            head_x, head_y = bot.get_body()[0]
            return min(
                (abs(head_x - fx) + abs(head_y - fy) for fx, fy in self.foods),
                default=0,
            )

        # Сначала раздаём еду тем, кто сейчас собирает, и самым «голодным» по пути
        ordered = sorted(bots, key=lambda bot: (bot.mode != "forage", nearest_food_distance(bot)))
        for bot in ordered:
            if not available:
                break
            head_x, head_y = bot.get_body()[0]
            target = min(
                available,
                key=lambda food: abs(head_x - food[0]) + abs(head_y - food[1]),
            )
            result[id(bot)] = target
            available.remove(target)
        return result

    def crowd_penalty(self, cell, bot):
        """Штраф за движение вплотную к другим ботам при сборе еды."""
        penalty = 0
        for other in self.all_snakes():
            if other is bot or not other.alive:
                continue
            other_x, other_y = other.get_body()[0]
            distance = abs(cell[0] - other_x) + abs(cell[1] - other_y)
            if distance <= 2:
                penalty += (3 - distance) * 2.0
        return penalty

    def attack_point(self, victim, bot=None, style="front"):
        """Куда бот стремится: отрезать спереди или зайти в кольцо сбоку."""
        head_x, head_y = victim.get_body()[0]
        dir_x, dir_y = victim.direction

        if style == "ring":
            side_x, side_y = -dir_y, dir_x
            candidates = []
            for sign in (-1, 1):
                attack_x = head_x + dir_x * 2 + side_x * 3 * sign
                attack_y = head_y + dir_y * 2 + side_y * 3 * sign
                point = self.clamp_point((attack_x, attack_y))
                if point not in candidates:
                    candidates.append(point)
            if candidates:
                if bot is not None:
                    bot_x, bot_y = bot.get_body()[0]
                    return min(
                        candidates,
                        key=lambda point: abs(point[0] - bot_x) + abs(point[1] - bot_y),
                    )
                return candidates[0]
            return self.clamp_point((head_x, head_y))

        if style == "back":
            # Забегаем вперёд по ходу жертвы и подставляем ей спину
            attack_x = head_x + dir_x * 3
            attack_y = head_y + dir_y * 3
            if bot is not None:
                side_x, side_y = -dir_y, dir_x
                attack_x += side_x * bot.flank * 2
                attack_y += side_y * bot.flank * 2
            return self.clamp_point((attack_x, attack_y))

        attack_x, attack_y = head_x + dir_x * 2, head_y + dir_y * 2
        if bot is not None:
            # Каждый бот заходит со своего плеча, а не встаёт в общую очередь
            side_x, side_y = -dir_y, dir_x
            attack_x += side_x * bot.flank
            attack_y += side_y * bot.flank
        return self.clamp_point((attack_x, attack_y))

    def body_block_reward(self, new_head, bot, victim, steps=3):
        """Награда, если тело бота окажется на пути жертвы (подставить спину)."""
        if victim is None or victim is bot:
            return 0.0

        if bot.grow:
            body = [new_head] + bot.get_body()
        else:
            body = [new_head] + bot.get_body()[:-1]
        blocking = set(body[1:])

        victim_x, victim_y = victim.get_body()[0]
        dir_x, dir_y = victim.direction
        reward = 0.0
        for step in range(1, steps + 1):
            cell = (victim_x + dir_x * step, victim_y + dir_y * step)
            if cell in blocking:
                reward += (steps - step + 1) * 2.0
        return reward

    def choose_bot_direction(self, bot):
        head_x, head_y = bot.get_body()[0]
        personality = PERSONALITIES[bot.personality]
        fatigued = bot.fatigue_timer > 0

        if fatigued or bot.goal == "score":
            # Устал или идёт к автоматической победе: игнорируем охоту
            target = None
            attack = None
            food_target = None
            if self.foods:
                food_target = self.food_targets.get(id(bot))
                if food_target is None:
                    food_target = min(
                        self.foods,
                        key=lambda food: abs(head_x - food[0]) + abs(head_y - food[1]),
                    )
        else:
            # Все боты атакуют: даже собирая еду, они давят на ближайшую цель
            target = self.pick_target(bot)
            attack = self.attack_point(target, bot, bot.attack_style) if target else None
            food_target = self.food_targets.get(id(bot))
            if food_target is None and self.foods:
                food_target = min(
                    self.foods,
                    key=lambda food: abs(head_x - food[0]) + abs(head_y - food[1]),
                )

        length_advantage = 0
        if target is not None:
            length_advantage = len(bot.get_body()) - len(target.get_body())

        blocked = self.blocked_cells()
        options = []

        for direction in DIRECTIONS:
            if direction == opposite(bot.direction):
                continue

            new_head = (head_x + direction[0], head_y + direction[1])
            if not self.is_safe_cell(new_head, bot):
                continue

            space = self.open_space(new_head, blocked)
            danger = self.head_danger(new_head, bot)

            if food_target is not None:
                food_distance = (
                    abs(new_head[0] - food_target[0]) + abs(new_head[1] - food_target[1])
                )
            else:
                food_distance = 0

            hunt_distance = 0
            if attack is not None:
                hunt_distance = abs(new_head[0] - attack[0]) + abs(new_head[1] - attack[1])

            crowd = 0.0
            if bot.mode == "forage":
                crowd = self.crowd_penalty(new_head, bot)
            elif bot.mode == "hunt":
                # Немного не любим идти строго друг за другом даже на охоте
                crowd = self.crowd_penalty(new_head, bot) * 0.4

            # Награда за то, что тело оказалось на пути жертвы
            block = self.body_block_reward(new_head, bot, target)
            block_weight = 1.0 if bot.attack_style == "back" else 0.35
            danger_weight = 3.0
            wall_weight = 1.0

            # Если жертва прижата к стене — используем это и давим к краю
            if target is not None:
                target_wall = self.distance_to_wall(target.get_body()[0])
                if target_wall <= 2:
                    wall_weight = 0.35
                elif target_wall <= 4:
                    wall_weight = 0.65

            if fatigued:
                # Усталость перекрывает охоту: резко идём за едой
                food_weight = 2.2
                hunt_weight = 0.0
                block_weight = 0.0
            else:
                food_weight = personality["food_weight"]
                # При сборе еды охота слабее, но всё равно присутствует
                hunt_weight = personality["hunt_weight"]
                if bot.mode != "hunt":
                    hunt_weight *= 0.55

                # Преимущество в длине: давим сильнее и смелее ставим тело
                if length_advantage > 0:
                    boldness = min(0.6, length_advantage * 0.06)
                    hunt_weight *= 1.0 + boldness
                    block_weight += min(0.8, length_advantage * 0.10)
                    danger_weight = max(
                        1.6, 3.0 - min(1.2, length_advantage * 0.10)
                    )

            # У стены еда всё равно стоит риска — разрешаем шаг на неё
            wall = self.wall_penalty(new_head, direction)
            if food_target is not None and new_head == food_target:
                wall = 0.0

            score = (
                food_distance * food_weight
                + hunt_distance * hunt_weight * bot.aggression
                - min(space, 120) * 0.10
                + danger * danger_weight
                + crowd
                - block * block_weight
                + wall * wall_weight
                + random.uniform(0.0, 0.6)
            )
            options.append((score, direction))

        if not options:
            return bot.direction

        options.sort(key=lambda item: item[0])
        return options[0][1]

    def tick(self):
        if self.state != "playing":
            return

        # Постепенное сжатие поля
        if self.can_shrink():
            self.shrink_timer -= 1
            if self.shrink_timer <= 0:
                self.shrink_arena()
                self.shrink_timer = SHRINK_INTERVAL_TICKS
                if not self.player.alive:
                    self.begin_observation()
                    if self.state != "playing":
                        return

        for bot in self.bots:
            if bot.alive:
                self.update_bot_behavior(bot)

        self.food_targets = self.assign_food_targets(
            [bot for bot in self.bots if bot.alive]
        )
        for bot in self.bots:
            if bot.alive:
                bot.next_direction = self.choose_bot_direction(bot)

        snakes = [snake for snake in self.all_snakes() if snake.alive]
        for snake in snakes:
            snake.update()

        # Стены и собственное тело
        for snake in snakes:
            if not self.in_bounds(snake.get_body()[0]):
                snake.alive = False
                if snake.is_player:
                    self.lose_reason = "Ты врезался в стену"
            elif snake.get_body()[0] in snake.get_body()[1:]:
                snake.alive = False
                if snake.is_player:
                    self.lose_reason = "Ты врезался в собственное тело"

        # Лобовые столкновения головами
        for i, first in enumerate(snakes):
            for second in snakes[i + 1:]:
                if first.alive and second.alive and first.get_body()[0] == second.get_body()[0]:
                    first.alive = False
                    second.alive = False
                    if first.is_player:
                        self.lose_reason = "Лобовое столкновение с ботом"
                    elif second.is_player:
                        self.lose_reason = "Лобовое столкновение с ботом"

        # Голова коснулась тела другого персонажа (проверяем одновременно)
        contenders = [snake for snake in snakes if snake.alive]
        dead_by_body = set()
        for snake in contenders:
            for other in contenders:
                if other is snake:
                    continue
                if snake.get_body()[0] in other.get_body()[1:]:
                    dead_by_body.add(id(snake))
                    if snake.is_player:
                        self.lose_reason = "Голова коснулась тела бота"
                    break
        for snake in contenders:
            if id(snake) in dead_by_body:
                snake.alive = False

        # Определяем занятые места для погибших в этом такте
        survivors = [snake for snake in snakes if snake.alive]
        if len(survivors) < len(snakes):
            place = len(survivors) + 1
            for snake in snakes:
                if not snake.alive and snake.place is None:
                    snake.place = place
                    if snake.is_player:
                        self.player_place = place

        # Поедание еды
        for snake in snakes:
            if not snake.alive:
                continue
            for food in list(self.foods):
                if snake.get_body()[0] == food:
                    snake.eat()
                    snake.food_eaten += 1
                    snake.hunger = 0
                    snake.fatigue_timer = 0
                    self.foods.remove(food)
                    if snake.is_player:
                        self.score += 1
                    break

        self.bots = [bot for bot in self.bots if bot.alive]
        self.maintain_food()

        # Автоматическая победа игрока по очкам
        if self.player.alive and self.score >= self.win_score:
            self.player_place = 1
            self.winner = self.player
            self.state = "win"
            return

        # Автоматическая победа бота по очкам
        goal_bot = next(
            (bot for bot in self.bots if bot.food_eaten >= self.win_score), None
        )
        if goal_bot is not None:
            self.winner = goal_bot
            if self.player.alive:
                self.lose_reason = f"{goal_bot.name} набрал {self.win_score} очков"
                self.player_place = 1 + sum(
                    1
                    for snake in self.all_snakes()
                    if snake.alive and not snake.is_player
                    and snake.food_eaten > self.score
                )
            self.state = "lose"
            return

        if not self.player.alive:
            self.begin_observation()
            return

    def begin_observation(self):
        """После гибели игрока не заканчиваем игру — досматриваем бой ботов."""
        self.player_dead = True
        self.bots = [bot for bot in self.bots if bot.alive]
        if len(self.bots) <= 1:
            self.winner = self.bots[0] if self.bots else None
            self.state = "lose"

    def finish_observation(self):
        """Досрочно завершить наблюдение и перейти к итогам."""
        if not self.player_dead or self.state != "playing":
            return
        self.bots = [bot for bot in self.bots if bot.alive]
        # Победитель не определён — бой прерван досрочно
        self.winner = None
        self.state = "lose"


class TextRenderer:
    def __init__(self):
        self.cache = {}

    def render(self, font, text, color):
        key = (font, text, color)
        if key in self.cache:
            return self.cache[key]

        if len(self.cache) > 256:
            glDeleteTextures([tex_id for tex_id, _, _ in self.cache.values()])
            self.cache.clear()

        text_surface = font.render(text, True, color)
        flipped = pygame.transform.flip(text_surface, False, True)

        texture_data = pygame.image.tostring(flipped, "RGBA", True)
        width = flipped.get_width()
        height = flipped.get_height()

        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)
        glBindTexture(GL_TEXTURE_2D, 0)

        self.cache[key] = (tex_id, width, height)
        return self.cache[key]

    def draw(self, x, y, font, text, color):
        tex_id, width, height = self.render(font, text, color)

        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(1.0, 1.0, 1.0, 1.0)
        glBindTexture(GL_TEXTURE_2D, tex_id)

        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(x, y)
        glTexCoord2f(1, 0); glVertex2f(x + width, y)
        glTexCoord2f(1, 1); glVertex2f(x + width, y + height)
        glTexCoord2f(0, 1); glVertex2f(x, y + height)
        glEnd()

        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)

    def draw_center(self, center_x, y, font, text, color):
        _, width, _ = self.render(font, text, color)
        self.draw(center_x - width // 2, y, font, text, color)

    def draw_bottom_left(self, x, bottom, font, text, color, margin=10):
        _, _, height = self.render(font, text, color)
        self.draw(x, bottom - height - margin, font, text, color)

    def draw_bottom_center(self, center_x, bottom, font, text, color, margin=10):
        _, _, height = self.render(font, text, color)
        self.draw_center(center_x, bottom - height - margin, font, text, color)

def load_font(size):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


def draw_rect(x, y, color, is_head=False):
    glColor3f(*color)
    glBegin(GL_QUADS)
    px = x * GRID_SIZE
    py = y * GRID_SIZE
    size = GRID_SIZE
    padding = 1 if not is_head else 0
    glVertex2f(px + padding, py + padding)
    glVertex2f(px + size - padding, py + padding)
    glVertex2f(px + size - padding, py + size - padding)
    glVertex2f(px + padding, py + size - padding)
    glEnd()


def draw_overlay(alpha=0.72):
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(0.02, 0.03, 0.05, alpha)
    glBegin(GL_QUADS)
    glVertex2f(0, 0)
    glVertex2f(WINDOW_WIDTH, 0)
    glVertex2f(WINDOW_WIDTH, WINDOW_HEIGHT)
    glVertex2f(0, WINDOW_HEIGHT)
    glEnd()
    glDisable(GL_BLEND)


def draw_grid():
    glColor3f(*COLOR_GRID)
    glBegin(GL_LINES)
    for x in range(0, WINDOW_WIDTH + 1, GRID_SIZE):
        glVertex2f(x, 0)
        glVertex2f(x, WINDOW_HEIGHT)
    for y in range(0, WINDOW_HEIGHT + 1, GRID_SIZE):
        glVertex2f(0, y)
        glVertex2f(WINDOW_WIDTH, y)
    glEnd()


def draw_arena(game):
    """Подсвечиваем текущие границы поля и затемняем всё за ними."""
    x0 = game.arena_left * GRID_SIZE
    y0 = game.arena_top * GRID_SIZE
    x1 = (game.arena_right + 1) * GRID_SIZE
    y1 = (game.arena_bottom + 1) * GRID_SIZE

    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(0.02, 0.03, 0.05, 0.62)
    glBegin(GL_QUADS)
    # Сверху
    glVertex2f(0, 0); glVertex2f(WINDOW_WIDTH, 0)
    glVertex2f(WINDOW_WIDTH, y0); glVertex2f(0, y0)
    # Снизу
    glVertex2f(0, y1); glVertex2f(WINDOW_WIDTH, y1)
    glVertex2f(WINDOW_WIDTH, WINDOW_HEIGHT); glVertex2f(0, WINDOW_HEIGHT)
    # Слева
    glVertex2f(0, y0); glVertex2f(x0, y0)
    glVertex2f(x0, y1); glVertex2f(0, y1)
    # Справа
    glVertex2f(x1, y0); glVertex2f(WINDOW_WIDTH, y0)
    glVertex2f(WINDOW_WIDTH, y1); glVertex2f(x1, y1)
    glEnd()
    glDisable(GL_BLEND)

    glColor3f(0.95, 0.55, 0.20)
    glLineWidth(max(1, s(3)))
    glBegin(GL_LINE_LOOP)
    glVertex2f(x0, y0)
    glVertex2f(x1, y0)
    glVertex2f(x1, y1)
    glVertex2f(x0, y1)
    glEnd()
    glLineWidth(1)


def draw_snake(snake):
    for i, segment in enumerate(snake.get_body()):
        if i == 0:
            draw_rect(segment[0], segment[1], lighten(snake.color), is_head=True)
        else:
            draw_rect(segment[0], segment[1], snake.color)


def draw_game(game, text_renderer, font, font_small):
    draw_grid()
    draw_arena(game)

    for fx, fy in game.foods:
        draw_rect(fx, fy, COLOR_FOOD)

    for bot in game.bots:
        draw_snake(bot)
    if game.player.alive:
        draw_snake(game.player)

    field_status = game.field_status()

    if game.player_dead:
        place = game.player_place if game.player_place is not None else "—"
        text_renderer.draw(s(10), s(10), font, "Ты погиб", (255, 90, 90))
        text_renderer.draw(
            s(10), s(42), font_small,
            f"Место: {place} из {game.total_participants}", COLOR_ACCENT,
        )
        text_renderer.draw(
            s(10), s(68), font_small, f"Боты: {len(game.bots)}/{game.bot_count}", COLOR_TEXT
        )
        text_renderer.draw(
            s(10), s(94), font_small, f"Еда: {len(game.foods)}/{game.food_count}", COLOR_TEXT
        )
        text_renderer.draw(s(10), s(120), font_small, field_status, COLOR_TEXT)
        best_bot = max((bot.food_eaten for bot in game.bots), default=0)
        text_renderer.draw(
            s(10), s(150), font_small,
            f"Лучший бот: {best_bot}/{game.win_score}", COLOR_HINT,
        )
        text_renderer.draw_bottom_center(
            WINDOW_WIDTH // 2, WINDOW_HEIGHT, font_small,
            "Наблюдение за ботами • Space — к итогам", COLOR_HINT, margin=s(10),
        )
        return

    text_renderer.draw(s(10), s(10), font, f"Счёт: {game.score}", COLOR_TEXT)
    text_renderer.draw(
        s(10), s(42), font_small, f"Боты: {len(game.bots)}/{game.bot_count}", COLOR_TEXT
    )
    text_renderer.draw(
        s(10), s(68), font_small, f"Еда: {len(game.foods)}/{game.food_count}", COLOR_TEXT
    )
    text_renderer.draw(s(10), s(94), font_small, field_status, COLOR_TEXT)
    best_bot = max((bot.food_eaten for bot in game.bots), default=0)
    text_renderer.draw(
        s(10), s(120), font_small,
        f"Лучший бот: {best_bot}/{game.win_score}", COLOR_HINT,
    )

    text_renderer.draw_bottom_left(
        s(10), WINDOW_HEIGHT, font_small,
        f"Автоматическая победа: {game.score}/{game.win_score}",
        COLOR_ACCENT, margin=s(10),
    )


def draw_main_menu(text_renderer, font_title, font, font_small):
    text_renderer.draw_center(
        WINDOW_WIDTH // 2, s(220), font_title, "ГАДЮШНИК", COLOR_TITLE_RED
    )
    text_renderer.draw_center(
        WINDOW_WIDTH // 2, s(540), font, "Съешь их всех", COLOR_TEXT
    )

    prompt = "Нажми любую кнопку"
    _, prompt_width, _ = text_renderer.render(font_small, prompt, COLOR_HINT)
    text_renderer.draw(
        WINDOW_WIDTH - prompt_width - s(30),
        WINDOW_HEIGHT - s(70),
        font_small,
        prompt,
        COLOR_HINT,
    )
    text_renderer.draw(s(30), WINDOW_HEIGHT - s(70), font_small, "Esc — выход", COLOR_HINT)


def draw_settings(difficulty_index, bot_count, food_count, selected,
                  text_renderer, font_big, font, font_small):
    text_renderer.draw_center(WINDOW_WIDTH // 2, s(90), font_big, "НАСТРОЙКИ", COLOR_TITLE_RED)

    rows = [
        ("Сложность", difficulty_label(difficulty_index)),
        ("Количество ботов", str(bot_count)),
        ("Количество еды", str(food_count)),
    ]

    for i, (label, value) in enumerate(rows):
        is_selected = i == selected
        color = COLOR_SETTING_SELECTED if is_selected else COLOR_SETTING_RED
        left = "‹ " if is_selected else ""
        right = " ›" if is_selected else ""
        text_renderer.draw_center(
            WINDOW_WIDTH // 2,
            s(240 + i * 85),
            font,
            f"{label}:  {left}{value}{right}",
            color,
        )

    text_renderer.draw_center(
        WINDOW_WIDTH // 2,
        s(470),
        font_small,
        f"Поле: {field_label()}",
        COLOR_HINT,
    )
    text_renderer.draw_center(
        WINDOW_WIDTH // 2,
        s(510),
        font_small,
        f"Для автоматической победы нужно: {win_score_for(bot_count, food_count)} очков",
        COLOR_ACCENT,
    )
    text_renderer.draw_center(
        WINDOW_WIDTH // 2,
        s(555),
        font_small,
        "↑ ↓ — выбор    ← → — изменить    Enter — играть    Esc — назад",
        COLOR_TEXT,
    )


def draw_end_screen(game, won, text_renderer, font_big, font, font_small):
    draw_overlay()

    if won:
        title = "ПОБЕДА!"
        color = (110, 255, 150)
        subtitle = f"Автоматическая победа: {game.win_score} очков"
        place_line = f"Место: 1 из {game.total_participants}"
        score_line = f"Счёт: {game.score} / {game.win_score}"
    else:
        title = "ПРОИГРЫШ"
        color = (255, 90, 90)
        subtitle = game.lose_reason or "Ты погиб"
        place = game.player_place if game.player_place is not None else "—"
        place_line = f"Место: {place} из {game.total_participants}"
        score_line = f"Счёт: {game.score} / {game.win_score}"
        winner_line = None
        if game.winner is not None and not game.winner.is_player:
            winner_line = (
                f"Победитель: {game.winner.name} ({game.winner.personality_title}) "
                f"• {game.winner.food_eaten}/{game.win_score}"
            )

    text_renderer.draw_center(WINDOW_WIDTH // 2, s(150), font_big, title, color)
    text_renderer.draw_center(WINDOW_WIDTH // 2, s(240), font, subtitle, COLOR_TEXT)
    text_renderer.draw_center(WINDOW_WIDTH // 2, s(290), font, place_line, COLOR_ACCENT)
    text_renderer.draw_center(WINDOW_WIDTH // 2, s(335), font_small, score_line, COLOR_TEXT)
    if not won and winner_line:
        text_renderer.draw_center(WINDOW_WIDTH // 2, s(375), font_small, winner_line, COLOR_SETTING_RED)
    text_renderer.draw_center(
        WINDOW_WIDTH // 2,
        s(420),
        font_small,
        "R — играть снова    M — настройки    Esc — меню",
        COLOR_TEXT,
    )


def init_opengl():
    glViewport(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_WIDTH, WINDOW_HEIGHT, 0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glClearColor(*COLOR_BG, 1.0)

def set_resolution(index):
    global WINDOW_WIDTH, WINDOW_HEIGHT, GRID_WIDTH, GRID_HEIGHT, UI_SCALE
    WINDOW_WIDTH, WINDOW_HEIGHT = RESOLUTIONS[index]
    GRID_WIDTH = WINDOW_WIDTH // GRID_SIZE
    GRID_HEIGHT = WINDOW_HEIGHT // GRID_SIZE
    UI_SCALE = WINDOW_HEIGHT / 720.0
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), DOUBLEBUF | OPENGL)
    init_opengl()


def make_fonts():
    return (
        load_font(max(24, int(104 * UI_SCALE))),
        load_font(max(18, int(58 * UI_SCALE))),
        load_font(max(14, int(28 * UI_SCALE))),
        load_font(max(12, int(22 * UI_SCALE))),
    )


def main():
    pygame.init()
    pygame.display.set_caption("Гадюшник")
    pygame.time.set_timer(USEREVENT, 100)

    difficulty_index = DEFAULT_DIFFICULTY_INDEX
    _, bot_count, food_count = DIFFICULTIES[difficulty_index]
    selected_setting = 0

    set_resolution(0)
    font_title, font_big, font, font_small = make_fonts()
    text_renderer = TextRenderer()

    clock = pygame.time.Clock()
    state = "menu"
    game = None

    while True:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == KEYDOWN:
                if state == "menu":
                    if event.key == K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    state = "settings"

                elif state == "settings":
                    if event.key == K_ESCAPE:
                        state = "menu"
                    elif event.key in (K_UP, K_DOWN):
                        delta = -1 if event.key == K_UP else 1
                        selected_setting = (selected_setting + delta) % 3
                    elif event.key in (K_LEFT, K_RIGHT):
                        delta = -1 if event.key == K_LEFT else 1
                        if selected_setting == 0:
                            # Сложность задаёт ботов и еду сразу
                            if difficulty_index is None:
                                new_index = 0
                            else:
                                new_index = difficulty_index + delta
                            new_index = max(0, min(len(DIFFICULTIES) - 1, new_index))
                            difficulty_index = new_index
                            _, bot_count, food_count = DIFFICULTIES[new_index]
                        elif selected_setting == 1:
                            bot_count = max(MIN_BOTS, min(MAX_BOTS, bot_count + delta))
                            difficulty_index = match_difficulty(bot_count, food_count)
                        else:
                            food_count = max(1, min(MAX_FOOD, food_count + delta))
                            difficulty_index = match_difficulty(bot_count, food_count)
                    elif event.key in (K_RETURN, K_KP_ENTER, K_SPACE):
                        game = Game(bot_count, food_count)
                        state = "playing"

                elif state == "playing":
                    if event.key == K_ESCAPE:
                        game = None
                        state = "menu"
                    elif game is not None and game.player_dead:
                        if event.key == K_SPACE:
                            game.finish_observation()
                            if game.state == "lose":
                                state = "lose"
                    elif game is not None and game.player.alive:
                        if event.key == K_UP:
                            game.player.change_direction(UP)
                        elif event.key == K_DOWN:
                            game.player.change_direction(DOWN)
                        elif event.key == K_LEFT:
                            game.player.change_direction(LEFT)
                        elif event.key == K_RIGHT:
                            game.player.change_direction(RIGHT)

                elif state in ("win", "lose"):
                    if event.key == K_r:
                        game = Game(bot_count, food_count)
                        state = "playing"
                    elif event.key == K_m:
                        game = None
                        state = "settings"
                    elif event.key == K_ESCAPE:
                        game = None
                        state = "menu"

            elif event.type == USEREVENT and state == "playing" and game:
                game.tick()
                if game.state == "win":
                    state = "win"
                elif game.state == "lose":
                    state = "lose"

        glClear(GL_COLOR_BUFFER_BIT)
        glLoadIdentity()

        if state == "menu":
            draw_main_menu(text_renderer, font_title, font, font_small)
        elif state == "settings":
            draw_settings(
                difficulty_index,
                bot_count,
                food_count,
                selected_setting,
                text_renderer,
                font_big,
                font,
                font_small,
            )
        else:
            draw_game(game, text_renderer, font, font_small)
            if state == "win":
                draw_end_screen(game, True, text_renderer, font_big, font, font_small)
            elif state == "lose":
                draw_end_screen(game, False, text_renderer, font_big, font, font_small)

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
