import arcade
import math
import random
import json
import os

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_TITLE = "Scary tale"
The_authors = "Воропаев Артём и Кузнецов Максим"

WORLD_LEFT = -500
WORLD_RIGHT = 2200
GROUND_Y = 130
MIN_X_LIMIT = 25

LEVELS_FILE = "Scary_tale_Levels.json"


def load_levels():
    if not os.path.exists(LEVELS_FILE):
        data = {
            "level1": True,
            "level1_completed": False,

            "level2": False,
            "level2_completed": False,

            "level3": False,
            "level3_completed": False,

            "level4": False,
            "level4_completed": False
        }

        with open(LEVELS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    with open(LEVELS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_levels(data):
    with open(LEVELS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def unlock_level(name):
    data = load_levels()
    data[name] = True
    save_levels(data)


############################################################################
# Мир

class WorldView(arcade.View):
    def __init__(self):
        super().__init__()
        self.player_x = 200
        self.player_y = GROUND_Y
        self.change_x = 0
        self.change_y = 0
        self.walk_anim = 0

        self.has_item = False
        self.hidden = False
        self.dead = False

        self.cam_world = arcade.camera.Camera2D()
        self.cam_ui = arcade.camera.Camera2D()

        random.seed(42)

        # Задний фон
        self.trees = [(random.randint(WORLD_LEFT, WORLD_RIGHT), random.randint(400, 650)) for _ in range(40)]
        self.grass = [(x, random.randint(15, 30)) for x in range(WORLD_LEFT, WORLD_RIGHT, 30)]

        # Светлячки)
        self.fireflies = [
            (random.randint(WORLD_LEFT, WORLD_RIGHT),
             random.randint(200, 600),
             random.random() * 6.28)
            for _ in range(60)
        ]

        # Деревья - граница
        self.left_wall_trees = [
            (MIN_X_LIMIT - 60 - i * 40, random.randint(350, 500))
            for i in range(40)
        ]

        self.hint = ""
        self.hint_active = False

        self.time = 0.0
        self.last_direction = 1

        self.ask_exit_menu = False
        self.ask_exit_game = False

    # ------------------------------------------------------------------
    # Система оповещения

    def show_hint(self, text: str):
        self.hint = text
        self.hint_active = True

    # ------------------------------------------------------------------
    # Движение фона

    def draw_parallax_background(self):
        self.cam_ui.position = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        self.cam_ui.use()

        arcade.set_background_color((15, 17, 22))

        # Движение светлячкой)
        for fx, fy, phase in self.fireflies:
            px = (fx - self.player_x * 0.1) + SCREEN_WIDTH / 2
            py = fy + math.sin(self.time * 2 + phase) * 5
            arcade.draw_circle_filled(px, py, 2, (255, 240, 120, 180))

        # Движение заднего фона
        for tx, th in self.trees:
            px = (tx - self.player_x * 0.2) + SCREEN_WIDTH / 2
            arcade.draw_triangle_filled(px, 80, px + 40, 80, px + 20, 80 + th, (10, 12, 15))

        # Движение земли
        arcade.draw_rect_filled(
            arcade.rect.XYWH(SCREEN_WIDTH / 2, 40, (WORLD_RIGHT - WORLD_LEFT) + 500, 80),
            (5, 5, 10)
        )

        # Движение травы
        for gx, gh in self.grass:
            px = (gx - self.player_x * 0.4) + SCREEN_WIDTH / 2
            arcade.draw_triangle_filled(px, 80, px + 20, 80, px + 10, 80 + gh, (5, 5, 10))

    # ------------------------------------------------------------------
    # Деревья - граница

    def draw_left_wall(self):
        self.cam_world.use()
        for tx, th in self.left_wall_trees:
            arcade.draw_triangle_filled(tx, 80, tx + 60, 80, tx + 30, 80 + th, (8, 10, 14))

    # ------------------------------------------------------------------
    # Персонаж

    def draw_lars(self):
        x = self.player_x
        y = self.player_y
        breath = math.sin(arcade.get_window().time * 2) * 2
        leg_off = 0
        if abs(self.change_x) > 0:
            self.walk_anim += 0.2
            leg_off = math.sin(self.walk_anim * 5) * 10

        base_y = y - 20

        # Ноги в кусте
        leg_color = (160, 160, 160) if not self.hidden else (110, 110, 120)
        arcade.draw_line(x - 6, base_y, x - 6, base_y - 40 + leg_off, leg_color, 3)
        arcade.draw_line(x + 6, base_y, x + 6, base_y - 40 - leg_off, leg_color, 3)

        # Тело в кусте
        body_color = (190, 190, 200) if not self.hidden else (120, 130, 140)
        arcade.draw_rect_filled(
            arcade.rect.XYWH(x, base_y + 15 + breath / 2, 32, 45),
            body_color
        )

        # Рычаг
        if self.has_item:
            arcade.draw_line(x, base_y + 15, x + 15, base_y + 20, (190, 190, 200), 4)
            arcade.draw_rect_filled(
                arcade.rect.XYWH(x + 15, base_y + 25, 10, 20),
                (255, 80, 80)
            )

        # Голова
        head_y = base_y + 55 + breath
        arcade.draw_circle_filled(x, head_y, 26, (210, 210, 215))

        # Глазки ^_^
        if self.last_direction == 1:
            lx = x - 5
            rx = x + 13
        else:
            lx = x - 13
            rx = x + 5

        arcade.draw_circle_filled(lx, head_y, 4, (20, 20, 30))
        arcade.draw_circle_filled(rx, head_y, 4, (20, 20, 30))

    # ------------------------------------------------------------------
    # Физика

    def update_player(self, delta_time):
        if self.dead or self.hint_active or self.ask_exit_menu or self.ask_exit_game:
            return

        self.time += delta_time

        self.player_x += self.change_x
        self.player_y += self.change_y

        if self.change_x > 0:
            self.last_direction = 1
        elif self.change_x < 0:
            self.last_direction = -1

        if self.player_y > GROUND_Y:
            self.change_y -= 0.8
        else:
            self.player_y = GROUND_Y
            self.change_y = 0

        # Левая граница
        if self.player_x < MIN_X_LIMIT:
            self.player_x = MIN_X_LIMIT
            if not self.hint_active:
                self.show_hint("Слишком темно")

        if self.player_x > WORLD_RIGHT - 50:
            self.player_x = WORLD_RIGHT - 50

    # ------------------------------------------------------------------
    # Система

    def draw_ui(self):
        self.cam_ui.position = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        self.cam_ui.use()

        arcade.draw_text("ESC — выйти в главное меню", 40, 40, (140, 140, 160), 16)

        # Оповещения
        if self.hint_active and self.hint:
            if self.hint == "Слишком темно":
                arcade.draw_text(
                    "Слишком темно...",
                    SCREEN_WIDTH / 2, 80,
                    (180, 40, 40), 22,
                    anchor_x="center", anchor_y="center"
                )
            else:
                y = SCREEN_HEIGHT - 80 if self.hint == "Ворота открываются..." else 80
                arcade.draw_rect_filled(
                    arcade.rect.XYWH(SCREEN_WIDTH / 2, y, 900, 60),
                    (10, 10, 20, 220)
                )
                arcade.draw_rect_outline(
                    arcade.rect.XYWH(SCREEN_WIDTH / 2, y, 900, 60),
                    (0, 200, 200, 150),
                    2
                )
                arcade.draw_text(self.hint, SCREEN_WIDTH / 2, y,
                                 (210, 210, 230), 18,
                                 anchor_x="center", anchor_y="center")

        # Death screen
        if self.dead:
            arcade.draw_rect_filled(
                arcade.rect.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                (10, 0, 0, 180)
            )
            arcade.draw_text("ТЫ ПОТЕРЯЛСЯ В СКАЗКЕ",
                             SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 20,
                             (220, 60, 60), 40, anchor_x="center")
            arcade.draw_text("Нажми R, чтобы возродиться",
                             SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 40,
                             (210, 210, 230), 20, anchor_x="center")

        # Подтверждение(в меню)
        if self.ask_exit_menu:
            arcade.draw_rect_filled(
                arcade.rect.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, 500, 200),
                (10, 10, 20, 230)
            )
            arcade.draw_rect_outline(
                arcade.rect.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, 500, 200),
                (0, 200, 200, 150),
                2
            )
            arcade.draw_text("Выйти в главное меню?",
                             SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 40,
                             (220, 220, 230), 20, anchor_x="center")
            arcade.draw_text("[Y] Да     [N] Нет",
                             SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 20,
                             (200, 200, 200), 18, anchor_x="center")

        # Подтверждение(из игры)
        if self.ask_exit_game:
            arcade.draw_rect_filled(
                arcade.rect.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, 500, 200),
                (10, 10, 20, 230)
            )
            arcade.draw_rect_outline(
                arcade.rect.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, 500, 200),
                (0, 200, 200, 150),
                2
            )
            arcade.draw_text("Выйти из игры?",
                             SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 40,
                             (220, 220, 230), 20, anchor_x="center")
            arcade.draw_text("[Y] Да     [N] Нет",
                             SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 20,
                             (200, 200, 200), 18, anchor_x="center")

    def kill_player(self):
        self.dead = True

    def on_key_release(self, key, modifiers):
        if key in (arcade.key.A, arcade.key.D):
            self.change_x = 0


