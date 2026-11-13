import pygame
import random

# ---------------------------------------------------------------
# JOGO TESTE: o menor "Vampire Survivors" possível.
# Controles: WASD anda | 1, 2, 3 escolhe o upgrade | R recomeça
# Precisa da pasta "assets" ao lado deste arquivo.
# ---------------------------------------------------------------


# classes pequenas: cada inimigo e cada tiro guardam os seus próprios dados
class Enemy:
    def __init__(self, pos):
        self.pos = pygame.Vector2(pos)
        self.hp = 2
        self.angry = False       # False = inofensivo, True = forma maligna


class Shot:
    def __init__(self, pos, direction):
        self.pos = pygame.Vector2(pos)
        self.direction = direction      # vetor de tamanho 1 apontando para o alvo
        self.timeLeft = 1.5             # segundos até o tiro sumir


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

    def loadSprites(self):
        self.grass = pygame.image.load("assets/grass.png").convert_alpha()
        self.grass = pygame.transform.scale(self.grass, (self.tileSide, self.tileSide))
        self.player = pygame.image.load("assets/player_front_1.png").convert_alpha()
        self.player = pygame.transform.scale(self.player, (self.tileSide, self.tileSide))
        self.banano = pygame.image.load("assets/banano.png").convert_alpha()
        self.banano = pygame.transform.scale(self.banano, (self.tileSide, self.tileSide))
        self.bananoangry = pygame.image.load("assets/banano2.png").convert_alpha()
        self.bananoangry = pygame.transform.scale(self.bananoangry, (self.tileSide, self.tileSide))
        self.spoon = pygame.image.load("assets/colher.png").convert_alpha()
        self.spoon = pygame.transform.scale(self.spoon, (self.tileSide, self.tileSide))

    def newGame(self):
        # tudo que muda durante a partida fica aqui.
        # chamar newGame() de novo = recomeçar do zero.

        # atributos do jogador
        self.playerPos = pygame.Vector2(0, 0)    # posição no MUNDO (não na tela)
        self.playerHp = 100
        self.playerMaxHp = 100
        self.playerSpeed = 250                   # pixels por segundo
        self.playerDamage = 1                    # força
        self.attackDelay = 0.6                   # segundos entre tiros (menor = mais rápido)
        self.attackTimer = 0

        # experiência
        self.xp = 0
        self.xpToLevel = 5
        self.level = 1

        # listas
        self.enemies = []
        self.shots = []
        self.spawnTimer = 0

        # estados do jogo
        self.gameOver = False
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
            self.dt = self.clock.tick(75) / 1000

        pygame.quit()

    def handleEvents(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if event.type == pygame.KEYDOWN:
                if self.choosingUpgrade:
                    if event.key == pygame.K_1:
                        self.chooseUpgrade(1)
                    if event.key == pygame.K_2:
                        self.chooseUpgrade(2)
                    if event.key == pygame.K_3:
                        self.chooseUpgrade(3)

                if self.gameOver and event.key == pygame.K_r:
                    self.newGame()

    # ------------------------------------------------------- atualizar
    def update(self):
        self.movePlayer()
        self.spawnEnemies()
        self.moveEnemies()
        self.attack()
        self.moveShots()
        self.removeDeadEnemies()

        if self.playerHp <= 0:
            self.gameOver = True

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

        # velocidade (pixels por segundo) * dt (segundos) = pixels neste frame
        self.playerPos += direction * self.playerSpeed * self.dt

    def spawnEnemies(self):
        self.spawnTimer -= self.dt
        if self.spawnTimer <= 0:
            self.spawnTimer = 1.5

            # sorteia um ângulo e coloca o inimigo a 600 pixels do jogador
            # (a tela só vai até uns 566 do centro, então ele nasce fora da vista)
            offset = pygame.Vector2(600, 0).rotate(random.randint(0, 359))
            self.enemies.append(Enemy(self.playerPos + offset))

    def moveEnemies(self):
        for enemy in self.enemies:
            toPlayer = self.playerPos - enemy.pos
            distance = toPlayer.length()

            # chegou perto? fica maligno (e continua maligno)
            if distance < 250:
                enemy.angry = True

            if enemy.angry:
                speed = 150
            else:
                speed = 50

            if distance > 0:
                enemy.pos += toPlayer.normalize() * speed * self.dt

            # encostou no jogador: tira vida (8 por segundo)
            if distance < 50:
                self.playerHp -= 8 * self.dt

    def attack(self):
        self.attackTimer -= self.dt
        if self.attackTimer > 0 or len(self.enemies) == 0:
            return

        # procura o inimigo mais perto do jogador
        nearest = self.enemies[0]
        for enemy in self.enemies:
            if enemy.pos.distance_to(self.playerPos) < nearest.pos.distance_to(self.playerPos):
                nearest = enemy

        direction = nearest.pos - self.playerPos
        if direction.length() > 0:
            self.shots.append(Shot(self.playerPos, direction.normalize()))
            self.attackTimer = self.attackDelay

    def moveShots(self):
        for shot in self.shots:
            shot.pos += shot.direction * 600 * self.dt
            shot.timeLeft -= self.dt

            # acertou algum inimigo?
            for enemy in self.enemies:
                if shot.pos.distance_to(enemy.pos) < 40:
                    enemy.hp -= self.playerDamage
                    shot.timeLeft = 0       # o tiro some
                    break

        # monta uma lista nova só com os tiros que ainda valem
        aliveShots = []
        for shot in self.shots:
            if shot.timeLeft > 0:
                aliveShots.append(shot)
        self.shots = aliveShots

    def removeDeadEnemies(self):
        aliveEnemies = []
        for enemy in self.enemies:
            if enemy.hp > 0:
                aliveEnemies.append(enemy)
            else:
                self.gainXp(1)
        self.enemies = aliveEnemies

    def gainXp(self, amount):
        self.xp += amount
        if self.xp >= self.xpToLevel:
            self.xp -= self.xpToLevel
            self.xpToLevel += 3
            self.level += 1
            self.choosingUpgrade = True     # congela o jogo até escolher

    def chooseUpgrade(self, number):
        if number == 1:
            self.playerSpeed += 40
        if number == 2:
            self.attackDelay *= 0.8
        if number == 3:
            self.playerDamage += 1
        self.choosingUpgrade = False

    # --------------------------------------------------------- desenhar
    def draw(self):
        # câmera: o jogador sempre fica no centro da tela
        self.camera = self.playerPos - pygame.Vector2(self.screenWidth / 2, self.screenHeight / 2)

        self.screen.fill('darkgray')
        self.drawGrass()

        for enemy in self.enemies:
            if enemy.angry:
                self.drawSprite(self.bananoangry, enemy.pos)
            else:
                self.drawSprite(self.banano, enemy.pos)

        for shot in self.shots:
            self.drawSprite(self.spoon, shot.pos)

        self.drawSprite(self.player, self.playerPos)
        self.drawHud()

        if self.choosingUpgrade:
            self.dimScreen()
            self.drawText("Subiu de nível! Escolha:", 250)
            self.drawText("1 - Mais velocidade de movimento", 350)
            self.drawText("2 - Mais velocidade de ataque", 420)
            self.drawText("3 - Mais força", 490)

        if self.gameOver:
            self.dimScreen()
            self.drawText("Fim de jogo", 350)
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
        xpWidth = 200 * self.xp / self.xpToLevel
        pygame.draw.rect(self.screen, 'gold', (10, 35, xpWidth, 10))

        text = self.font.render(f"Nível {self.level}", True, 'white')
        self.screen.blit(text, (10, 50))

    def dimScreen(self):
        # um retângulo preto meio transparente por cima de tudo
        dark = pygame.Surface((self.screenWidth, self.screenHeight))
        dark.set_alpha(150)
        self.screen.blit(dark, (0, 0))

    def drawText(self, text, y):
        image = self.font.render(text, True, 'white')
        rect = image.get_rect(center=(self.screenWidth / 2, y))
        self.screen.blit(image, rect)


if __name__ == "__main__":
    Game().Run()