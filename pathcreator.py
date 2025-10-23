import math
import random

# Variabili globali
seed = 1
a, b, c, d, e = 0, 0, 0, 0, 0
t = 0.1
j = 0.04
flip = False
xi, yi = 0, 0
xn, yn = 15, 10
width, height = 300, 200
radius = 2.0
offset = 0.0
vertical = False
BEZIER_BASE_STEPS = 100 # valore base attuale

def init_params(num_x, num_y, w, h, r=2.0, tabsize=20, jitter=4):
    global xn, yn, width, height, radius, t, j
    xn = num_x
    yn = num_y
    width = w
    height = h
    radius = r
    t = tabsize / 200.0
    j = jitter / 100.0

# Funzioni di supporto
def random_seed():
    global seed
    x = math.sin(seed) * 10000
    seed += 1
    return x - math.floor(x)

def uniform(min_val, max_val):
    r = random_seed()
    return min_val + r * (max_val - min_val)

def rbool():
    return random_seed() > 0.5

def sl():
    return height / yn if vertical else width / xn

def sw():
    return width / xn if vertical else height / yn

def ol():
    return offset + sl() * (yi if vertical else xi)

def ow():
    return offset + sw() * (xi if vertical else yi)

def l(v):
    ret = ol() + sl() * v
    return round(ret * 100) / 100

def w(v):
    ret = ow() + sw() * v * (-1.0 if flip else 1.0)
    return round(ret * 100) / 100

def p0l(): return l(0.0)
def p0w(): return w(0.0)
def p1l(): return l(0.2)
def p1w(): return w(a)
def p2l(): return l(0.5 + b + d)
def p2w(): return w(-t + c)
def p3l(): return l(0.5 - t + b)
def p3w(): return w(t + c)
def p4l(): return l(0.5 - 2.0 * t + b - d)
def p4w(): return w(3.0 * t + c)
def p5l(): return l(0.5 + 2.0 * t + b - d)
def p5w(): return w(3.0 * t + c)
def p6l(): return l(0.5 + t + b)
def p6w(): return w(t + c)
def p7l(): return l(0.5 + b + d)
def p7w(): return w(-t + c)
def p8l(): return l(0.8)
def p8w(): return w(e)
def p9l(): return l(1.0)
def p9w(): return w(0.0)

def first():
    global e
    e = uniform(-j, j)
    next()

def next():
    global a, b, c, d, e, flip
    flip_old = flip
    flip = rbool()
    a = -e if flip == flip_old else e
    b = uniform(-j, j)
    c = uniform(-j, j)
    d = uniform(-j, j)
    e = uniform(-j, j)

# Funzione per calcolare punti di una curva di Bézier cubica
def bezier_cubic(p0, p1, p2, p3):
    
    steps = BEZIER_BASE_STEPS

    points = []
    for t in range(steps + 1):
        t = t / steps
        mt = 1 - t
        x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
        y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
        points.append((x, y))
    return points

def gen_dh():
    global vertical, yi, xi
    paths = []
    vertical = False
    for yi in range(1, yn):
        xi = 0
        first()
        path = []
        path.append((p0l(), p0w()))  # Punto iniziale
        while xi < xn:
            # Prima curva di Bézier
            path.extend(bezier_cubic(
                (p0l(), p0w()), (p1l(), p1w()), (p2l(), p2w()), (p3l(), p3w())
            ))
            # Seconda curva di Bézier
            path.extend(bezier_cubic(
                (p3l(), p3w()), (p4l(), p4w()), (p5l(), p5w()), (p6l(), p6w())
            ))
            # Terza curva di Bézier
            path.extend(bezier_cubic(
                (p6l(), p6w()), (p7l(), p7w()), (p8l(), p8w()), (p9l(), p9w())
            ))
            paths.append(path)
            path = [(p9l(), p9w())]  # Inizia il prossimo segmento
            next()
            xi += 1
    return paths

def gen_dv():
    global vertical, xi, yi
    paths = []
    vertical = True
    for xi in range(1, xn):
        yi = 0
        first()
        path = []
        path.append((p0w(), p0l()))
        while yi < yn:
            path.extend(bezier_cubic(
                (p0w(), p0l()), (p1w(), p1l()), (p2w(), p2l()), (p3w(), p3l())
            ))
            path.extend(bezier_cubic(
                (p3w(), p3l()), (p4w(), p4l()), (p5w(), p5l()), (p6w(), p6l())
            ))
            path.extend(bezier_cubic(
                (p6w(), p6l()), (p7w(), p7l()), (p8w(), p8l()), (p9w(), p9l())
            ))
            paths.append(path)
            path = [(p9w(), p9l())]
            next()
            yi += 1
    return paths

def gen_db():
    segments = [
        ("line", (offset + radius, offset), (offset + width - radius, offset)),
        ("arc", (offset + width - radius*2, offset, offset + width, offset + radius*2), radius, 270, 360),
        ("line", (offset + width, offset + radius), (offset + width, offset + height - radius)),
        ("arc", (offset + width - radius*2, offset + height - radius*2, offset + width, offset + height), radius, 0, 90),
        ("line", (offset + width, offset + height), (offset + radius, offset + height)),
        ("arc", (offset, offset + height - radius*2, offset + radius*2, offset + height), radius, 90, 180),
        ("line", (offset, offset + height - radius), (offset, offset + radius)),
        ("arc", (offset, offset, offset + radius*2, offset + radius*2), radius, 180, 270)
    ]
    return segments