##############################################################
# Глава 1 - Сломанный механизм
class Level1View(WorldView):
    def __init__(self):
        super().__init__()
        self.LEVER_X = 500
        self.ITEM_X = 1200
        self.GATE_X = 1280

        self.item_placed = False
        self.lever_pulled = False

        # Врата
        self.gate_y = GROUND_Y

        self.show_hint("A / D — движение, Пробел — прыжок.")

    def on_draw(self):
        self.clear()
        self.draw_parallax_background()

        self.cam_world.position = (self.player_x, SCREEN_HEIGHT / 2)
        self.cam_world.use()

        # Деревья-граница
        self.draw_left_wall()

        # Рычаг
        if not self.has_item and not self.item_placed:
            arcade.draw_rect_filled(
                arcade.rect.XYWH(self.ITEM_X, 100, 20, 20),
                (255, 80, 80)
            )
            if abs(self.player_x - self.ITEM_X) < 100 and not self.hint_active:
                arcade.draw_text("E: Взять", self.ITEM_X, 150,
                                 arcade.color.WHITE, 12, anchor_x="center")

        # Основа механизма
        arcade.draw_rect_filled(
            arcade.rect.XYWH(self.LEVER_X, 95, 40, 30),
            (35, 35, 40)
        )

        # Текст над механизмом
        if abs(self.player_x - self.LEVER_X) < 100 and not self.hint_active:
            if self.has_item:
                hint = "Q: Вставить рукоятку"
            elif self.item_placed and not self.lever_pulled:
                hint = "E: Потянуть"
            elif self.lever_pulled:
                hint = "Механизм активирован"
            else:
                hint = "Чего-то не хватает..."
            arcade.draw_text(hint, self.LEVER_X, 200,
                             (200, 180, 50), 14, anchor_x="center")

        # Механизм с рычагом
        if self.item_placed:
            angle = 35 if not self.lever_pulled else -35
            arcade.draw_line(
                self.LEVER_X, 100,
                self.LEVER_X + math.sin(math.radians(angle)) * 60,
                100 + math.cos(math.radians(angle)) * 60,
                (180, 50, 50), 6
            )

        # Врата
        arcade.draw_rect_filled(
            arcade.rect.XYWH(self.GATE_X, self.gate_y + 150, 50, 400),
            (30, 30, 35)
        )

        # Персонаж
        self.draw_lars()

        # UI
        self.draw_ui()

    def on_update(self, delta_time):
        if self.dead or self.hint_active or self.ask_exit_menu or self.ask_exit_game:
            return

        self.update_player(delta_time)

        # Врата стоп - "Ты не пройдёшь!"
        if not self.lever_pulled and self.player_x > self.GATE_X - 45:
            self.player_x = self.GATE_X - 45

        # Врата вниз
        if self.lever_pulled and self.gate_y > -300:
            self.gate_y -= 5

        # Конец - в меню
        if self.lever_pulled and self.player_x > self.GATE_X + 60:
            data = load_levels()
            data["level1_completed"] = True
            data["level2"] = True
            save_levels(data)
            self.window.show_view(LevelSelectView())

    def on_key_press(self, key, modifiers):
        # В менюшку
        if self.ask_exit_menu:
            if key == arcade.key.Y:
                self.window.show_view(LevelSelectView())
            elif key == arcade.key.N:
                self.ask_exit_menu = False
            return

        # Из игры
        if self.ask_exit_game:
            if key == arcade.key.Y:
                arcade.exit()
            elif key == arcade.key.N:
                self.ask_exit_game = False
            return

        # Подсказки В С Ё
        if self.hint_active:
            self.hint_active = False
            return

        # Возрождение
        if self.dead and key == arcade.key.R:
            self.window.show_view(Level1View())
            return

        # ESC в меню
        if key == arcade.key.ESCAPE:
            self.ask_exit_menu = True
            return

        # Движение
        if key == arcade.key.A:
            self.change_x = -6
            self.change_x = -6
        elif key == arcade.key.D:
            self.change_x = 6
        elif key == arcade.key.SPACE and self.player_y <= GROUND_Y + 5:
            self.change_y = 16

        # Взаимодействия
        elif key == arcade.key.E:
            # Взять рукоятку
            if abs(self.player_x - self.ITEM_X) < 60 and not self.has_item and not self.item_placed:
                self.has_item = True

            elif abs(self.player_x - self.LEVER_X) < 100 and self.item_placed:
                self.lever_pulled = True
                self.show_hint("Ворота открываются...")

        elif key == arcade.key.Q:
            if abs(self.player_x - self.LEVER_X) < 100 and self.has_item:
                self.has_item = False
                self.item_placed = True


