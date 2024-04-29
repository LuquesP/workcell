const tMax = 10000;
const d = 0.05;
const a = -0.3;
const b = 0.2;
const th = 0.45;

function* h_generator(ttf, d, a, b, th) {
  th = typeof th !== "undefined" ? th : 0;
  for (let t = ttf; t >= 0; t--) {
    let h = 1 - d - Math.exp(a * Math.pow(t, b));
    if (h < th) {
      break;
    }
    yield { t: t, h: h };
  }
}

// function sleep(ms) {
//   return new Promise((resolve) => setTimeout(resolve, ms));
// }

class RotationalMachine {
  constructor(name, h1, h2) {
    this.ambientTemperature = 20; // degrees Celsius
    this.maxTemperature = 120;
    this.ambientPressure = 101; // kPa

    this.W = [1 / 2, 1, 2, 3, 5, 7, 12, 18];
    this.A = [1, 5, 80, 2 / 3, 8, 2, 14, 50];
    this.t = 0;
    this.name = name;
    this.speed = 0;
    this.speedDesired = 0;
    this.temperature = this.ambientTemperature;
    this.pressure = this.ambientPressure;
    this.pressureFactor = 2;
    this.h1 = h1;
    this.h2 = h2;
    this.broken = false;
  }
  setHealth(h1, h2) {
    this.h1 = h1;
    this.h2 = h2;
    this.broken = false;
  }
  setSpeed(speed) {
    this.speedDesired = speed;
  }
  _g(v, minV, maxV, target, rate) {
    let delta = (target - v) * rate;
    return Math.max(Math.min(v + delta, maxV), minV);
  }
  noise(magnitude) {
    return Math.random() * (magnitude - -magnitude - magnitude);
  }

  nextState() {
    let h1 = 0;
    let h2 = 0;
    try {
      h1 = this.h1.next().value.h;
    } catch {
      this.broken = true;
      throw new Error("F1");
    }
    try {
      h2 = this.h2.next().value.h;
    } catch {
      this.broken = true;
      throw new Error("F2");
    }
    this.speed = (this.speed + (2 - h2) * this.speedDesired) / 2;

    this.temperature =
      (2 - h1) *
      this._g(
        this.temperature,
        this.ambientPressure,
        this.maxTemperature,
        this.speed / 10,
        (0.01 * this.speed) / 1000
      );
    this.pressure =
      h1 *
      this._g(
        this.pressure,
        this.ambientPressure,
        Infinity,
        this.speed * this.pressureFactor,
        (0.3 * this.speed) / 1000
      );
    let state = {
      speedDesired: this.speedDesired,
      ambientPressure: this.ambientPressure + this.noise(0.1),
      ambientTemperature: this.ambientTemperature + this.noise(0.1),
      speed: this.speed + this.noise(5),
      temperature: this.temperature + this.noise(0.1),
      pressure: this.pressure + this.noise(20),
    };
    this.t += 1;
    for (const key in state) {
      if (Object.prototype.hasOwnProperty.call(state, key)) {
        const value = state[key];
        if (typeof value === "number") {
          state[key] = parseFloat(value.toFixed(2));
        }
      }
    }
    return state;
  }
}

function createMachines(n) {
  let machines = [];
  for (let i = 0; i < n; i++) {
    let ttf1 = Math.floor(Math.random() * (50000 - 5000 + 1) + 5000);
    let ttf2 = Math.floor(Math.random() * (90000 - 5000 + 1) + 5000);
    let h1 = h_generator(ttf1, d, a, b);
    let h2 = h_generator(ttf2, d, a, b);
    let m = new RotationalMachine(`M_${String(i).padStart(4, "0")}`, h1, h2);
    machines.push(m);
  }
  return machines;
}

let machine = createMachines(1)[0];
let cycleLengthMin = 1;
let cycleLengthMax = 5;
let sampleRate = 2;

while (true) {
  if (machine.broken) {
    let ttf1 = Math.floor(Math.random() * (50000 - 5000 + 1) + 5000);
    let h1 = h_generator(ttf1, d, a, b);

    let ttf2 = Math.floor(Math.random() * (90000 - 5000 + 1) + 5000);
    let h2 = h_generator(ttf2, d, a, b);

    machine.setHealth(h1, h2);

    console.log({
      timestamp: new Date().toISOString(),
      machineID: machine.name,
      level: "INFO",
      code: "fixed",
    });
    continue;
  }
  let l =
    Math.random() * (cycleLengthMax - cycleLengthMin + 1) + cycleLengthMin;
  let offset = Math.random() * (60 - 1 - 0 + 1) + 0;
  machine.setSpeed(1000);
  let duration = l * 60;
  let cooldownPoint = duration - 20;
  for (let i = 0; i < duration; i++) {
    if (i == cooldownPoint) {
      machine.setSpeed(0);
    }
    try {
      let state = machine.nextState();
      state["timestamp"] = new Date().toISOString();
      state["machineID"] = machine.name;
      console.log(state);
      if (!state) {
        break;
      }
    } catch (error) {
      console.log({
        timestamp: new Date().toISOString(),
        machineID: machine.name,
        level: "CRITICAL",
        code: error.toString(),
      });
      break;
    }
  }
}
