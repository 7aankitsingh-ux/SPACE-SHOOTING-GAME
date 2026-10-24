import arcade
import math
import random
from pathlib import Path

from PIL import Image

SCREEN_WIDTH = 900
SCREEN_HEIGHT = 600
SCREEN_TITLE = "SPACE SHOOTER"

# Player settings
PLAYER_SPEED = 6
PLAYER_RADIUS = 20
PLAYER_MAX_HEALTH = 30
PLAYER_SHOOT_COOLDOWN = 0.2

# Player bullet settings
BULLET_SPEED = 12
BULLET_RADIUS = 5
BULLET_DAMAGE = 1

# Enemy settings
ENEMY_SPAWN_RATE = 0.5
ENEMY_SPEED_MIN = 1.0
ENEMY_SPEED_MAX = 3.5
ENEMY_RADIUS = 18
ENEMY_MIN_HEALTH = 1
ENEMY_MAX_HEALTH = 3
ENEMY_DAMAGE = 1

# Red shooting enemy settings
SHOOT_ENEMY_CHANCE = 0.2  # 0.2 means 20% of spawned enemies are red
SHOOT_ENEMY_MIN_SPEED = 1.0
SHOOT_ENEMY_MAX_SPEED = 2.0
SHOOT_ENEMY_MIN_HEALTH = 2
SHOOT_ENEMY_MAX_HEALTH = 4
ENEMY_BULLET_SPEED = 5
ENEMY_BULLET_RADIUS = 6
ENEMY_BULLET_DAMAGE = 1
ENEMY_SHOOT_COOLDOWN = 0.8
SHOOT_ENEMY_PREFERRED_DISTANCE = 230
SHOOT_ENEMY_DISTANCE_TOLERANCE = 35

# Boss settings
BOSS_SPAWN_EVERY = 200          # a boss shows up every 200 points
BOSS_RADIUS = 45                # much bigger than normal enemies (18)
BOSS_HEALTH = 30
BOSS_SPEED = 0.9
BOSS_SHOOT_COOLDOWN = 4.0       # one shot every 4 seconds
BOSS_BULLET_SPEED = 4
BOSS_BULLET_RADIUS = 14
BOSS_BULLET_DAMAGE = 3
BOSS_CONTACT_DAMAGE = 5
BOSS_CONTACT_COOLDOWN = 1.0     # boss can hurt you by touching once per second
BOSS_SCORE = 50
BOSS_PREFERRED_DISTANCE = 260

# Power-up settings
POWERUP_DROP_CHANCE = 0.12      # chance that a normal enemy drops a power-up
POWERUP_RADIUS = 12
POWERUP_LIFETIME = 8.0          # seconds before an uncollected power-up vanishes
HEALTH_PICKUP_AMOUNT = 1        # health power-up gives +1 health
SHIELD_DURATION = 5.0           # seconds
FIRE_DURATION = 6.0             # seconds of rapid fire
FIRE_SHOOT_COOLDOWN = 0.07

# Sound settings
MUSIC_START_VOLUME = 0.5        # background music volume at start (0.0 - 1.0)
MUSIC_VOLUME_STEP = 0.1         # how much each +/- press changes the volume
SFX_VOLUME = 0.6                # sound effects always stay at this volume

# Menu states
STATE_PLAY = "play"
STATE_MENU = "menu"
STATE_SETTINGS = "settings"


# --------------------------------------------------------------------------
# Sprite art (cut out of the sprite sheet, stored in the "assets" folder)
# --------------------------------------------------------------------------
ASSET_DIR = Path(__file__).resolve().parent / "assets"
ROTATION_STEP = 5               # degrees; rotated copies are cached per step

# Facing = the game angle (in degrees) the picture points at when not rotated.
# 90 means "nose points up", -90 means "nose points down".
SPRITE_FILES = {
    #  key              file                facing
    "player":        ("player.png",        90),
    "enemy_blue":    ("enemy_blue.png",    90),
    "enemy_red":     ("enemy_red.png",    -90),
    "boss":          ("boss.png",         -90),
    "bullet_player": ("bullet_player.png", 90),
    "bullet_fire":   ("bullet_fire.png",   90),
    "bullet_enemy":  ("bullet_enemy.png",  90),
    "bullet_boss":   ("boss_bullet.png",   90),
    "pu_health":     ("pu_health.png",     90),
    "pu_shield":     ("pu_shield.png",     90),
    "pu_fire":       ("pu_fire.png",       90),
}

ART = {}                        # key -> SpriteArt, filled by load_art()
_texture_counter = 0


def make_texture(pil_image):
    """Build an arcade texture from a PIL image (arcade 3.x, with 2.6 fallback)."""
    global _texture_counter
    try:
        return arcade.Texture(pil_image)
    except TypeError:
        _texture_counter += 1
        return arcade.Texture(f"space_shooter_tex_{_texture_counter}", pil_image)


def draw_texture(texture, x, y):
    if hasattr(arcade, "draw_texture_rect"):            # arcade 3.x
        arcade.draw_texture_rect(
            texture, arcade.XYWH(x, y, texture.width, texture.height)
        )
    else:                                               # arcade 2.6
        arcade.draw_texture_rectangle(
            x, y, texture.width, texture.height, texture
        )


