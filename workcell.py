import numpy as np
import random
from datetime import date
from scipy.interpolate import interp1d
import math
from datetime import datetime

t_max = 10000

d = 0.05
a = -0.3
b = 0.2
th = 0.45


def h_generator(ttf, d, a, b, th=0):
    for t in range(ttf, -1, -1):
        h = 1 - d - math.exp(a * t**b)
        if h < th:
            break
        yield t, h


class VibrationSensorSignalSample:
    CUTOFF = 150

    def __init__(
        self,
        W,
        A,
        fundamental_from,
        fundamental_to,
        t=0,
        interval=1,
        previous_sample=None,
        sample_rate=1024,
    ):
        self.interval = interval
        self.sample_rate = sample_rate
        self.W = W
        self.A = A
        self.t = t
        self.base_frequency = fundamental_from
        self.target_base_frequency = fundamental_to
        self.add_noise = True
        self.__previous_sample = previous_sample
        self.__N = sample_rate * interval

    def pcm(self):
        ts = np.linspace(self.t, self.t + self.interval, num=self.__N, endpoint=False)

        x = np.array([0, self.interval]) + self.t
        points = np.array([self.base_frequency, self.target_base_frequency])
        rpm = interp1d(x, points, kind="linear")

        f = rpm(ts)
        f[f < 0] = 0

        fi = np.cumsum(f / self.sample_rate) + (
            self.__previous_sample.__last_cumsum if self.__previous_sample else 0
        )

        base = 2 * np.pi * fi
        b = np.array([np.sin(base * w) * a for w, a in zip(self.W, self.A)])
        a = b.sum(axis=0)

        if self.add_noise:
            a += np.random.normal(0, 0.1, self.__N)

        self.__last_cumsum = fi[-1]
        self.base_frequency = self.target_base_frequency

        a[a > self.CUTOFF] = self.CUTOFF
        a[a < -self.CUTOFF] = -self.CUTOFF

        return np.int16(a / self.CUTOFF * 32767)


class RotationalMachine:
    ambient_temperature = 20  # degrees Celsius
    max_temperature = 120
    ambient_pressure = 101  # kPa

    def __init__(self, name, h1, h2, use_vibraiton):
        self.W = [1 / 2, 1, 2, 3, 5, 7, 12, 18]
        self.A = [1, 5, 80, 2 / 3, 8, 2, 14, 50]
        self.t = 0
        self.name = name
        self.speed = 0
        self.speed_desired = 0
        self.temperature = RotationalMachine.ambient_temperature
        self.pressure = RotationalMachine.ambient_pressure
        self.pressure_factor = 2
        self.__vibration_sample = None
        self.__h1 = h1
        self.__h2 = h2
        self.broken = False
        self.use_vibraiton = False

    def set_health(self, h1, h2):
        self.__h1 = h1
        self.__h2 = h2
        self.broken = False

    def set_speed(self, speed):
        self.speed_desired = speed

    def __g(self, v, min_v, max_v, target, rate):
        delta = (target - v) * rate
        return max(min(v + delta, max_v), min_v)

    def noise(self, magnitude):
        return random.uniform(-magnitude, magnitude)

    def next_state(self):
        try:
            _, h1 = next(self.__h1)
        except:
            self.broken = True
            raise Exception("F1")

        try:
            _, h2 = next(self.__h2)
        except:
            self.broken = True
            raise Exception("F2")

        v_from = self.speed / 60
        self.speed = (self.speed + (2 - h2) * self.speed_desired) / 2
        v_to = self.speed / 60

        self.temperature = (2 - h1) * self.__g(
            self.temperature,
            self.ambient_temperature,
            self.max_temperature,
            self.speed / 10,
            0.01 * self.speed / 1000,
        )
        self.pressure = h1 * self.__g(
            self.pressure,
            self.ambient_pressure,
            np.inf,
            self.speed * self.pressure_factor,
            0.3 * self.speed / 1000,
        )
        if self.use_vibraiton:
            self.__vibration_sample = VibrationSensorSignalSample(
                # self.W, self.A, v_from, v_to, t = self.t, previous_sample = self.__vibration_sample)
                self.W,
                self.A,
                v_from,
                v_to,
                t=self.t,
            )

        state = {
            "speed_desired": self.speed_desired,
            "ambient_temperature": self.ambient_temperature + self.noise(0.1),
            "ambient_pressure": self.ambient_pressure + self.noise(0.1),
            "speed": self.speed + self.noise(5),
            "temperature": self.temperature + self.noise(0.1),
            "pressure": self.pressure + self.noise(20),
            "vibration": self.__vibration_sample,
        }

        self.t += 1

        for key in state:
            value = state[key]
            if isinstance(value, (int, float)):
                state[key] = round(value, 2)

        return state


def create_machines(n):
    machines = []
    for i in range(n):
        ttf1 = random.randint(5000, 50000)
        ttf2 = random.randint(5000, 90000)

        h1 = h_generator(ttf1, d, a, b)
        h2 = h_generator(ttf2, d, a, b)

        m = RotationalMachine("M_{0:04d}".format(i), h1, h2, False)
        machines.append(m)
    return machines


machine = create_machines(1)[0]
cycle_length_min = 1
cycle_length_max = 5

while 1:
    if machine.broken:
        ttf1 = random.randint(5000, 50000)
        h1 = h_generator(ttf1, d, a, b)

        ttf2 = random.randint(5000, 90000)
        h2 = h_generator(ttf2, d, a, b)
        machine.set_health(h1, h2)

        print(
            "error fixed: ",
            {
                "timestamp": str(datetime.now()),
                "machineID": machine.name,
                "level": "INFO",
                "code": "fixed",
            },
        )

        continue

    l = random.randint(cycle_length_min, cycle_length_max)
    offset = random.randint(0, 60 - l)
    machine.set_speed(1000)
    duration = l * 60
    cooldown_point = duration - 20
    for i in range(duration):
        if i == cooldown_point:
            machine.set_speed(0)
        try:
            state = machine.next_state()
            state["timestamp"] = str(datetime.now())
            state["machineID"] = machine.name
            print(state)
            if not state["speed"]:
                break
        except Exception as e:
            print(
                "*********Error occured: *********",
                {
                    "timestamp": str(datetime.now()),
                    "machineID": machine.name,
                    "level": "CRITICAL",
                    "code": str(e),
                },
            )
            break
