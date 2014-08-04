import pygame, sys, math
from pygame.locals import *
import random

class Map:
    # Multipliers for transforming coordinates to other octants:
    mult = [
                [1,  0,  0, -1, -1,  0,  0,  1],
                [0,  1, -1,  0,  0, -1,  1,  0],
                [0,  1,  1,  0,  0, -1, -1,  0],
                [1,  0,  0,  1, -1,  0,  0, -1]
            ]
    def __init__(self, x, y, bbs):
        self.init_data(bbs, x, y)
        self.width, self.height = x, y
        self.light = []
        for i in range(self.height):
            self.light.append([(0, [])] * self.width)
        self.flag = 0

    def init_data(self, bbs, w, h):        
        self.data = []
        for i in range(h):
            self.data.append(['.'] * w)
        for bb in bbs:
            self.data[bb.y][bb.x:bb.x+bb.w] = ['#']*(bb.w)
            self.data[bb.y+bb.h][bb.x:bb.x+bb.w] = ['#']*(bb.w)
            for row in self.data[bb.y:bb.y+bb.h+1]:
                row[bb.x] = '#'
                row[bb.x+bb.w] = '#'
        self.data[0][:] = ['#'] * w
        self.data[-1][:] = ['#'] * w
        for row in self.data[:]:
            row[0] = '#'
            row[-1] = '#'
        
    def square(self, x, y):
        return self.data[y][x]
    
    def blocked(self, x, y):
        return (x < 0 or y < 0
                or x >= self.width or y >= self.height
                or self.data[y][x] == "#")
    
    def lit(self, x, y):
        return self.light[y][x][0]
    
    def set_lit(self, x, y, ls):
        if 0 <= x < self.width and 0 <= y < self.height and not ls in self.light[y][x][1]:
            v = ls.v/(1 + ((x/100.0-ls.x/100.0)**2 + (y/100.0-ls.y/100.0)**2))
            self.light[y][x] = (self.light[y][x][0] + v, self.light[y][x][1] + [ls])
            
    def _cast_light(self, cx, cy, row, start, end, radius, ls, xx, xy, yx, yy, id):
        """Recursive lightcasting function"""
        if start < end:
            return
        radius_squared = radius*radius
        for j in range(row, radius+1):
            dx, dy = -j-1, -j
            blocked = False
            while dx <= 0:
                dx += 1
                # Translate the dx, dy coordinates into map coordinates:
                X, Y = cx + dx * xx + dy * xy, cy + dx * yx + dy * yy
                # l_slope and r_slope store the slopes of the left and right
                # extremities of the square we're considering:
                l_slope, r_slope = (dx-0.5)/(dy+0.5), (dx+0.5)/(dy-0.5)
                if start < r_slope:
                    continue
                elif end > l_slope:
                    break
                else:
                    # Our light beam is touching this square; light it:
                    if dx*dx + dy*dy < radius_squared:
                        self.set_lit(X, Y, ls)
                    if blocked:
                        # we're scanning a row of blocked squares:
                        if self.blocked(X, Y):
                            new_start = r_slope
                            continue
                        else:
                            blocked = False
                            start = new_start
                    else:
                        if self.blocked(X, Y) and j < radius:
                            # This is a blocking square, start a child scan:
                            blocked = True
                            self._cast_light(cx, cy, j+1, start, l_slope,
                                             radius, ls,
                                             xx, xy, yx, yy, id+1)
                            new_start = r_slope
            # Row is scanned; do next row unless last square was blocked:
            if blocked:
                break
            
    def do_fov(self, x, y, radius, ls):
        self.flag += 1
        self.set_lit(x, y, ls)
        for oct in range(8):
            self._cast_light(x, y, 1, 1.0, 0.0, radius, ls,
                             self.mult[0][oct], self.mult[1][oct],
                             self.mult[2][oct], self.mult[3][oct], 0)
            
    def check_lights(self, game):
        for light in game.lightSources:
            self.do_fov(light.x, light.y, int(light.v*400), light)


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class LightSource:
    """Represents a point light source"""    
    def __init__(self, x, y, v=1):
        self.x = x
        self.y = y
        self.v = min(1, v)

class BoundingBox:
    """Represents a simple bounding box"""
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def intersects(self, bb):
        return not (bb.x > self.x+self.w or 
           bb.x+bb.w < self.x or
           bb.y+bb.h > self.y or
           bb.y < self.y+self.h)

