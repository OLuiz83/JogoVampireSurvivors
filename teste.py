import pygame
import random

# ---------------------------------------------------------------
# JOGO TESTE: o menor "Vampire Survivors" possível.
# Controles: WASD anda | 1, 2, 3 escolhe o upgrade | R recomeça
# Precisa da pasta "assets" ao lado deste arquivo.
# ---------------------------------------------------------------


# ---------------------------------------------------------------
# DADOS DO JOGO
# Para mudar o equilíbrio do jogo, basta mexer nestas tabelas.
# ---------------------------------------------------------------

# tipos de inimigo: vida, velocidade (normal e maligno), dano por segundo e xp que dá ao morrer
ENEMY_TYPES = {
    "banano": {"sprite": "banano", "angrySprite": "banano2", "hp": 2, "speed": 50, "angrySpeed": 150, "damage": 8, "xp": 1},
    "ovito": {"sprite": "ovito", "angrySprite": "ovito2", "hp": 3, "speed": 70, "angrySpeed": 170, "damage": 8, "xp": 2},
    "tomato": {"sprite": "tomato", "angrySprite": "tomato2", "hp": 6, "speed": 40, "angrySpeed": 110, "damage": 14, "xp": 4},
}

# fases: cada uma dura STAGE_TIME segundos e muda os inimigos, a frequência deles e a cor do cenário.
# Sobreviver a todas as fases = vitória.
STAGE_TIME = 30
STAGES = [
    {"enemies": ["banano"], "spawnDelay": 1.5, "tint": None},
    {"enemies": ["banano", "ovito"], "spawnDelay": 1.2, "tint": ("orange", 40)},
    {"enemies": ["banano", "ovito", "tomato"], "spawnDelay": 1.0, "tint": ("purple", 50)},
    {"enemies": ["ovito", "tomato"], "spawnDelay": 0.8, "tint": ("red", 50)},
    {"enemies": ["banano", "ovito", "tomato"], "spawnDelay": 0.6, "tint": ("black", 90)},
]

# armas: "delay" = segundos entre ataques. Cada nível da arma aumenta a quantidade de projéteis.
WEAPONS = {
    "colher": {"name": "Colher", "info": "mira no inimigo", "delay": 0.6},
    "faca": {"name": "Faca", "info": "atravessa", "delay": 0.9},
    "garfo": {"name": "Garfo", "info": "atira em volta", "delay": 1.6},
    "frigideira": {"name": "Frigideira", "info": "gira em volta", "delay": 0},
}
MAX_WEAPON_LEVEL = 4


# classes pequenas: cada inimigo e cada tiro guardam os seus próprios dados
class Enemy:
    def __init__(self, pos, kind, extraHp=0):
        self.pos = pygame.Vector2(pos)
        self.data = ENEMY_TYPES[kind]
        self.hp = self.data["hp"] + extraHp
        self.angry = False       # False = inofensivo, True = forma maligna
        self.panCooldown = 0     # tempo até a frigideira poder bater nele de novo


class Shot:
    def __init__(self, pos, direction, image, speed, timeLeft, pierce=False):
        self.pos = pygame.Vector2(pos)
        self.direction = direction      # vetor de tamanho 1 apontando para onde o tiro vai
        self.image = image              # já vem girada para apontar na direção do tiro
        self.speed = speed              # pixels por segundo
        self.timeLeft = timeLeft        # segundos até o tiro sumir
        self.pierce = pierce            # True = atravessa os inimigos em vez de sumir
        self.hit = []                   # inimigos que um tiro que atravessa já acertou