class SpriteArt:
    """One picture. Rotated copies are made with Pillow and cached, so the ship
    always points the right way no matter which arcade version is installed."""

    def __init__(self, filename, facing):
        self.image = Image.open(ASSET_DIR / filename).convert("RGBA")
        self.facing = facing
        self._cache = {}

    def texture(self, angle=None):
        # angle is in radians (the same angle the game uses for movement)
        if angle is None:
            rot = 0
        else:
            rot = round((math.degrees(angle) - self.facing) / ROTATION_STEP)
            rot = (rot * ROTATION_STEP) % 360

        tex = self._cache.get(rot)
        if tex is None:
            img = self.image
            if rot:
                img = img.rotate(rot, resample=Image.BICUBIC, expand=True)
            tex = make_texture(img.copy())
            self._cache[rot] = tex
        return tex

    def draw(self, x, y, angle=None):
        draw_texture(self.texture(angle), x, y)


def load_art():
    ART.clear()
    for key, (filename, facing) in SPRITE_FILES.items():
        path = ASSET_DIR / filename
        if not path.is_file():
            raise FileNotFoundError(
                f"Required sprite asset is missing: {path}. "
                "Add the expected image to the assets folder."
            )
        try:
            ART[key] = SpriteArt(filename, facing)
        except Exception as error:
            raise RuntimeError(f"Could not load sprite {path}: {error}") from error





# --------------------------------------------------------------------------
# Sounds: robust file discovery and loading
# Replace the old sound section with this complete section.
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Sound loading: exact normalized matching only; no broad fuzzy matches.
# Arcade/pyglet support depends on installed codecs. WAV and OGG are safest;
# MP3 support can vary by platform/runtime. M4A/MP4 are intentionally excluded.
# --------------------------------------------------------------------------
_BASE_DIR = Path(__file__).resolve().parent
# Known locations first, then any project subfolder whose name is "music"
# (case-insensitive), so Music/, assets/music/, and MUSIC/ all work.
SOUND_FOLDERS = [
    _BASE_DIR / "music",
    _BASE_DIR / "Music",
    _BASE_DIR / "assets" / "music",
    _BASE_DIR / "assets" / "Music",
    _BASE_DIR / "assets" / "sounds",
    _BASE_DIR / "assets",
    _BASE_DIR / "sounds",
    _BASE_DIR,
]
SOUND_EXTENSIONS = {".wav", ".ogg", ".mp3"}

SOUND_FILES = {
    "music": ["BACKGROUND", "BACKGROUND_MUSIC", "MUSIC", "BG_MUSIC", "BACKGROUND_MUSIC_LOOP"],
    "boss_defeat": ["BOSS_DEFEAT", "BOSS_DEAD", "BOSS_KILL"],
    "boss_missile": ["BOSS_MISSILE", "BOSS_SHOOT", "BOSS_BULLET"],
    "enemy_dead": [
        "ENEMY_AND_SHOOT_ENEMY_DEAD_SOUND", "ENEMY_DEAD",
        "SHOOT_ENEMY_DEAD_SOUND", "ENEMY_KILL",
    ],
    "game_over": ["GAME_OVER", "GAMEOVER"],
    "player_shoot": ["PLAYER_BULLET_SHOUND", "PLAYER_BULLET_SOUND", "PLAYER_SHOOT"],
    "power_buff": ["POWER_BUFF", "POWERUP", "POWER_UP", "PICKUP"],
    "enemy_shoot": ["SHOOT_ENEMY", "ENEMY_SHOOT", "ENEMY_FIRE"],
}
SOUNDS = {key: None for key in SOUND_FILES}


def normalize_sound_name(name):
    """Normalize case, spaces, underscores and hyphens for exact comparisons."""
    return "".join(char.lower() for char in name if char.isalnum())


def get_sound_search_folders():
    """Return unique search folders, including nested music folders."""
    folders = []
    seen = set()
    for folder in SOUND_FOLDERS:
        resolved = str(folder.resolve()).casefold()
        if resolved not in seen:
            folders.append(folder)
            seen.add(resolved)

    # Find music folders anywhere under the project, including assets/music.
    # Avoid scanning common virtual environments and version-control folders.
    excluded = {".venv", "venv", "__pycache__", ".git", "site-packages"}
    try:
        for candidate in _BASE_DIR.rglob("*"):
            if not candidate.is_dir():
                continue
            if candidate.name.casefold() == "music":
                resolved = str(candidate.resolve()).casefold()
                if resolved not in seen:
                    folders.append(candidate)
                    seen.add(resolved)
    except OSError as error:
        print(f"[sound] Could not discover nested music folders: {error}")
    return folders


def find_sound_file(possible_names):
    wanted = {normalize_sound_name(name) for name in possible_names}
    for folder in get_sound_search_folders():
        if not folder.is_dir():
            continue
        try:
            for path in sorted(folder.rglob("*")):
                if path.is_file() and path.suffix.lower() in SOUND_EXTENSIONS:
                    if normalize_sound_name(path.stem) in wanted:
                        return path
        except OSError as error:
            print(f"[sound] Could not search {folder}: {error}")
    return None