####################################################################
# Глава 2 - Страж леса

class Level2View(WorldView):
    def __init__(self):
        super().__init__()
        self.bush_x = 900
        self.bush_y = GROUND_Y - 50

        self.monster_x = 1300
        self.monster_y = GROUND_Y + 10

        self.monster_left = WORLD_LEFT - 300
        self.monster_right = 1700
        self.monster_speed = 2
        self.monster_phase = 0

        self.exit_x = 2000

    # ------------------------------------------------------------------
    def draw_monster(self):
        x = self.monster_x
        y = self.monster_y + 30

        arcade.draw_rect_filled(
            arcade.rect.XYWH(x, y, 40, 80),
            (40, 40, 50)
        )

        ex = x
        ey = y + 15
        self.monster_phase += 0.1
        glow = 10 + 3 * math.sin(self.monster_phase)

        arcade.draw_circle_filled(ex - 8, ey, glow, (180, 180, 200, 60))
        arcade.draw_circle_filled(ex + 8, ey, glow, (180, 180, 200, 60))
        arcade.draw_circle_filled(ex - 8, ey, 4, (0, 0, 0))
        arcade.draw_circle_filled(ex + 8, ey, 4, (0, 0, 0))

    # ------------------------------------------------------------------
    def on_draw(self):
        self.clear()
        self.draw_parallax_background()

        self.cam_world.position = (self.player_x, SCREEN_HEIGHT / 2)
        self.cam_world.use()

        self.draw_left_wall()
        self.draw_monster()

        arcade.draw_rect_filled(
            arcade.rect.XYWH(self.bush_x, self.bush_y + 50, 140, 140),
            (30, 80, 40, 180)
        )

        self.draw_lars()
        self.draw_ui()

    # ------------------------------------------------------------------
    def on_update(self, delta_time):
        if self.dead or self.hint_active or self.ask_exit_menu or self.ask_exit_game:
            return

        self.update_player(delta_time)

        in_bush = abs(self.player_x - self.bush_x) < 60 and abs(self.player_y - GROUND_Y) < 30
        self.hidden = in_bush

        # Движение монстра
        self.monster_x += self.monster_speed

        if self.monster_x >= self.monster_right:
            self.monster_x = self.monster_right
            self.monster_speed *= -1

        if self.monster_x <= self.monster_left:
            self.monster_x = self.monster_left
            self.monster_speed *= -1

        # Смерть
        if abs(self.player_x - self.monster_x) < 160 and not self.hidden:
            self.kill_player()

        if self.player_x > self.exit_x:
            data = load_levels()
            data["level2_completed"] = True
            data["level3"] = True
            save_levels(data)
            self.window.show_view(LevelSelectView())
    # ------------------------------------------------------------------
    def on_key_press(self, key, modifiers):
        if self.ask_exit_menu:
            if key == arcade.key.Y:
                self.window.show_view(LevelSelectView())
            elif key == arcade.key.N:
                self.ask_exit_menu = False
            return

        if self.ask_exit_game:
            if key == arcade.key.Y:
                arcade.exit()
            elif key == arcade.key.N:
                self.ask_exit_game = False
            return

        if self.hint_active:
            self.hint_active = False
            return

        if self.dead and key == arcade.key.R:
            self.window.show_view(Level2View())
            return

        if key == arcade.key.ESCAPE:
            self.ask_exit_menu = True
            return

        if key == arcade.key.A:
            self.change_x = -6
        elif key == arcade.key.D:
            self.change_x = 6
        elif key == arcade.key.SPACE and self.player_y <= GROUND_Y + 5:
            self.change_y = 16
        elif key == arcade.key.E:
            if abs(self.player_x - self.bush_x) < 60:
                if self.hidden:
                    self.show_hint("Ты выходишь из укрытия.")
                else:
                    self.show_hint("Слишком темно")

