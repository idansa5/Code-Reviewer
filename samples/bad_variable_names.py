def process(data):
    x = 0
    for d in data:
        tmp = d * 2
        x += tmp
    return x


def calc(a, b, c):
    z = a + b
    y = z * c
    return y


class Mgr:
    def __init__(self, val):
        self.v = val

    def run(self, lst):
        res = []
        for e in lst:
            res.append(e + self.v)
        return res