def load_sounds():
    SOUNDS.clear()
    search_folders = get_sound_search_folders()
    print("[sound] Search folders:")
    for folder in search_folders:
        print(f"  - {folder} ({'exists' if folder.is_dir() else 'missing'})")
    discovered = []
    for folder in search_folders:
        if folder.is_dir():
            try:
                discovered.extend(
                    p for p in folder.rglob("*")
                    if p.is_file() and p.suffix.lower() in SOUND_EXTENSIONS
                )
            except OSError as error:
                print(f"[sound] Could not list {folder}: {error}")
    unique = sorted(set(discovered), key=lambda p: str(p).lower())
    print("[sound] Supported extensions: .wav, .ogg, .mp3")
    print("[sound] Discovered audio files:")
    if unique:
        for path in unique:
            print(f"  - {path}")
    else:
        print("  (none found; supported extensions: .wav, .ogg, .mp3)")

    for key, aliases in SOUND_FILES.items():
        SOUNDS[key] = None
        path = find_sound_file(aliases)
        if path is None:
            print(f"[sound] MISSING {key}: expected one of {aliases}")
            continue
        try:
            SOUNDS[key] = arcade.load_sound(str(path))
            print(f"[sound] LOADED {key}: {path}")
        except Exception as error:
            print(f"[sound] FAILED {key}: {path} | {type(error).__name__}: {error}")


def play_sfx(key, volume=SFX_VOLUME):
    sound = SOUNDS.get(key)
    if sound is None:
        return None
    try:
        return arcade.play_sound(sound, volume=max(0.0, min(1.0, volume)))
    except Exception as error:
        print(f"[sound] Could not play {key}: {type(error).__name__}: {error}")
        return None


def is_on_screen(x, y, margin=0):
    return (-margin <= x <= SCREEN_WIDTH + margin and
            -margin <= y <= SCREEN_HEIGHT + margin)


def set_text(text_object, value):
    text_object.text = str(value)


def draw_box(cx, cy, width, height, fill, outline=None, border_width=1):
    """Draw a filled rectangle using Arcade 2.6 or 3.x APIs."""
    if hasattr(arcade, "LBWH") and hasattr(arcade, "draw_rect_filled"):
        rect = arcade.LBWH(cx - width / 2, cy - height / 2, width, height)
        arcade.draw_rect_filled(rect, fill)
        if outline is not None and border_width > 0:
            arcade.draw_rect_outline(rect, outline, border_width)
    else:
        arcade.draw_rectangle_filled(cx, cy, width, height, fill)
        if outline is not None and border_width > 0:
            arcade.draw_rectangle_outline(cx, cy, width, height, outline, border_width)


def draw_health_bar(cx, cy, width, health, max_health):
    max_health = max(1, max_health)
    fraction = max(0.0, min(1.0, health / max_health))
    height = 5
    draw_box(cx, cy, width, height, (45, 45, 55, 220), (180, 180, 190), 1)
    if fraction > 0:
        filled_width = max(1, width * fraction)
        fill_color = arcade.color.GREEN if fraction > 0.5 else (
            arcade.color.YELLOW if fraction > 0.25 else arcade.color.RED
        )
        draw_box(cx - width / 2 + filled_width / 2, cy, filled_width,
                 height - 1, fill_color)


class Button:
    """A clickable rectangle with a centered label."""

    def __init__(self, label, cx, cy, width=240, height=48, font_size=18):
        self.cx = cx
        self.cy = cy
        self.width = width
        self.height = height
        self.text = arcade.Text(
            label,
            cx,
            cy,
            arcade.color.WHITE,
            font_size,
            anchor_x="center",
            anchor_y="center",
        )

    def contains(self, x, y):
        return (
            abs(x - self.cx) <= self.width / 2
            and abs(y - self.cy) <= self.height / 2
        )

    def draw(self, selected=False):
        fill = (60, 90, 160, 235) if selected else (25, 30, 55, 235)
        edge = arcade.color.CYAN if selected else (120, 130, 170)

        draw_box(
            self.cx,
            self.cy,
            self.width,
            self.height,
            fill,
            edge,
            2,
        )

        self.text.draw()

class Bullet:
    """A player bullet."""

    sprite_key = "bullet_player"

    def __init__(self, x, y, angle, sprite_key=None):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = BULLET_SPEED
        self.radius = BULLET_RADIUS
        self.damage = BULLET_DAMAGE
        if sprite_key:
            self.sprite_key = sprite_key

    def update(self):
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed

    def draw(self):
        ART[self.sprite_key].draw(self.x, self.y, self.angle)

    def is_off_screen(self):
        return not is_on_screen(self.x, self.y)


class EnemyBullet(Bullet):
    """Bullet fired by a red shooting enemy."""

    sprite_key = "bullet_enemy"

    def __init__(self, x, y, angle):
        super().__init__(x, y, angle)
        self.speed = ENEMY_BULLET_SPEED
        self.radius = ENEMY_BULLET_RADIUS
        self.damage = ENEMY_BULLET_DAMAGE