####################################################################
# Глава 3 - Лес отражений

class Level3View(WorldView):
    def __init__(self):
        super().__init__()

        # Клон
        self.clone_offset_x = 80
        self.clone_x = self.player_x + self.clone_offset_x
        self.clone_y = self.player_y

        # Плиты
        self.player_plate_x = 800
        self.clone_plate_x = 970
        self.plate_y = GROUND_Y - 50

        # Дверь
        self.door_x = 1700
        self.door_y = GROUND_Y
        self.door_drop = 0
        self.door_max_drop = 420
        self.door_open = False

        # Выход
        self.exit_x = 2000
        # Подсказка Глава 3
        self.show_hint("Вы встретили своё отражение, а отражения всегда повторяют ваши движения...")
    # --------------------------------------------------------------
    def on_draw(self):
        self.clear()
        self.draw_parallax_background()

        self.cam_world.position = (self.player_x, SCREEN_HEIGHT / 2)
        self.cam_world.use()

        self.draw_left_wall()

        # Плита игрока
        arcade.draw_rect_filled(
            arcade.rect.XYWH(self.player_plate_x, self.plate_y + 10, 140, 20),
            (120, 120, 120)
        )

        # Плита клона
        arcade.draw_rect_filled(
            arcade.rect.XYWH(self.clone_plate_x, self.plate_y + 10, 140, 20),
            (120, 120, 120)
        )

        # Дверь
        arcade.draw_rect_filled(
            arcade.rect.XYWH(self.door_x, self.door_y + 150 - self.door_drop, 50, 400),
            (30, 30, 35)
        )

        # Клон
        arcade.draw_rect_filled(
            arcade.rect.XYWH(self.clone_x, self.clone_y - 20 + 15, 32, 45),
            (120, 120, 150)
        )
        arcade.draw_circle_filled(self.clone_x, self.clone_y - 20 + 55, 26, (200, 200, 220))
        arcade.draw_circle_filled(self.clone_x - 6, self.clone_y - 20 + 55, 4, (0, 0, 0))
        arcade.draw_circle_filled(self.clone_x + 6, self.clone_y - 20 + 55, 4, (0, 0, 0))

        self.draw_lars()
        self.draw_ui()

    # --------------------------------------------------------------
    def on_update(self, dt):
        if self.dead or self.hint_active or self.ask_exit_menu or self.ask_exit_game:
            return

        # Движение игрока
        self.update_player(dt)

        # ----------------------------------------------------------
        # ДВИЖЕНИЕ КЛОНА (НЕ зависит от того, упёрся ли игрок)
        # ----------------------------------------------------------
        if self.change_x < 0:      # игрок влево
            clone_dx = 6           # клон вправо
        elif self.change_x > 0:    # игрок вправо
            clone_dx = -6          # клон влево
        else:
            clone_dx = 0

        self.clone_x += clone_dx

        # Клон НЕ прыгает
        self.clone_y = GROUND_Y

        # Клон упирается в левую границу мира
        if self.clone_x < MIN_X_LIMIT:
            self.clone_x = MIN_X_LIMIT

        # ----------------------------------------------------------
        # СТОЛКНОВЕНИЕ КЛОНА С ДВЕРЬЮ (как у игрока)
        # ----------------------------------------------------------
        door_left = self.door_x - 25
        door_right = self.door_x + 25

        if not self.door_open:
            if door_left < self.clone_x < door_right:
                # Клон упирается в дверь
                self.clone_x = door_left

        # ----------------------------------------------------------
        # СМЕРТЬ ОТ КАСАНИЯ КЛОНА
        # ----------------------------------------------------------
        if abs(self.player_x - self.clone_x) < 40 and abs(self.player_y - self.clone_y) < 50:
            self.kill_player()

        # ----------------------------------------------------------
        # БЛОКИРОВКА ИГРОКА ДВЕРЬЮ
        # ----------------------------------------------------------
        if not self.door_open:
            if door_left < self.player_x < door_right:
                self.player_x = door_left - 5

        # ----------------------------------------------------------
        # ПЛИТЫ
        # ----------------------------------------------------------
        player_on_plate = abs(self.player_x - self.player_plate_x) < 70
        clone_on_plate = abs(self.clone_x - self.clone_plate_x) < 70

        # Если оба стоят — дверь опускается вниз
        if player_on_plate and clone_on_plate and not self.door_open:
            self.door_drop += 5
            if self.door_drop >= self.door_max_drop:
                self.door_open = True
                self.show_hint("Дверь открылась!")

        # ----------------------------------------------------------
        # ВЫХОД
        # ----------------------------------------------------------
        if self.door_open and self.player_x > self.exit_x + 60:
            data = load_levels()
            data["level3_completed"] = True
            data["level4"] = True
            save_levels(data)
            self.window.show_view(LevelSelectView())

    # --------------------------------------------------------------
    def on_key_press(self, key, modifiers):
        if self.ask_exit_menu:
            if key == arcade.key.Y:
                self.window.show_view(LevelSelectView())
            elif key == arcade.key.N:
                self.ask_exit_menu = False
            return

        if self.ask_exit_game:
            if key == arcade.key.Y:
                arcade.exit()
            elif key == arcade.key.N:
                self.ask_exit_game = False
            return

        if self.hint_active:
            self.hint_active = False
            return

        if self.dead and key == arcade.key.R:
            self.window.show_view(Level3View())
            return

        if key == arcade.key.ESCAPE:
            self.ask_exit_menu = True
            return

        # Управление игроком
        if key == arcade.key.A:
            self.change_x = -6
        elif key == arcade.key.D:
            self.change_x = 6
        elif key == arcade.key.SPACE and self.player_y <= GROUND_Y + 5:
            self.change_y = 16