class RayGame:
    """Keeps game variables"""
    mouseX=0
    mouseY=0
    lightDirty = True
    shadedAreas = []
    map=None
    
    def __init__(self, lightSources=[], boundingBoxes=[], masterSurface=None):
        self.lightSources = lightSources
        self.boundingBoxes = boundingBoxes
        self.masterSurface = masterSurface

    def addLight(self, x=0, y=0, v=1, ls=None):
        # can add checks for redundancy and what not
        if ls != None:
            self.lightSources = self.lightSources + [ls]
        else:
            self.lightSources = self.lightSources + [LightSource(x, y, v)]

    def addbb(self, x=0, y=0, w=0, h=0, bb=None):
        if bb != None:
            self.boundingBoxes = self.boundingBoxes + [bb]
        else:
            self.boundingBoxes = self.boundingBoxes + [BoundingBox(x, y, w, h)]

    def addShadedArea(self, shadedArea):
        self.shadedAreas = self.shadedAreas + [shadedArea]

    def initMap(self, x, y):
        self.map = Map(x, y, self.boundingBoxes)

def handle_event(event):
    if event.type == MOUSEMOTION:
        game.mouseX, game.mouseY = event.pos
        handle_event_light_source(game.mouseX, game.mouseY)

def handle_event_light_source(x, y):
    # right now replaces all light sources with mouse light source
    game.lightSources = [LightSource(x, y, 1)]
    game.lightDirty = True

def handle_pixel(map, pixel, x, y):
    i = map.lit(x, y)
    i = max(.08, i)
    i = min(1, i)
    return tuple([i*x for x in pygame.Color(pixel*256)]) # account for not displaying alpha

def shadePixelLayer(surface, map):    
    pixObj = pygame.PixelArray(surface)
    for x in range(0, len(pixObj)):
        for y in range(0, len(pixObj[x])):
            pixObj[x][y] = handle_pixel(map, pixObj[x][y], x, y)

def randomRectangle(w, h):
    x = random.randint(0, w-1)
    y = random.randint(0, h-1)
    w = random.randint(0, w-x-1)
    h = random.randint(0, h-y-1)
    return BoundingBox(x, y, w, h)

def nRandomRects(game, n, x, y):
    while len(game.boundingBoxes) < n:
        bb = randomRectangle(x, y)
        if bb.w < 10 or bb.h < 10 or bb.w > 100 or bb.h > 100:
            continue
        i = False
        for box in game.boundingBoxes:
            i = i or box.intersects(bb)
        if not i:
            game.addbb(bb=bb)
            pygame.draw.rect(DISPLAYSURF, BLUE, (bb.x, bb.y, bb.w, bb.h))
   
BLACK = (  0,   0,   0)
WHITE = (255, 255, 255)
RED = (255,   0,   0)
GREEN = (  0, 255,   0)
BLUE = (  0,   0, 255)

pygame.init()

FPS = 30 # frames per second setting
fpsClock = pygame.time.Clock()

DISPLAYSURF = pygame.display.set_mode((400,300))
game = RayGame()
anotherSurface = DISPLAYSURF.convert_alpha() # to use transparency
pygame.display.set_caption('Ray Cast Start')

DISPLAYSURF.fill(WHITE)

nRandomRects(game, 5, DISPLAYSURF.get_width(), DISPLAYSURF.get_height())

"""
pygame.draw.rect(DISPLAYSURF, BLUE, (40, 45, 100, 50))
game.addbb(bb=BoundingBox(40, 45, 100, 50))
pygame.draw.rect(DISPLAYSURF, BLUE, (260, 45, 100, 50))
game.addbb(bb=BoundingBox(260, 45, 100, 50))
pygame.draw.rect(DISPLAYSURF, BLUE, (40, 205, 100, 50))
game.addbb(bb=BoundingBox(40, 205, 100, 50))
pygame.draw.rect(DISPLAYSURF, BLUE, (260, 205, 100, 50))
game.addbb(260, 205, 100, 50)
"""

game.addLight(ls=LightSource(300, 150, .6))
game.addLight(ls=LightSource(10, 10, 1))
game.addLight(ls=LightSource(30, 290, .7))
game.addLight(90, 70, 1)

game.masterSurface = DISPLAYSURF.copy()

while True: # main loop
    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
        handle_event(event)
    if game.lightDirty:        
        game.initMap(DISPLAYSURF.get_width(), DISPLAYSURF.get_height())
        DISPLAYSURF.blit(game.masterSurface, (0, 0))
        game.map.check_lights(game)
        shadePixelLayer(DISPLAYSURF, game.map)
        game.lightDirty=False
    pygame.display.update()
    fpsClock.tick(FPS)