class BossBullet(EnemyBullet):
    """Big, slow, heavy-hitting bullet fired by the boss."""

    sprite_key = "bullet_boss"

    def __init__(self, x, y, angle):
        super().__init__(x, y, angle)
        self.speed = BOSS_BULLET_SPEED
        self.radius = BOSS_BULLET_RADIUS
        self.damage = BOSS_BULLET_DAMAGE


class PowerUp:
    """A pickup dropped by enemies: health, shield or fire."""

    KINDS = ["health", "shield", "fire"]
    GLOW = {
        "health": (255, 60, 60, 60),
        "shield": (200, 200, 220, 60),
        "fire": (0, 200, 255, 60),
    }

    def __init__(self, x, y, kind=None):
        self.x = x
        self.y = y
        self.kind = kind or random.choice(self.KINDS)
        self.radius = POWERUP_RADIUS
        self.life = POWERUP_LIFETIME

    def update(self, delta_time):
        self.life -= delta_time

    def draw(self):
        # blink during the last 2 seconds so the player knows it's about to vanish
        if self.life < 2 and int(self.life * 6) % 2 == 0:
            return

        # soft colored glow behind the icon so it is easy to spot
        arcade.draw_circle_filled(
            self.x, self.y, self.radius + 8, self.GLOW[self.kind]
        )
        ART["pu_" + self.kind].draw(self.x, self.y)


class Enemy:
    """Blue enemy that chases the player."""

    sprite_key = "enemy_blue"
    dies_on_contact = True              # crashes into the player and disappears
    contact_damage = ENEMY_DAMAGE
    score_value = 10
    drop_chance = POWERUP_DROP_CHANCE
    bar_width = 30

    def __init__(self):
        side = random.choice(["top", "bottom", "left", "right"])

        if side == "top":
            self.x = random.uniform(0, SCREEN_WIDTH)
            self.y = SCREEN_HEIGHT + 20
        elif side == "bottom":
            self.x = random.uniform(0, SCREEN_WIDTH)
            self.y = -20
        elif side == "left":
            self.x = -20
            self.y = random.uniform(0, SCREEN_HEIGHT)
        else:
            self.x = SCREEN_WIDTH + 20
            self.y = random.uniform(0, SCREEN_HEIGHT)

        self.speed = random.uniform(ENEMY_SPEED_MIN, ENEMY_SPEED_MAX)
        self.angle = 0
        self.radius = ENEMY_RADIUS
        self.max_health = random.randint(ENEMY_MIN_HEALTH, ENEMY_MAX_HEALTH)
        self.health = self.max_health
        self.contact_timer = 0

    def update(self, player_x, player_y, delta_time, enemy_bullets):
        # Move directly toward the player.
        self.angle = math.atan2(player_y - self.y, player_x - self.x)
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed

    def draw(self):
        ART[self.sprite_key].draw(self.x, self.y, self.angle)
        draw_health_bar(self.x, self.y + self.radius + 12, self.bar_width,
                        self.health, self.max_health)


class ShootEnemy(Enemy):
    """Red enemy that chases the player and shoots at them."""

    sprite_key = "enemy_red"
    bullet_class = EnemyBullet

    def __init__(self):
        super().__init__()
        self.speed = random.uniform(
            SHOOT_ENEMY_MIN_SPEED, SHOOT_ENEMY_MAX_SPEED
        )
        self.max_health = random.randint(
            SHOOT_ENEMY_MIN_HEALTH, SHOOT_ENEMY_MAX_HEALTH
        )
        self.health = self.max_health
        self.preferred_distance = SHOOT_ENEMY_PREFERRED_DISTANCE
        self.shoot_cooldown = ENEMY_SHOOT_COOLDOWN
        self.shoot_timer = random.uniform(0.5, ENEMY_SHOOT_COOLDOWN)

    def update(self, player_x, player_y, delta_time, enemy_bullets):
        # Face the player so the enemy always aims at the correct position.
        dx = player_x - self.x
        dy = player_y - self.y
        distance = max(1, math.hypot(dx, dy))
        self.angle = math.atan2(dy, dx)

        # Keep some distance from the player instead of crashing into them.
        if distance > self.preferred_distance + SHOOT_ENEMY_DISTANCE_TOLERANCE:
            self.x += math.cos(self.angle) * self.speed
            self.y += math.sin(self.angle) * self.speed
        elif distance < self.preferred_distance - SHOOT_ENEMY_DISTANCE_TOLERANCE:
            self.x -= math.cos(self.angle) * self.speed
            self.y -= math.sin(self.angle) * self.speed

        # Count down and fire. Don't waste shots while still outside the screen.
        self.shoot_timer -= delta_time
        if self.shoot_timer <= 0 and is_on_screen(self.x, self.y):
            enemy_bullets.append(self.make_bullet())
            self.shoot_timer = self.shoot_cooldown

        # Keep enemies from getting lost far outside the visible window.
        self.x = max(-self.radius, min(SCREEN_WIDTH + self.radius, self.x))
        self.y = max(-self.radius, min(SCREEN_HEIGHT + self.radius, self.y))

    def make_bullet(self):
        bullet = self.bullet_class(self.x, self.y, self.angle)
        # start the bullet just outside the enemy so it doesn't overlap it
        offset = self.radius + bullet.radius + 2
        bullet.x += math.cos(self.angle) * offset
        bullet.y += math.sin(self.angle) * offset
        return bullet