################################################################
# Главное меню

class LevelSelectView(arcade.View):
    def __init__(self):
        super().__init__()
        self.levels = load_levels()
        self.ask_exit_game = False
        self.show_updates = False

    def on_draw(self):
        self.clear((10, 10, 15))

        arcade.draw_text("Scary tale", SCREEN_WIDTH / 2, SCREEN_HEIGHT - 120,
                         (220, 220, 230), 48, anchor_x="center")
        arcade.draw_text("Выбор главы", SCREEN_WIDTH / 2, SCREEN_HEIGHT - 180,
                         (210, 210, 230), 26, anchor_x="center")

        y = 380
        entries = [
            ("[1] Глава 1: Сломанный механизм", "level1"),
            ("[2] Глава 2: Страж леса", "level2"),
            ("[3] Глава 3: Лес отражений", "level3"),
            ("[4] Глава 4: Домик на опушке", "level4"),
        ]

        for text, key in entries:
            unlocked = self.levels.get(key, False)
            color = (210, 210, 230) if unlocked else (90, 90, 110)
            arcade.draw_text(text, 260, y, color, 24)
            if not unlocked:
                arcade.draw_text("ЗАКРЫТО", 800, y, (120, 60, 60), 18)
            y -= 60

        # Прогресс
        total = 4
        completed = 0
        if self.levels.get("level1_completed"): completed += 1
        if self.levels.get("level2_completed"): completed += 1
        if self.levels.get("level3_completed"): completed += 1
        if self.levels.get("level4_completed"): completed += 1

        progress = completed / total

        bar_x = SCREEN_WIDTH / 2
        bar_y = 120
        bar_w = 600
        bar_h = 20

        arcade.draw_rect_filled(
            arcade.rect.XYWH(bar_x, bar_y, bar_w, bar_h),
            (40, 40, 50)
        )

        arcade.draw_rect_filled(
            arcade.rect.XYWH(bar_x - bar_w / 2 + (bar_w * progress) / 2, bar_y,
                             bar_w * progress, bar_h),
            (80, 180, 80)
        )

        arcade.draw_text(
            f"Прогресс: {completed}/{total}",
            bar_x, bar_y + 30,
            (200, 200, 210), 18,
            anchor_x="center"
        )

        arcade.draw_text("ESC - выйти из игры", 40, 40, (140, 140, 160), 16)

        if self.ask_exit_game:
            arcade.draw_rect_filled(
                arcade.rect.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, 500, 200),
                (10, 10, 20, 230)
            )
            arcade.draw_rect_outline(
                arcade.rect.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, 500, 200),
                (0, 200, 200, 150),
                2
            )
            arcade.draw_text("Выйти из игры?",
                             SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 40,
                             (220, 220, 230), 20, anchor_x="center")
            arcade.draw_text("[Y] Да     [N] Нет",
                             SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 20,
                             (200, 200, 200), 18, anchor_x="center")
        # Кнопка Обновлений
        arcade.draw_rect_filled(
            arcade.rect.XYWH(SCREEN_WIDTH - 120, SCREEN_HEIGHT - 40, 180, 40),
            (30, 30, 40)
        )
        arcade.draw_rect_outline(
            arcade.rect.XYWH(SCREEN_WIDTH - 120, SCREEN_HEIGHT - 40, 180, 40),
            (120, 200, 200),
            2
        )
        arcade.draw_text(
            "[0] Обновления",
            SCREEN_WIDTH - 120, SCREEN_HEIGHT - 40,
            (220, 220, 230), 18,
            anchor_x="center", anchor_y="center"
        )
        # Окно обновлений
        if self.show_updates:
            arcade.draw_rect_filled(
                arcade.rect.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, 700, 400),
                (10, 10, 20, 240)
            )
            arcade.draw_rect_outline(
                arcade.rect.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, 700, 400),
                (0, 200, 200),
                2
            )

            arcade.draw_text(
                "Обновления игры",
                SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 150,
                (220, 220, 230), 26,
                anchor_x="center"
            )
            # Обновления содержимое
            lines = ["- Добавлены ещё комментарии по всему коду",
                     "- Исправлены имена классов уровней",
                     "- Добавлена кнопка обновлений",
                     "- Добавлена возможность выбора уровней и ",
                     "   кнопки обновлений мышкой",
                     "- В главе 2 исправлена текстура куста",
                     "- Добавлена Глава 3",
                     "- Добавлена заглушка на Главу 4"]

            start_x = SCREEN_WIDTH / 2 - 320
            start_y = SCREEN_HEIGHT / 2 + 90
            line_height = 28
            for i, line in enumerate(lines):
                arcade.draw_text( line, start_x, start_y - i * line_height, (200, 200, 210), 18)

            arcade.draw_text(
                "[Нажмите любую клавишу или мышку, чтобы закрыть]",
                SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 180,
                (160, 160, 180), 16,
                anchor_x="center"
            )

    def on_key_press(self, key, modifiers):
        # Меню обновлений
        if self.show_updates:
            self.show_updates = False
            return

        if key == arcade.key.KEY_0:
            self.show_updates = True
            return

        # Выход из игры
        if self.ask_exit_game:
            if key == arcade.key.Y:
                arcade.exit()
            elif key == arcade.key.N:
                self.ask_exit_game = False
            return

        if key == arcade.key.ESCAPE:
            self.ask_exit_game = True
            return

        # Основные кнопки
        if key == arcade.key.KEY_1:
            self.window.show_view(Level1View())
        if key == arcade.key.KEY_2 and self.levels.get("level2", False):
            self.window.show_view(Level2View())
        if key == arcade.key.KEY_3 and self.levels.get("level3", False):
            self.window.show_view(Level3View())
        # if key == arcade.key.KEY_4 and self.levels.get("level4", False):
        #     self.window.show_view(Level4View())


    # Выбор глав мышкой
    def on_mouse_press(self, x, y, button, modifiers):
        # Если окно обновлений открыто
        if self.show_updates:
            self.show_updates = False
            return
        # Кнопка Обновлений
        if SCREEN_WIDTH - 210 < x < SCREEN_WIDTH - 30 and SCREEN_HEIGHT - 60 < y < SCREEN_HEIGHT - 20:
            self.show_updates = True
            return

        # Выход из игры
        if self.ask_exit_game:
            return

        start_y = 380
        step = 60
        entries = [
            ("[1] Глава 1: Сломанный механизм", "level1"),
            ("[2] Глава 2: Страж леса", "level2"),
            ("[3] Глава 3: Лес отражений", "level3"),
            ("[4] Глава 4: Домик на опушке", "level4"),
        ]

        for i, (_, key) in enumerate(entries):
            row_y = start_y - i * step
            if 260 <= x <= 900 and row_y - 10 <= y <= row_y + 30:
                if not self.levels.get(key, False):
                    return
                if key == "level1":
                    self.window.show_view(Level1View())
                elif key == "level2":
                    self.window.show_view(Level2View())
                elif key == "level3":
                    self.window.show_view(Level3View())
                # elif key == "level4":
                #     self.window.show_view(Level4View())
                return