class Game:
    def __init__(self):
        pygame.init()

        self.screenWidth, self.screenHeight = 800, 800
        self.tileSide = 40
        self.screen = pygame.display.set_mode((self.screenWidth, self.screenHeight))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 40)
        self.dt = 0
        self.camera = pygame.Vector2(0, 0)
        self.loadSprites()
        self.newGame()

    def loadImage(self, name):
        image = pygame.image.load(f"assets/{name}.png").convert_alpha()
        return pygame.transform.scale(image, (self.tileSide, self.tileSide))

    def loadSprites(self):
        self.grass = self.loadImage("grass")
        self.player = self.loadImage("player_front_1")

        # inimigos e armas ficam num dicionário: self.sprites["banano"], self.sprites["faca"]...
        self.sprites = {}
        for name in ["banano", "banano2", "ovito", "ovito2", "tomato", "tomato2", "colher", "faca", "garfo"]:
            self.sprites[name] = self.loadImage(name)

        # a imagem da frigideira tem 64x32; a panela está no meio, então pegamos só esse pedaço
        pan = pygame.image.load("assets/fryingpan1.png").convert_alpha().subsurface((16, 0, 32, 32))
        self.sprites["frigideira"] = pygame.transform.scale(pan, (self.tileSide, self.tileSide))

        # retângulo usado para escurecer a tela e para dar cor às fases
        self.overlay = pygame.Surface((self.screenWidth, self.screenHeight))

    def newGame(self):
        # tudo que muda durante a partida fica aqui.
        # chamar newGame() de novo = recomeçar do zero.

        # atributos do jogador
        self.playerPos = pygame.Vector2(0, 0)    # posição no MUNDO (não na tela)
        self.playerHp = 100
        self.playerMaxHp = 100
        self.playerSpeed = 250                   # pixels por segundo
        self.playerDamage = 1                    # força (vale para todas as armas)
        self.attackDelay = 1                     # multiplicador do tempo entre ataques (menor = mais rápido)
        self.facing = pygame.Vector2(1, 0)       # para onde o jogador está virado (a faca usa isso)

        # armas: nome -> nível. Começa só com a colher.
        self.weapons = {"colher": 1}
        self.attackTimers = {name: 0 for name in WEAPONS}
        self.panAngle = 0                        # ângulo atual das frigideiras girando

        # experiência
        self.xp = 0
        self.xpToLevel = 5
        self.level = 1

        # fases
        self.time = 0                            # segundos sobrevividos
        self.stage = 0                           # posição na lista STAGES (0 = fase 1)
        self.bannerTimer = 2                     # tempo mostrando "Fase X" na tela

        # listas
        self.enemies = []
        self.shots = []
        self.spawnTimer = 0
        self.upgradeOptions = []

        # estados do jogo
        self.gameOver = False
        self.won = False
        self.choosingUpgrade = False

    # ---------------------------------------------------------- loop
    def Run(self):
        self.running = True
        while self.running:
            self.handleEvents()

            # o jogo só anda se não estiver congelado
            if not self.gameOver and not self.choosingUpgrade:
                self.update()

            self.draw()
            pygame.display.flip()

            # limita o dt: se a janela travar (ex: arrastar), o jogo não "pula" no tempo
            self.dt = min(self.clock.tick(75) / 1000, 0.05)

        pygame.quit()

    def handleEvents(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if event.type != pygame.KEYDOWN:
                continue

            # teclas 1, 2 e 3 são seguidas, então K_1 -> opção 1, K_2 -> opção 2...
            if self.choosingUpgrade and event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self.chooseUpgrade(event.key - pygame.K_1 + 1)

            if self.gameOver and event.key == pygame.K_r:
                self.newGame()

    # ------------------------------------------------------- atualizar
    def update(self):
        self.updateStage()
        self.movePlayer()
        self.spawnEnemies()
        self.moveEnemies()
        self.attack()
        self.moveShots()
        self.movePans()
        self.removeDeadEnemies()

        if self.playerHp <= 0:
            self.gameOver = True
            self.choosingUpgrade = False
        elif self.time >= STAGE_TIME * len(STAGES):
            self.gameOver = True
            self.won = True

    def updateStage(self):
        self.time += self.dt
        self.bannerTimer -= self.dt

        # fase atual = tempo / duração da fase (sem passar da última)
        stage = min(int(self.time // STAGE_TIME), len(STAGES) - 1)
        if stage != self.stage:
            self.stage = stage
            self.bannerTimer = 2

    def movePlayer(self):
        keys = pygame.key.get_pressed()
        direction = pygame.Vector2(0, 0)
        if keys[pygame.K_w]:
            direction.y -= 1
        if keys[pygame.K_s]:
            direction.y += 1
        if keys[pygame.K_a]:
            direction.x -= 1
        if keys[pygame.K_d]:
            direction.x += 1

        # na diagonal o vetor tem tamanho maior que 1, então deixamos ele com tamanho 1
        if direction.length() > 0:
            direction = direction.normalize()
            self.facing = direction

        # velocidade (pixels por segundo) * dt (segundos) = pixels neste frame
        self.playerPos += direction * self.playerSpeed * self.dt

    def spawnEnemies(self):
        self.spawnTimer -= self.dt
        if self.spawnTimer <= 0:
            stage = STAGES[self.stage]
            self.spawnTimer = stage["spawnDelay"]

            # sorteia um ângulo e coloca o inimigo a 600 pixels do jogador
            # (a tela só vai até uns 566 do centro, então ele nasce fora da vista)
            offset = pygame.Vector2(600, 0).rotate(random.randint(0, 359))
            kind = random.choice(stage["enemies"])

            # a cada 2 fases os inimigos ganham +1 de vida
            self.enemies.append(Enemy(self.playerPos + offset, kind, self.stage // 2))

    def moveEnemies(self):
        for enemy in self.enemies:
            toPlayer = self.playerPos - enemy.pos
            distance = toPlayer.length()

            # chegou perto? fica maligno (e continua maligno)
            if distance < 250:
                enemy.angry = True

            if enemy.angry:
                speed = enemy.data["angrySpeed"]
            else:
                speed = enemy.data["speed"]

            if distance > 0:
                enemy.pos += toPlayer.normalize() * speed * self.dt

            # encostou no jogador: tira vida
            if distance < 50:
                self.playerHp -= enemy.data["damage"] * self.dt

    def nearestEnemy(self):
        # o inimigo com a menor distância até o jogador (None se não tem nenhum)
        return min(self.enemies, key=lambda enemy: enemy.pos.distance_to(self.playerPos), default=None)

    def attack(self):
        for name, level in self.weapons.items():
            if name == "frigideira":
                continue    # a frigideira não atira, ela gira (ver movePans)

            self.attackTimers[name] = max(self.attackTimers[name] - self.dt, 0)
            if self.attackTimers[name] > 0:
                continue

            if self.shoot(name, level):
                self.attackTimers[name] = WEAPONS[name]["delay"] * self.attackDelay

    def shoot(self, name, level):
        # dispara a arma e devolve True se atirou (só atira se houver inimigos)
        target = self.nearestEnemy()
        if target is None:
            return False

        if name == "colher":
            # vai na direção do inimigo mais perto; cada nível abre mais uma colher em leque
            direction = target.pos - self.playerPos
            if direction.length() == 0:
                return False
            for angle in self.fanAngles(level, 12):
                self.addShot("colher", direction.normalize().rotate(angle), 600, 1.5)

        elif name == "faca":
            # vai para onde o jogador está virado e atravessa os inimigos
            for angle in self.fanAngles(level, 10):
                self.addShot("faca", self.facing.rotate(angle), 800, 1.0, pierce=True)

        elif name == "garfo":
            # explosão de garfos para todos os lados: 4 no nível 1, 6 no nível 2...
            count = 2 + 2 * level
            for i in range(count):
                self.addShot("garfo", pygame.Vector2(1, 0).rotate(360 / count * i), 350, 0.9)

        return True

    def fanAngles(self, count, step):
        # ângulos de um leque centrado: (3, 10) -> [-10, 0, 10]
        return [(i - (count - 1) / 2) * step for i in range(count)]

    def addShot(self, sprite, direction, speed, timeLeft, pierce=False):
        image = self.rotated(sprite, direction)
        self.shots.append(Shot(self.playerPos, direction, image, speed, timeLeft, pierce))

    def rotated(self, sprite, direction):
        # os desenhos apontam para CIMA; giramos para apontar para "direction".
        # (o pygame gira ao contrário do vetor, por isso o sinal de menos)
        angle = -pygame.Vector2(0, -1).angle_to(direction)
        return pygame.transform.rotate(self.sprites[sprite], angle)

    def moveShots(self):
        for shot in self.shots:
            shot.pos += shot.direction * shot.speed * self.dt
            shot.timeLeft -= self.dt

            # acertou algum inimigo?
            for enemy in self.enemies:
                if enemy.hp <= 0 or enemy in shot.hit:
                    continue
                if shot.pos.distance_to(enemy.pos) < 40:
                    enemy.hp -= self.playerDamage
                    if shot.pierce:
                        shot.hit.append(enemy)  # atravessa, mas não bate duas vezes no mesmo
                    else:
                        shot.timeLeft = 0       # o tiro some
                        break

        # fica só com os tiros que ainda valem
        self.shots = [shot for shot in self.shots if shot.timeLeft > 0]

    def panPositions(self):
        # posição (e direção para fora) de cada frigideira girando em volta do jogador.
        # o nível da arma = quantidade de frigideiras, espalhadas em círculo.
        level = self.weapons.get("frigideira", 0)
        result = []
        for i in range(level):
            direction = pygame.Vector2(1, 0).rotate(self.panAngle + 360 / level * i)
            result.append((self.playerPos + direction * 100, direction))
        return result

    def movePans(self):
        if "frigideira" not in self.weapons:
            return

        self.panAngle += 180 * self.dt      # graus por segundo
        pans = self.panPositions()

        for enemy in self.enemies:
            enemy.panCooldown -= self.dt
            if enemy.panCooldown > 0 or enemy.hp <= 0:
                continue

            for panPos, direction in pans:
                if panPos.distance_to(enemy.pos) < 45:
                    enemy.hp -= self.playerDamage
                    enemy.panCooldown = 0.5     # só bate de novo depois de meio segundo
                    break

    def removeDeadEnemies(self):
        aliveEnemies = []
        for enemy in self.enemies:
            if enemy.hp > 0:
                aliveEnemies.append(enemy)
            else:
                self.gainXp(enemy.data["xp"])
        self.enemies = aliveEnemies

    def gainXp(self, amount):
        self.xp += amount
        self.checkLevelUp()

    def checkLevelUp(self):
        if self.xp >= self.xpToLevel and not self.choosingUpgrade:
            self.xp -= self.xpToLevel
            self.xpToLevel += 3
            self.level += 1
            self.newUpgradeOptions()
            self.choosingUpgrade = True     # congela o jogo até escolher

    def newUpgradeOptions(self):
        # lista de (código, texto). Armas novas e evoluções entram no sorteio junto com os upgrades normais.
        options = [
            ("speed", "Mais velocidade de movimento"),
            ("delay", "Mais velocidade de ataque"),
            ("damage", "Mais força"),
            ("heal", "Recuperar 30 de vida"),
        ]
        for name, weapon in WEAPONS.items():
            level = self.weapons.get(name, 0)
            if level == 0:
                options.append((name, f"Nova arma: {weapon['name']} ({weapon['info']})"))
            elif level < MAX_WEAPON_LEVEL:
                options.append((name, f"{weapon['name']} nível {level + 1}"))

        self.upgradeOptions = random.sample(options, 3)

    def chooseUpgrade(self, number):
        option = self.upgradeOptions[number - 1][0]

        if option == "speed":
            self.playerSpeed += 40
        elif option == "delay":
            self.attackDelay = max(self.attackDelay * 0.8, 0.25)
        elif option == "damage":
            self.playerDamage += 1
        elif option == "heal":
            self.playerHp = min(self.playerHp + 30, self.playerMaxHp)
        else:
            self.weapons[option] = self.weapons.get(option, 0) + 1     # arma nova (nível 1) ou evolução

        self.choosingUpgrade = False
        self.checkLevelUp()     # se juntou xp para mais um nível, já abre outro menu

    # --------------------------------------------------------- desenhar
    def draw(self):
        # câmera: o jogador sempre fica no centro da tela
        self.camera = self.playerPos - pygame.Vector2(self.screenWidth / 2, self.screenHeight / 2)

        self.screen.fill('darkgray')
        self.drawGrass()

        # cor do cenário da fase atual
        tint = STAGES[self.stage]["tint"]
        if tint:
            self.dimScreen(tint[0], tint[1])

        for enemy in self.enemies:
            if enemy.angry:
                self.drawSprite(self.sprites[enemy.data["angrySprite"]], enemy.pos)
            else:
                self.drawSprite(self.sprites[enemy.data["sprite"]], enemy.pos)

        for shot in self.shots:
            self.drawSprite(shot.image, shot.pos)

        for panPos, direction in self.panPositions():
            self.drawSprite(self.rotated("frigideira", direction), panPos)

        self.drawSprite(self.player, self.playerPos)
        self.drawHud()

        if self.bannerTimer > 0 and not self.gameOver:
            self.drawText(f"Fase {self.stage + 1}", 120)

        if self.choosingUpgrade:
            self.dimScreen()
            self.drawText("Subiu de nível! Escolha:", 250)
            for i, option in enumerate(self.upgradeOptions):
                self.drawText(f"{i + 1} - {option[1]}", 350 + i * 70)

        if self.gameOver:
            self.dimScreen()
            self.drawText("Você venceu!" if self.won else "Fim de jogo", 350)
            self.drawText("Aperte R para recomeçar", 420)

    def drawSprite(self, image, worldPos):
        # converte a posição do MUNDO em posição da TELA e desenha com o centro nela
        screenPos = worldPos - self.camera
        rect = image.get_rect(center=screenPos)
        self.screen.blit(image, rect)

    def drawGrass(self):
        # a grama anda ao contrário da câmera. O % faz o deslocamento "dar a volta"
        # a cada tile, então a grama se repete para sempre.
        offsetX = -(self.camera.x % self.tileSide)
        offsetY = -(self.camera.y % self.tileSide)

        # + 1 tile de folga para não aparecer buraco na borda enquanto desliza
        tilesX = self.screenWidth // self.tileSide + 1
        tilesY = self.screenHeight // self.tileSide + 1

        for x in range(tilesX):
            for y in range(tilesY):
                self.screen.blit(self.grass, (offsetX + x * self.tileSide, offsetY + y * self.tileSide))

    def drawHud(self):
        # barra de vida
        pygame.draw.rect(self.screen, 'darkred', (10, 10, 200, 20))
        hpWidth = 200 * max(self.playerHp, 0) / self.playerMaxHp
        pygame.draw.rect(self.screen, 'red', (10, 10, hpWidth, 20))

        # barra de xp
        pygame.draw.rect(self.screen, 'black', (10, 35, 200, 10))
        xpWidth = 200 * min(self.xp / self.xpToLevel, 1)
        pygame.draw.rect(self.screen, 'gold', (10, 35, xpWidth, 10))

        text = self.font.render(f"Nível {self.level}   Fase {self.stage + 1}/{len(STAGES)}", True, 'white')
        self.screen.blit(text, (10, 50))

    def dimScreen(self, color='black', alpha=150):
        # um retângulo colorido meio transparente por cima de tudo
        self.overlay.fill(color)
        self.overlay.set_alpha(alpha)
        self.screen.blit(self.overlay, (0, 0))

    def drawText(self, text, y):
        image = self.font.render(text, True, 'white')
        rect = image.get_rect(center=(self.screenWidth / 2, y))
        self.screen.blit(image, rect)


if __name__ == "__main__":
    Game().Run()