class Boss(ShootEnemy):
    """Big purple boss: lots of health, one heavy shot every 4 seconds."""

    sprite_key = "boss"
    bullet_class = BossBullet
    dies_on_contact = False             # touching it hurts, but it stays alive
    contact_damage = BOSS_CONTACT_DAMAGE
    score_value = BOSS_SCORE
    drop_chance = 1.0                   # a boss always drops a power-up
    bar_width = 100

    def __init__(self):
        super().__init__()
        self.radius = BOSS_RADIUS
        self.speed = BOSS_SPEED
        self.max_health = BOSS_HEALTH
        self.health = self.max_health
        self.preferred_distance = BOSS_PREFERRED_DISTANCE
        self.shoot_cooldown = BOSS_SHOOT_COOLDOWN
        self.shoot_timer = BOSS_SHOOT_COOLDOWN


class GameWindow(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(arcade.color.BLACK)

        # Load every picture once (needs the window to exist first).
        load_art()
        background_path = ASSET_DIR / "background.jpg"
        if not background_path.is_file():
            raise FileNotFoundError(
                f"Required background image is missing: {background_path}"
            )
        try:
            with Image.open(background_path) as background_image:
                self.background = make_texture(background_image.convert("RGBA"))
        except Exception as error:
            raise RuntimeError(
                f"Could not load background image {background_path}: {error}"
            ) from error

        load_sounds()
        self.music_player = None
        self.music_volume = MUSIC_START_VOLUME

        self.keys_pressed = set()
        self.mouse_x = SCREEN_WIDTH // 2
        self.mouse_y = SCREEN_HEIGHT // 2
        self.mouse_down = False

        # Pause menu / settings screen.
        self.state = STATE_PLAY
        self.menu_index = 0
        self.dragging_volume = False
        cx = SCREEN_WIDTH / 2
        self.menu_button = Button(
            "MENU (ESC)", SCREEN_WIDTH - 75, SCREEN_HEIGHT - 25,
            width=130, height=30, font_size=12
        )
        self.menu_buttons = [
            Button("RESUME", cx, 330),
            Button("SETTING", cx, 262),
            Button("EXIT", cx, 194),
        ]
        self.menu_title = arcade.Text(
            "PAUSED", cx, 420, arcade.color.WHITE, 30,
            anchor_x="center", anchor_y="center"
        )
        self.settings_title = arcade.Text(
            "SETTING", cx, 420, arcade.color.WHITE, 30,
            anchor_x="center", anchor_y="center"
        )
        self.volume_label = arcade.Text(
            "BACKGROUND SOUND", cx, 350, arcade.color.LIGHT_GRAY, 16,
            anchor_x="center", anchor_y="center"
        )
        self.volume_percent = arcade.Text(
            "", cx, 262, arcade.color.CYAN, 18,
            anchor_x="center", anchor_y="center"
        )
        self.volume_hint = arcade.Text(
            "Arrow keys or mouse also work", cx, 130, (150, 155, 180), 11,
            anchor_x="center", anchor_y="center"
        )
        # Volume bar sits between the "-" and "+" buttons.
        self.bar_cx = cx
        self.bar_cy = 305
        self.bar_width = 220
        self.bar_height = 16
        self.volume_down_button = Button("-", cx - 160, 305, 56, 48, 24)
        self.volume_up_button = Button("+", cx + 160, 305, 56, 48, 24)
        self.back_button = Button("BACK", cx, 200)
        self.settings_buttons = [
            self.volume_down_button, self.volume_up_button, self.back_button
        ]

        # Reusable text objects for the HUD.
        self.score_text = arcade.Text(
            "", 10, SCREEN_HEIGHT - 30, arcade.color.WHITE, 16
        )
        self.health_text = arcade.Text(
            "", 10, SCREEN_HEIGHT - 55, arcade.color.WHITE, 16
        )
        self.enemy_text = arcade.Text(
            "", 10, SCREEN_HEIGHT - 80, arcade.color.WHITE, 12
        )
        self.buff_text = arcade.Text(
            "", 10, SCREEN_HEIGHT - 105, arcade.color.CYAN, 14
        )
        self.boss_text = arcade.Text(
            "BOSS INCOMING!", SCREEN_WIDTH / 2, SCREEN_HEIGHT - 60,
            arcade.color.MAGENTA, 28, anchor_x="center"
        )
        self.game_over_text = arcade.Text(
            "GAME OVER", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 20,
            arcade.color.RED, 40, anchor_x="center"
        )
        self.restart_text = arcade.Text(
            "Press R to restart", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 30,
            arcade.color.WHITE, 18, anchor_x="center"
        )

        self.reset()

    def reset(self):
        self.player_x = SCREEN_WIDTH // 2
        self.player_y = SCREEN_HEIGHT // 2
        self.player_angle = 0
        self.player_radius = PLAYER_RADIUS
        self.player_health = PLAYER_MAX_HEALTH

        self.bullets = []
        self.enemy_bullets = []
        self.enemies = []
        self.powerups = []

        self.shoot_cooldown = 0
        self.enemy_spawn_timer = ENEMY_SPAWN_RATE
        self.shield_timer = 0
        self.fire_timer = 0

        self.score = 0
        self.next_boss_score = BOSS_SPAWN_EVERY
        self.boss_message_timer = 0
        self.game_over = False

        self.state = STATE_PLAY
        self.mouse_down = False
        self.dragging_volume = False
        self.keys_pressed.clear()
        self.start_music()

    # ---------------------------------------------------------------- music
    def start_music(self):
        """(Re)start the looping background music at the current volume."""
        self.stop_music()
        sound = SOUNDS.get("music")
        if sound is None:
            return
        try:
            try:
                self.music_player = arcade.play_sound(
                    sound, volume=self.music_volume,loop=True       # arcade 3.x
                )
            except TypeError:
                self.music_player = arcade.play_sound(
                    sound, volume=self.music_volume,looping=True    # arcade 2.6
                )
        except Exception as error:
            print(f"[sound] could not start music: {error}")
            self.music_player = None

    def stop_music(self):
        if self.music_player is not None:
            try:
                arcade.stop_sound(self.music_player)
            except Exception:
                pass
            self.music_player = None

    def set_music_volume(self, value):
        """Change ONLY the background music volume (sound effects stay fixed)."""
        self.music_volume = round(max(0.0, min(1.0, value)), 2)
        if self.music_player is not None:
            try:
                self.music_player.volume = self.music_volume
            except Exception:
                pass

    # ----------------------------------------------------------------- menu
    def open_menu(self):
        if self.game_over:
            return
        self.state = STATE_MENU
        self.menu_index = 0
        self.mouse_down = False
        self.dragging_volume = False

    def resume_game(self):
        self.state = STATE_PLAY
        self.dragging_volume = False

    def open_settings(self):
        self.state = STATE_SETTINGS
        self.menu_index = 2             # start on BACK
        self.dragging_volume = False

    def exit_game(self):
        self.stop_music()
        self.close()

    def current_buttons(self):
        if self.state == STATE_MENU:
            return self.menu_buttons
        return self.settings_buttons

    def activate_button(self, button):
        if self.state == STATE_MENU:
            if button is self.menu_buttons[0]:
                self.resume_game()
            elif button is self.menu_buttons[1]:
                self.open_settings()
            else:
                self.exit_game()
        else:
            if button is self.volume_down_button:
                self.set_music_volume(self.music_volume - MUSIC_VOLUME_STEP)
            elif button is self.volume_up_button:
                self.set_music_volume(self.music_volume + MUSIC_VOLUME_STEP)
            else:
                self.state = STATE_MENU
                self.menu_index = 1

    def volume_from_mouse(self, x):
        left = self.bar_cx - self.bar_width / 2
        self.set_music_volume((x - left) / self.bar_width)

    def over_volume_bar(self, x, y):
        return (abs(x - self.bar_cx) <= self.bar_width / 2 + 6
                and abs(y - self.bar_cy) <= self.bar_height / 2 + 8)

    def draw_menu(self):
        # darken the game behind the menu
        draw_box(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2,
                 SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0, 170))
        draw_box(SCREEN_WIDTH / 2, 310, 420, 340, (10, 14, 30, 240),
                 arcade.color.CYAN, 3)

        if self.state == STATE_MENU:
            self.menu_title.draw()
            for i, button in enumerate(self.menu_buttons):
                button.draw(i == self.menu_index)
            return

        # settings screen
        self.settings_title.draw()
        self.volume_label.draw()

        left = self.bar_cx - self.bar_width / 2
        draw_box(self.bar_cx, self.bar_cy, self.bar_width, self.bar_height,
                 (40, 45, 70), (120, 130, 170), 2)
        filled = self.bar_width * self.music_volume
        if filled > 0:
            draw_box(left + filled / 2, self.bar_cy, filled,
                     self.bar_height - 4, arcade.color.CYAN)

        set_text(self.volume_percent, f"{round(self.music_volume * 100)}%")
        self.volume_percent.draw()
        for i, button in enumerate(self.settings_buttons):
            button.draw(i == self.menu_index)
        self.volume_hint.draw()

    def on_draw(self):
        self.clear()

        # Space background.
        draw_texture(self.background, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)

        # Draw the player ship.
        r = self.player_radius
        ART["player"].draw(self.player_x, self.player_y, self.player_angle)

        # Shield ring (blinks when it is about to run out).
        if self.shield_timer > 0:
            if self.shield_timer > 1.5 or int(self.shield_timer * 8) % 2 == 0:
                arcade.draw_circle_outline(
                    self.player_x, self.player_y, r + 10,
                    arcade.color.CYAN, 3
                )

        draw_health_bar(
            self.player_x, self.player_y + r + 15, 40,
            self.player_health, PLAYER_MAX_HEALTH
        )

        for powerup in self.powerups:
            powerup.draw()
        for bullet in self.bullets:
            bullet.draw()
        for bullet in self.enemy_bullets:
            bullet.draw()
        for enemy in self.enemies:
            enemy.draw()

        set_text(self.score_text, f"Score: {self.score}")
        set_text(
            self.health_text,
            f"Health: {int(self.player_health)}/{PLAYER_MAX_HEALTH}"
        )
        set_text(self.enemy_text, f"Enemies: {len(self.enemies)}")

        buffs = []
        if self.shield_timer > 0:
            buffs.append(f"SHIELD {self.shield_timer:.1f}s")
        if self.fire_timer > 0:
            buffs.append(f"FIRE {self.fire_timer:.1f}s")
        set_text(self.buff_text, "   ".join(buffs))

        self.score_text.draw()
        self.health_text.draw()
        self.enemy_text.draw()
        self.buff_text.draw()

        if self.boss_message_timer > 0:
            self.boss_text.draw()

        if self.game_over:
            self.game_over_text.draw()
            self.restart_text.draw()
        else:
            self.menu_button.draw(self.menu_button.contains(self.mouse_x, self.mouse_y)
                                  and self.state == STATE_PLAY)

        if self.state != STATE_PLAY:
            self.draw_menu()

    @staticmethod
    def check_collision(x1, y1, r1, x2, y2, r2):
        return math.hypot(x2 - x1, y2 - y1) <= r1 + r2

    def damage_player(self, amount):
        # an active shield blocks everything
        if self.shield_timer > 0:
            return
        self.player_health -= amount

    def boss_alive(self):
        return any(isinstance(enemy, Boss) for enemy in self.enemies)

    def apply_powerup(self, powerup):
        play_sfx("power_buff")
        if powerup.kind == "health":
            self.player_health = min(
                PLAYER_MAX_HEALTH, self.player_health + HEALTH_PICKUP_AMOUNT
            )
        elif powerup.kind == "shield":
            self.shield_timer = SHIELD_DURATION
        else:
            self.fire_timer = FIRE_DURATION

    def on_update(self, delta_time):
        # frozen while the pause menu / settings screen is open
        if self.game_over or self.state != STATE_PLAY:
            return

        self.shoot_cooldown -= delta_time
        self.enemy_spawn_timer -= delta_time
        self.boss_message_timer -= delta_time
        self.shield_timer = max(0, self.shield_timer - delta_time)
        self.fire_timer = max(0, self.fire_timer - delta_time)

        if self.mouse_down:
            self.shoot()

        # Spawn blue and red enemies.
        if self.enemy_spawn_timer <= 0:
            if random.random() < SHOOT_ENEMY_CHANCE:
                self.enemies.append(ShootEnemy())
            else:
                self.enemies.append(Enemy())
            self.enemy_spawn_timer = ENEMY_SPAWN_RATE

        # Spawn the boss when the score reaches the next boss score.
        if self.score >= self.next_boss_score and not self.boss_alive():
            self.enemies.append(Boss())
            # Keep fixed score milestones (200, 400, 600...), rather than
            # resetting relative to the score at the moment the boss spawns.
            self.next_boss_score += BOSS_SPAWN_EVERY
            self.boss_message_timer = 3.0

        # WASD movement.
        if arcade.key.W in self.keys_pressed:
            self.player_y += PLAYER_SPEED
        if arcade.key.S in self.keys_pressed:
            self.player_y -= PLAYER_SPEED
        if arcade.key.A in self.keys_pressed:
            self.player_x -= PLAYER_SPEED
        if arcade.key.D in self.keys_pressed:
            self.player_x += PLAYER_SPEED

        # Keep the player inside the window.
        self.player_x = max(
            self.player_radius,
            min(SCREEN_WIDTH - self.player_radius, self.player_x)
        )
        self.player_y = max(
            self.player_radius,
            min(SCREEN_HEIGHT - self.player_radius, self.player_y)
        )

        # Aim toward the mouse.
        self.player_angle = math.atan2(
            self.mouse_y - self.player_y,
            self.mouse_x - self.player_x
        )

        # Power-ups: count down their life and let the player pick them up.
        for powerup in self.powerups[:]:
            powerup.update(delta_time)

            if powerup.life <= 0:
                self.powerups.remove(powerup)
            elif self.check_collision(
                powerup.x, powerup.y, powerup.radius,
                self.player_x, self.player_y, self.player_radius
            ):
                self.apply_powerup(powerup)
                self.powerups.remove(powerup)

        # Update player bullets and damage enemies.
        for bullet in self.bullets[:]:
            bullet.update()

            if bullet.is_off_screen():
                self.bullets.remove(bullet)
                continue

            for enemy in self.enemies:
                if enemy.health <= 0:
                    continue

                if self.check_collision(
                    bullet.x, bullet.y, bullet.radius,
                    enemy.x, enemy.y, enemy.radius
                ):
                    enemy.health -= bullet.damage
                    self.bullets.remove(bullet)
                    break

        # Update bullets fired by red enemies and the boss.
        for bullet in self.enemy_bullets[:]:
            bullet.update()

            if bullet.is_off_screen():
                self.enemy_bullets.remove(bullet)
                continue

            if self.check_collision(
                bullet.x, bullet.y, bullet.radius,
                self.player_x, self.player_y, self.player_radius
            ):
                self.damage_player(bullet.damage)
                self.enemy_bullets.remove(bullet)

        # Update enemies, remove defeated enemies, and handle collisions.
        for enemy in self.enemies[:]:
            shots_before = len(self.enemy_bullets)
            enemy.update(
                self.player_x, self.player_y,
                delta_time, self.enemy_bullets
            )
            if len(self.enemy_bullets) > shots_before:
                play_sfx("boss_missile" if isinstance(enemy, Boss)
                         else "enemy_shoot")
            enemy.contact_timer -= delta_time

            if enemy.health <= 0:
                self.enemies.remove(enemy)
                play_sfx("boss_defeat" if isinstance(enemy, Boss)
                         else "enemy_dead")
                self.score += enemy.score_value
                if random.random() < enemy.drop_chance:
                    self.powerups.append(PowerUp(enemy.x, enemy.y))
                continue

            if self.check_collision(
                enemy.x, enemy.y, enemy.radius,
                self.player_x, self.player_y, self.player_radius
            ):
                if enemy.dies_on_contact:
                    self.damage_player(enemy.contact_damage)
                    self.enemies.remove(enemy)
                elif enemy.contact_timer <= 0:
                    # the boss survives, so it can only hit once per second
                    self.damage_player(enemy.contact_damage)
                    enemy.contact_timer = BOSS_CONTACT_COOLDOWN

        if self.player_health <= 0:
            self.player_health = 0
            self.game_over = True
            self.stop_music()
            play_sfx("game_over")

    def shoot(self):
        if self.shoot_cooldown > 0 or self.game_over:
            return

        tip = self.player_radius * 1.5
        bullet_x = self.player_x + math.cos(self.player_angle) * tip
        bullet_y = self.player_y + math.sin(self.player_angle) * tip

        if self.fire_timer > 0:
            # fire power-up: red-orange bullets, much faster shooting
            bullet = Bullet(bullet_x, bullet_y, self.player_angle,
                            "bullet_fire")
            self.shoot_cooldown = FIRE_SHOOT_COOLDOWN
        else:
            bullet = Bullet(bullet_x, bullet_y, self.player_angle)
            self.shoot_cooldown = PLAYER_SHOOT_COOLDOWN

        self.bullets.append(bullet)
        play_sfx("player_shoot")

    def on_key_press(self, key, modifiers):
        # --- pause menu / settings keys ---
        if self.state != STATE_PLAY:
            buttons = self.current_buttons()
            if key == arcade.key.ESCAPE:
                if self.state == STATE_SETTINGS:
                    self.state = STATE_MENU
                    self.menu_index = 1
                else:
                    self.resume_game()
            elif self.state == STATE_SETTINGS and key in (
                    arcade.key.UP, arcade.key.RIGHT):
                self.set_music_volume(self.music_volume + MUSIC_VOLUME_STEP)
            elif self.state == STATE_SETTINGS and key in (
                    arcade.key.DOWN, arcade.key.LEFT):
                self.set_music_volume(self.music_volume - MUSIC_VOLUME_STEP)
            elif key == arcade.key.UP:
                self.menu_index = (self.menu_index - 1) % len(buttons)
            elif key == arcade.key.DOWN:
                self.menu_index = (self.menu_index + 1) % len(buttons)
            elif key in (arcade.key.ENTER, arcade.key.RETURN, arcade.key.SPACE):
                self.activate_button(buttons[self.menu_index])
            return

        if key == arcade.key.ESCAPE:
            self.open_menu()
            return

        self.keys_pressed.add(key)
        if key == arcade.key.R and self.game_over:
            self.reset()

    def on_key_release(self, key, modifiers):
        self.keys_pressed.discard(key)

    def select_button_under_mouse(self, x, y):
        for i, button in enumerate(self.current_buttons()):
            if button.contains(x, y):
                self.menu_index = i

    def on_mouse_motion(self, x, y, dx, dy):
        self.mouse_x = x
        self.mouse_y = y
        if self.state != STATE_PLAY:
            self.select_button_under_mouse(x, y)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.mouse_x = x
        self.mouse_y = y
        if self.state == STATE_SETTINGS and self.dragging_volume:
            self.volume_from_mouse(x)

    def on_mouse_press(self, x, y, button, modifiers):
        self.mouse_x = x
        self.mouse_y = y
        if button != arcade.MOUSE_BUTTON_LEFT:
            return

        # clicks on the menu never shoot
        if self.state != STATE_PLAY:
            if self.state == STATE_SETTINGS and self.over_volume_bar(x, y):
                self.dragging_volume = True
                self.volume_from_mouse(x)
                return
            for button_obj in self.current_buttons():
                if button_obj.contains(x, y):
                    self.activate_button(button_obj)
                    return
            return

        if not self.game_over and self.menu_button.contains(x, y):
            self.open_menu()
            return

        self.mouse_down = True
        self.shoot()

    def on_mouse_release(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.mouse_down = False
            self.dragging_volume = False

    def on_close(self):
        self.stop_music()
        super().on_close()


def main():
    print("Running this file:", __file__)
    GameWindow()
    arcade.run()


if __name__ == "__main__":
    main()