#########################################################################
# Интро

class IntroView(arcade.View):
    def __init__(self):
        super().__init__()
        self.alpha = 0
        self.fade_in = True
        self.timer = 0

        self.title = arcade.Text(
            "Scary tale",
            SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 40,
            (220, 220, 230), 60, anchor_x="center"
        )
        self.sub = arcade.Text(
            "Одна старая и страшная байка",
            SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 40,
            (210, 210, 230), 22, anchor_x="center"
        )

    def on_draw(self):
        self.clear((0, 0, 0))

        col = (220, 220, 230, int(self.alpha))
        self.title.color = col
        self.sub.color = col

        self.title.draw()
        self.sub.draw()

        if self.alpha >= 250:
            arcade.draw_text("Нажмите любую клавишу",
                             SCREEN_WIDTH / 2, 120,
                             (200, 200, 220), 18,
                             anchor_x="center")

    def on_update(self, dt):
        self.timer += dt
        if self.fade_in:
            self.alpha += 60 * dt
            if self.alpha >= 255:
                self.alpha = 255
                self.fade_in = False
        else:
            self.alpha = 240 + 10 * math.sin(self.timer * 2)

    def on_key_press(self, key, modifiers):
        self.window.show_view(LevelSelectView())

    def on_mouse_press(self, x, y, button, modifiers):
        self.window.show_view(LevelSelectView())


#################################################################
# Main / General

def main():
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    window.show_view(IntroView())
    arcade.run()


if __name__ == "__main__":
    main()
